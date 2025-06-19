#!/usr/bin/env python3
"""
Mixed-Effects Models for Biomechanical Data Analysis

Created: 2025-06-19 with user permission
Purpose: Advanced mixed-effects modeling capabilities for hierarchical biomechanical data

Intent:
This module provides comprehensive mixed-effects modeling functionality specifically designed 
for biomechanical gait analysis. It integrates with the LocomotionData class to handle 
hierarchical data structures (subjects, sessions, trials) and provides pre-built templates
for common biomechanical research questions.

Key Features:
- lme4 integration via rpy2 for robust mixed-effects modeling
- Biomechanics-specific model templates and workflows
- Automated model comparison and selection
- Random effects structure recommendations
- Model diagnostics and assumption checking
- Effect size calculations and interpretation tools

Architecture:
- MixedEffectsManager: Main interface for model building and analysis
- BiomechanicalModels: Pre-built templates for common analyses
- ModelComparison: Automated model selection and validation
- RandomEffectsOptimizer: Intelligent random effects structure recommendation
- DiagnosticsEngine: Comprehensive model validation and assumption checking
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Union, Any
import warnings
from pathlib import Path
import logging

# R integration
try:
    import rpy2.robjects as ro
    from rpy2.robjects import pandas2ri, Formula
    from rpy2.robjects.packages import importr
    from rpy2.robjects.conversion import localconverter
    R_AVAILABLE = True
    
    # Import R packages
    base = importr('base')
    stats = importr('stats')
    utils = importr('utils')
    
    # Try to import lme4
    try:
        lme4 = importr('lme4')
        LME4_AVAILABLE = True
    except Exception as e:
        LME4_AVAILABLE = False
        warnings.warn(f"lme4 package not available: {e}")
    
    # Enable automatic pandas-R conversion
    pandas2ri.activate()
    
except ImportError:
    R_AVAILABLE = False
    LME4_AVAILABLE = False
    warnings.warn("rpy2 not available. Mixed-effects modeling requires rpy2 and R with lme4 package.")

# Import core locomotion functionality
try:
    from .locomotion_analysis import LocomotionData
    from .feature_constants import ANGLE_FEATURES, MOMENT_FEATURES, VELOCITY_FEATURES
except ImportError:
    from locomotion_analysis import LocomotionData
    from feature_constants import ANGLE_FEATURES, MOMENT_FEATURES, VELOCITY_FEATURES


class MixedEffectsManager:
    """
    Main interface for mixed-effects modeling of biomechanical data.
    
    Provides high-level methods for common biomechanical research questions
    while maintaining flexibility for custom analyses.
    """
    
    def __init__(self, locomotion_data: LocomotionData):
        """
        Initialize mixed-effects manager with locomotion data.
        
        Parameters
        ----------
        locomotion_data : LocomotionData
            Loaded locomotion data instance
        """
        if not R_AVAILABLE:
            raise ImportError("R integration not available. Install rpy2 and R with lme4 package.")
        
        if not LME4_AVAILABLE:
            raise ImportError("lme4 package not available in R. Install with: install.packages('lme4')")
        
        self.loco_data = locomotion_data
        self.models = {}  # Store fitted models
        self.model_summaries = {}  # Store model summaries
        self.logger = logging.getLogger(__name__)
        
        # Initialize model components
        self.templates = BiomechanicalModels(self)
        self.comparison = ModelComparison(self)
        self.optimizer = RandomEffectsOptimizer(self)
        self.diagnostics = DiagnosticsEngine(self)
        
    def prepare_data_for_modeling(self, subjects: Optional[List[str]] = None,
                                tasks: Optional[List[str]] = None,
                                features: Optional[List[str]] = None,
                                include_phase: bool = True,
                                long_format: bool = True) -> pd.DataFrame:
        """
        Prepare biomechanical data for mixed-effects modeling.
        
        Parameters
        ----------
        subjects : list of str, optional
            Subjects to include. If None, includes all subjects.
        tasks : list of str, optional
            Tasks to include. If None, includes all tasks.
        features : list of str, optional
            Features to include. If None, includes all available features.
        include_phase : bool
            Whether to include phase as a predictor
        long_format : bool
            Whether to return data in long format (required for mixed-effects models)
            
        Returns
        -------
        pd.DataFrame
            Data formatted for mixed-effects modeling
        """
        # Get subjects and tasks
        if subjects is None:
            subjects = self.loco_data.get_subjects()
        if tasks is None:
            tasks = self.loco_data.get_tasks()
        if features is None:
            features = self.loco_data.features
            
        # Prepare data list
        data_list = []
        
        for subject in subjects:
            for task in tasks:
                # Get 3D data
                data_3d, feature_names = self.loco_data.get_cycles(subject, task, features)
                
                if data_3d is None:
                    continue
                    
                n_cycles, n_phases, n_features = data_3d.shape
                
                # Create long format data
                for cycle in range(n_cycles):
                    for phase in range(n_phases):
                        row_data = {
                            'subject': subject,
                            'task': task,
                            'cycle': cycle + 1,
                            'phase': phase + 1 if include_phase else None,
                            'phase_percent': (phase / n_phases) * 100 if include_phase else None
                        }
                        
                        # Add feature values
                        for feat_idx, feature in enumerate(feature_names):
                            row_data[feature] = data_3d[cycle, phase, feat_idx]
                            
                        data_list.append(row_data)
        
        df = pd.DataFrame(data_list)
        
        # Add derived variables for common analyses
        df['subject_factor'] = df['subject'].astype('category')
        df['task_factor'] = df['task'].astype('category')
        df['cycle_factor'] = df['cycle'].astype('category')
        
        # Add phase-based variables if requested
        if include_phase:
            df['phase_sin'] = np.sin(2 * np.pi * df['phase_percent'] / 100)
            df['phase_cos'] = np.cos(2 * np.pi * df['phase_percent'] / 100)
            df['phase_factor'] = df['phase'].astype('category')
            
        return df
    
    def fit_basic_hierarchical_model(self, outcome: str, predictors: List[str],
                                   random_effects: str = "(1|subject)",
                                   data: Optional[pd.DataFrame] = None,
                                   model_name: str = "basic_model") -> Dict[str, Any]:
        """
        Fit a basic hierarchical model with specified predictors and random effects.
        
        Parameters
        ----------
        outcome : str
            Outcome variable name
        predictors : list of str
            Fixed effects predictors
        random_effects : str
            Random effects specification in lme4 format
        data : pd.DataFrame, optional
            Data to use. If None, prepares data automatically.
        model_name : str
            Name to store model under
            
        Returns
        -------
        dict
            Model results including fit, summary, and diagnostics
        """
        if data is None:
            data = self.prepare_data_for_modeling()
            
        # Create formula
        fixed_effects = " + ".join(predictors)
        formula_str = f"{outcome} ~ {fixed_effects} + {random_effects}"
        
        try:
            # Convert data to R
            with localconverter(ro.default_converter + pandas2ri.converter):
                r_data = ro.conversion.py2rpy(data)
            
            # Fit model
            ro.globalenv['model_data'] = r_data
            ro.globalenv['formula_str'] = formula_str
            
            # Use lme4::lmer
            r_code = f"""
            library(lme4)
            model <- lmer({formula_str}, data = model_data, REML = TRUE)
            model_summary <- summary(model)
            """
            
            result = ro.r(r_code)
            model = ro.globalenv['model']
            summary_obj = ro.globalenv['model_summary']
            
            # Extract results
            results = {
                'model': model,
                'summary': summary_obj,
                'formula': formula_str,
                'outcome': outcome,
                'predictors': predictors,
                'random_effects': random_effects,
                'data_shape': data.shape,
                'converged': self._check_convergence(model),
                'aic': float(ro.r('AIC(model)')[0]),
                'bic': float(ro.r('BIC(model)')[0]),
                'loglik': float(ro.r('logLik(model)')[0])
            }
            
            # Store model
            self.models[model_name] = results
            
            self.logger.info(f"Successfully fitted model '{model_name}': {formula_str}")
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to fit model '{model_name}': {str(e)}")
            raise RuntimeError(f"Model fitting failed: {str(e)}")
    
    def _check_convergence(self, model) -> bool:
        """Check if lme4 model converged properly."""
        try:
            # Check convergence code
            conv_code = ro.r('model@optinfo$conv$opt')[0]
            return conv_code == 0
        except:
            return False
    
    def get_model_summary(self, model_name: str) -> Dict[str, Any]:
        """Get comprehensive summary of fitted model."""
        if model_name not in self.models:
            raise ValueError(f"Model '{model_name}' not found.")
            
        model_info = self.models[model_name]
        
        # Extract detailed summary information
        summary_info = {
            'formula': model_info['formula'],
            'converged': model_info['converged'],
            'aic': model_info['aic'],
            'bic': model_info['bic'],
            'loglik': model_info['loglik'],
            'n_observations': model_info['data_shape'][0]
        }
        
        # Get fixed effects
        try:
            ro.globalenv['current_model'] = model_info['model']
            fixed_effects = ro.r('fixef(current_model)')
            summary_info['fixed_effects'] = dict(zip(fixed_effects.names, list(fixed_effects)))
        except:
            summary_info['fixed_effects'] = {}
            
        # Get random effects variance
        try:
            random_var = ro.r('VarCorr(current_model)')
            summary_info['random_effects_variance'] = str(random_var)
        except:
            summary_info['random_effects_variance'] = "Not available"
            
        return summary_info


class BiomechanicalModels:
    """Pre-built model templates for common biomechanical analyses."""
    
    def __init__(self, manager: MixedEffectsManager):
        self.manager = manager
    
    def gait_analysis_model(self, outcome: str, tasks: List[str] = None,
                          include_phase: bool = True,
                          model_name: str = "gait_analysis") -> Dict[str, Any]:
        """
        Fit a standard gait analysis model comparing tasks across the gait cycle.
        
        Parameters
        ----------
        outcome : str
            Joint angle, moment, or other biomechanical outcome
        tasks : list of str, optional
            Tasks to compare. If None, uses all available tasks.
        include_phase : bool
            Whether to model phase-dependent effects
        model_name : str
            Name to store model under
            
        Returns
        -------
        dict
            Model results
        """
        # Prepare data
        data = self.manager.prepare_data_for_modeling(
            tasks=tasks, features=[outcome], include_phase=include_phase
        )
        
        # Build predictors
        predictors = ['task_factor']
        if include_phase:
            predictors.extend(['phase_sin', 'phase_cos', 'task_factor:phase_sin', 'task_factor:phase_cos'])
        
        # Random effects: subject-specific intercepts and phase effects
        if include_phase:
            random_effects = "(phase_sin + phase_cos | subject)"
        else:
            random_effects = "(1 | subject)"
            
        return self.manager.fit_basic_hierarchical_model(
            outcome=outcome,
            predictors=predictors,
            random_effects=random_effects,
            data=data,
            model_name=model_name
        )
    
    def intervention_effect_model(self, outcome: str, 
                                pre_tasks: List[str], post_tasks: List[str],
                                model_name: str = "intervention_effect") -> Dict[str, Any]:
        """
        Model intervention effects (pre/post comparison).
        
        Parameters
        ----------
        outcome : str
            Biomechanical outcome variable
        pre_tasks : list of str
            Pre-intervention task names
        post_tasks : list of str
            Post-intervention task names
        model_name : str
            Name to store model under
            
        Returns
        -------
        dict
            Model results
        """
        # Prepare data with intervention coding
        all_tasks = pre_tasks + post_tasks
        data = self.manager.prepare_data_for_modeling(
            tasks=all_tasks, features=[outcome], include_phase=True
        )
        
        # Add intervention coding
        data['intervention'] = data['task'].apply(
            lambda x: 'post' if x in post_tasks else 'pre'
        ).astype('category')
        
        # Model with intervention, phase, and their interaction
        predictors = ['intervention', 'phase_sin', 'phase_cos', 
                     'intervention:phase_sin', 'intervention:phase_cos']
        
        # Random effects: subject-specific intervention and phase effects
        random_effects = "(intervention + phase_sin + phase_cos | subject)"
        
        return self.manager.fit_basic_hierarchical_model(
            outcome=outcome,
            predictors=predictors,
            random_effects=random_effects,
            data=data,
            model_name=model_name
        )
    
    def subject_group_comparison_model(self, outcome: str, group_info: Dict[str, str],
                                     model_name: str = "group_comparison") -> Dict[str, Any]:
        """
        Compare different subject groups (e.g., healthy vs. pathological).
        
        Parameters
        ----------
        outcome : str
            Biomechanical outcome variable
        group_info : dict
            Dictionary mapping subject IDs to group labels
        model_name : str
            Name to store model under
            
        Returns
        -------
        dict
            Model results
        """
        # Prepare data
        subjects_with_groups = list(group_info.keys())
        data = self.manager.prepare_data_for_modeling(
            subjects=subjects_with_groups, features=[outcome], include_phase=True
        )
        
        # Add group information
        data['group'] = data['subject'].map(group_info).astype('category')
        
        # Model with group, phase, and their interaction
        predictors = ['group', 'phase_sin', 'phase_cos', 
                     'group:phase_sin', 'group:phase_cos']
        
        # Random effects: subject-specific intercepts and phase effects within groups
        random_effects = "(phase_sin + phase_cos | subject)"
        
        return self.manager.fit_basic_hierarchical_model(
            outcome=outcome,
            predictors=predictors,
            random_effects=random_effects,
            data=data,
            model_name=model_name
        )


class ModelComparison:
    """Automated model comparison and selection tools."""
    
    def __init__(self, manager: MixedEffectsManager):
        self.manager = manager
    
    def compare_models(self, model_names: List[str]) -> pd.DataFrame:
        """
        Compare multiple fitted models using information criteria.
        
        Parameters
        ----------
        model_names : list of str
            Names of fitted models to compare
            
        Returns
        -------
        pd.DataFrame
            Comparison table with AIC, BIC, and other metrics
        """
        comparison_data = []
        
        for name in model_names:
            if name not in self.manager.models:
                warnings.warn(f"Model '{name}' not found, skipping.")
                continue
                
            model_info = self.manager.models[name]
            comparison_data.append({
                'model': name,
                'formula': model_info['formula'],
                'aic': model_info['aic'],
                'bic': model_info['bic'],  
                'loglik': model_info['loglik'],
                'converged': model_info['converged'],
                'n_obs': model_info['data_shape'][0]
            })
        
        df = pd.DataFrame(comparison_data)
        
        # Add ranking columns
        df['aic_rank'] = df['aic'].rank()
        df['bic_rank'] = df['bic'].rank()
        df['delta_aic'] = df['aic'] - df['aic'].min()
        df['delta_bic'] = df['bic'] - df['bic'].min()
        
        return df.sort_values('aic')
    
    def likelihood_ratio_test(self, model1_name: str, model2_name: str) -> Dict[str, Any]:
        """
        Perform likelihood ratio test between nested models.
        
        Parameters
        ----------
        model1_name : str
            Name of first model (typically simpler)
        model2_name : str
            Name of second model (typically more complex)
            
        Returns
        -------
        dict
            Test results including chi-square statistic and p-value
        """
        if model1_name not in self.manager.models or model2_name not in self.manager.models:
            raise ValueError("Both models must be fitted first.")
        
        try:
            # Set up models in R environment
            ro.globalenv['model1'] = self.manager.models[model1_name]['model']
            ro.globalenv['model2'] = self.manager.models[model2_name]['model']
            
            # Perform LRT
            lrt_result = ro.r('anova(model1, model2)')
            
            # Extract results
            chi_sq = float(lrt_result.rx2('Chisq')[1])  # Second element (first is NA)
            p_value = float(lrt_result.rx2('Pr(>Chisq)')[1])
            df = int(lrt_result.rx2('Df')[1])
            
            return {
                'model1': model1_name,
                'model2': model2_name,
                'chi_square': chi_sq,
                'df': df,
                'p_value': p_value,
                'significant': p_value < 0.05,
                'interpretation': f"Model {model2_name} is {'significantly' if p_value < 0.05 else 'not significantly'} better than {model1_name}"
            }
            
        except Exception as e:
            raise RuntimeError(f"Likelihood ratio test failed: {str(e)}")


class RandomEffectsOptimizer:
    """Intelligent random effects structure recommendation."""
    
    def __init__(self, manager: MixedEffectsManager):
        self.manager = manager
    
    def recommend_random_effects(self, outcome: str, predictors: List[str],
                                data: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """
        Recommend optimal random effects structure based on data characteristics.
        
        Parameters
        ----------
        outcome : str
            Outcome variable
        predictors : list of str
            Fixed effects predictors
        data : pd.DataFrame, optional
            Data to analyze. If None, prepares automatically.
            
        Returns
        -------
        dict
            Recommendations with justification
        """
        if data is None:
            data = self.manager.prepare_data_for_modeling(features=[outcome])
        
        # Data characteristics analysis
        n_subjects = data['subject'].nunique()
        n_obs_per_subject = data.groupby('subject').size()
        has_tasks = 'task' in predictors or 'task_factor' in predictors
        has_phase = any('phase' in pred for pred in predictors)
        
        recommendations = {
            'data_summary': {
                'n_subjects': n_subjects,
                'mean_obs_per_subject': n_obs_per_subject.mean(),
                'min_obs_per_subject': n_obs_per_subject.min(),
                'max_obs_per_subject': n_obs_per_subject.max()
            },
            'recommendations': []
        }
        
        # Basic recommendation: random intercept
        recommendations['recommendations'].append({
            'structure': "(1 | subject)",
            'description': "Random intercept for subjects",
            'rationale': "Accounts for baseline differences between subjects",
            'complexity': 1
        })
        
        # If sufficient data, recommend random slopes
        if n_obs_per_subject.min() >= 10:
            if has_phase:
                recommendations['recommendations'].append({
                    'structure': "(phase_sin + phase_cos | subject)",
                    'description': "Random phase effects for subjects",
                    'rationale': "Accounts for individual differences in gait patterns across the cycle",
                    'complexity': 3
                })
            
            if has_tasks and data.groupby(['subject', 'task']).ngroups >= n_subjects * 2:
                recommendations['recommendations'].append({
                    'structure': "(1 + task_factor | subject)",
                    'description': "Random intercept and task effects for subjects",
                    'rationale': "Accounts for individual responses to different tasks",
                    'complexity': 2
                })
        
        # Full model if very rich data
        if n_obs_per_subject.min() >= 30 and has_phase and has_tasks:
            recommendations['recommendations'].append({
                'structure': "(task_factor + phase_sin + phase_cos | subject)",
                'description': "Full random effects model",
                'rationale': "Comprehensive individual differences modeling",
                'complexity': 4
            })
        
        return recommendations
    
    def test_random_effects_structures(self, outcome: str, predictors: List[str],
                                     structures: List[str],
                                     data: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Test multiple random effects structures and compare them.
        
        Parameters
        ----------
        outcome : str
            Outcome variable
        predictors : list of str
            Fixed effects predictors
        structures : list of str
            Random effects structures to test
        data : pd.DataFrame, optional
            Data to use
            
        Returns
        -------
        pd.DataFrame
            Comparison of different random effects structures
        """
        results = []
        
        for i, structure in enumerate(structures):
            model_name = f"re_test_{i}"
            
            try:
                model_result = self.manager.fit_basic_hierarchical_model(
                    outcome=outcome,
                    predictors=predictors,
                    random_effects=structure,
                    data=data,
                    model_name=model_name
                )
                
                results.append({
                    'structure': structure,
                    'aic': model_result['aic'],
                    'bic': model_result['bic'],
                    'loglik': model_result['loglik'],
                    'converged': model_result['converged'],
                    'model_name': model_name
                })
                
            except Exception as e:
                results.append({
                    'structure': structure,
                    'aic': np.nan,
                    'bic': np.nan,
                    'loglik': np.nan,
                    'converged': False,
                    'error': str(e),
                    'model_name': model_name
                })
        
        df = pd.DataFrame(results)
        
        # Add rankings for converged models
        converged_mask = df['converged']
        if converged_mask.sum() > 0:
            df.loc[converged_mask, 'aic_rank'] = df.loc[converged_mask, 'aic'].rank()
            df.loc[converged_mask, 'bic_rank'] = df.loc[converged_mask, 'bic'].rank()
        
        return df.sort_values('aic', na_last=True)


class DiagnosticsEngine:
    """Comprehensive model validation and assumption checking."""
    
    def __init__(self, manager: MixedEffectsManager):
        self.manager = manager
    
    def run_diagnostics(self, model_name: str) -> Dict[str, Any]:
        """
        Run comprehensive diagnostics on a fitted model.
        
        Parameters
        ----------
        model_name : str
            Name of fitted model to diagnose
            
        Returns
        -------
        dict
            Comprehensive diagnostics results
        """
        if model_name not in self.manager.models:
            raise ValueError(f"Model '{model_name}' not found.")
        
        model_info = self.manager.models[model_name]
        
        # Set up model in R environment
        ro.globalenv['diag_model'] = model_info['model']
        
        diagnostics = {
            'model_name': model_name,
            'convergence': model_info['converged'],
            'warnings': []
        }
        
        try:
            # Residual analysis
            ro.r('residuals_val <- residuals(diag_model)')
            ro.r('fitted_val <- fitted(diag_model)')
            
            residuals = np.array(ro.globalenv['residuals_val'])
            fitted = np.array(ro.globalenv['fitted_val'])
            
            diagnostics['residuals'] = {
                'mean': float(np.mean(residuals)),
                'std': float(np.std(residuals)),
                'min': float(np.min(residuals)),
                'max': float(np.max(residuals)),
                'range': float(np.max(residuals) - np.min(residuals))
            }
            
            # Check for patterns in residuals
            if abs(diagnostics['residuals']['mean']) > 0.01:
                diagnostics['warnings'].append("Residuals do not center around zero")
            
            # Random effects diagnostics
            try:
                ro.r('ranef_val <- ranef(diag_model)')
                diagnostics['random_effects_available'] = True
            except:
                diagnostics['random_effects_available'] = False
                diagnostics['warnings'].append("Could not extract random effects")
            
            # Model summary statistics
            diagnostics['fit_statistics'] = {
                'aic': model_info['aic'],
                'bic': model_info['bic'],
                'loglik': model_info['loglik'],
                'n_observations': model_info['data_shape'][0]
            }
            
        except Exception as e:
            diagnostics['error'] = str(e)
            diagnostics['warnings'].append(f"Diagnostics failed: {str(e)}")
        
        return diagnostics
    
    def check_assumptions(self, model_name: str) -> Dict[str, Any]:
        """
        Check key assumptions of mixed-effects models.
        
        Parameters
        ----------
        model_name : str
            Name of fitted model
            
        Returns
        -------
        dict
            Assumption checking results
        """
        diagnostics = self.run_diagnostics(model_name)
        
        assumptions = {
            'linearity': 'Unknown',
            'independence': 'Unknown', 
            'homoscedasticity': 'Unknown',
            'normality_residuals': 'Unknown',
            'normality_random_effects': 'Unknown',
            'overall_assessment': 'Unknown'
        }
        
        # Basic checks based on available diagnostics
        if 'residuals' in diagnostics:
            # Rough check for extreme residuals (potential outliers)
            res_std = diagnostics['residuals']['std']
            res_range = diagnostics['residuals']['range']
            
            if res_range > 6 * res_std:
                assumptions['homoscedasticity'] = 'Potential issues - large residual range'
            else:
                assumptions['homoscedasticity'] = 'Appears satisfactory'
        
        # Check convergence as indicator of model appropriateness
        if diagnostics['convergence']:
            assumptions['overall_assessment'] = 'Model converged successfully'
        else:
            assumptions['overall_assessment'] = 'Model convergence issues detected'
        
        return assumptions


# Example usage and demonstration functions
def example_gait_analysis():
    """Example of using mixed-effects models for gait analysis."""
    if not R_AVAILABLE or not LME4_AVAILABLE:
        print("R integration not available. Install rpy2 and R with lme4 package.")
        return
    
    print("Mixed-Effects Modeling Example")
    print("=" * 40)
    print("This example demonstrates advanced mixed-effects modeling for biomechanical data.")
    print("Key features:")
    print("- Hierarchical data modeling (subjects, trials, phases)")
    print("- Biomechanics-specific model templates")
    print("- Automated model comparison and selection")
    print("- Random effects optimization")
    print("- Comprehensive model diagnostics")
    print()
    print("To use this functionality:")
    print("1. Load your locomotion data: loco = LocomotionData('data.parquet')")
    print("2. Initialize manager: me_manager = MixedEffectsManager(loco)")
    print("3. Fit models: results = me_manager.templates.gait_analysis_model('knee_flexion_angle_ipsi_rad')")
    print("4. Compare models: comparison = me_manager.comparison.compare_models(['model1', 'model2'])")


if __name__ == '__main__':
    example_gait_analysis()