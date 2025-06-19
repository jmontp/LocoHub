# Validation Explorer

**Interactive exploration of data quality metrics, validation results, and quality assurance workflows.**

<div class="validation-features" markdown>
:material-shield-check: **Quality Assessment** - Comprehensive data quality evaluation  
:material-chart-line: **Interactive Visualization** - Real-time exploration of validation results  
:material-alert-octagon: **Issue Detection** - Automated identification of data quality problems  
:material-wrench: **Quality Improvement** - Actionable recommendations for data enhancement  
</div>

## Validation Dashboard

### Quick Quality Check {#quick-check}

<div class="validation-container" markdown>

**Time Required:** 5 minutes  
**Purpose:** Rapid assessment of dataset quality and validation status

=== "Python"
    ```python
    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt
    from pathlib import Path
    
    def quick_validation_check(data_file):
        """Perform rapid quality assessment of biomechanical dataset"""
        
        # Load dataset
        data = pd.read_csv(data_file)
        
        print("🔍 QUICK VALIDATION CHECK")
        print("=" * 40)
        
        # Basic structure validation
        print("📊 Dataset Structure:")
        print(f"  Rows: {len(data):,}")
        print(f"  Columns: {len(data.columns)}")
        print(f"  Memory usage: {data.memory_usage().sum() / 1024**2:.1f} MB")
        
        # Missing data check
        missing_data = data.isnull().sum()
        missing_percentage = (missing_data / len(data)) * 100
        
        print("\n🚨 Missing Data Assessment:")
        critical_missing = missing_percentage > 10
        if critical_missing.any():
            print("  ❌ CRITICAL: High missing data detected")
            for col in missing_percentage[critical_missing].index:
                print(f"    {col}: {missing_percentage[col]:.1f}% missing")
        else:
            print("  ✅ Missing data within acceptable limits (<10%)")
        
        # Biomechanical range validation
        angle_columns = [col for col in data.columns if 'angle' in col.lower() and 'rad' in col.lower()]
        force_columns = [col for col in data.columns if 'grf' in col.lower() or 'force' in col.lower()]
        
        print("\n📏 Range Validation:")
        
        # Check angle ranges (convert to degrees for interpretation)
        for col in angle_columns:
            if col in data.columns:
                values_deg = np.degrees(data[col].dropna())
                outliers = ((values_deg < -180) | (values_deg > 180)).sum()
                print(f"  {col}: {outliers} outliers beyond ±180°")
        
        # Check force ranges
        for col in force_columns:
            if col in data.columns:
                values = data[col].dropna()
                negative_forces = (values < 0).sum()
                extreme_forces = (values > 5000).sum()  # Assuming body weight ~700N, 5000N = ~7x BW
                print(f"  {col}: {negative_forces} negative values, {extreme_forces} extreme values (>5000N)")
        
        # Data quality score
        quality_issues = []
        if missing_percentage.max() > 10:
            quality_issues.append("High missing data")
        if any([((np.degrees(data[col].dropna()) < -180) | (np.degrees(data[col].dropna()) > 180)).sum() > 0 
               for col in angle_columns if col in data.columns]):
            quality_issues.append("Invalid angle ranges")
        if any([(data[col].dropna() < 0).sum() > 0 for col in force_columns if col in data.columns]):
            quality_issues.append("Negative force values")
        
        print(f"\n🏆 Quality Score:")
        if len(quality_issues) == 0:
            print("  ✅ EXCELLENT (No major issues detected)")
            quality_grade = "A"
        elif len(quality_issues) <= 2:
            print("  ⚠️ GOOD (Minor issues detected)")
            quality_grade = "B"
        else:
            print("  ❌ POOR (Multiple issues detected)")
            quality_grade = "C"
        
        print(f"  Grade: {quality_grade}")
        if quality_issues:
            print(f"  Issues: {', '.join(quality_issues)}")
        
        return {
            'grade': quality_grade,
            'issues': quality_issues,
            'missing_percentage': missing_percentage.max(),
            'data_shape': data.shape
        }
    
    # Example usage
    validation_result = quick_validation_check('docs/user_guide/docs/tutorials/test_files/locomotion_data.csv')
    
    print("\n🎯 Next Steps:")
    if validation_result['grade'] == 'A':
        print("  ✅ Dataset ready for analysis")
        print("  👉 Proceed to advanced analysis workflows")
    elif validation_result['grade'] == 'B':
        print("  ⚠️ Address minor issues before analysis")
        print("  👉 Review validation details below")
    else:
        print("  ❌ Significant data quality improvements needed")
        print("  👉 Implement data cleaning procedures")
    ```

</div>

### Comprehensive Quality Assessment

<div class="validation-container" markdown>

**Time Required:** 15 minutes  
**Purpose:** Detailed quality analysis with recommendations

=== "Python"
    ```python
    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt
    from scipy import stats
    import warnings
    warnings.filterwarnings('ignore')
    
    def comprehensive_validation(data_file):
        """Comprehensive biomechanical data validation and quality assessment"""
        
        data = pd.read_csv(data_file)
        
        print("🔬 COMPREHENSIVE VALIDATION ANALYSIS")
        print("=" * 50)
        
        validation_report = {
            'basic_stats': {},
            'range_validation': {},
            'temporal_validation': {},
            'signal_quality': {},
            'recommendations': []
        }
        
        # 1. Basic Statistics and Structure
        print("\n1️⃣ DATASET STRUCTURE ANALYSIS")
        
        basic_stats = {
            'n_rows': len(data),
            'n_columns': len(data.columns),
            'n_subjects': data['subject_id'].nunique() if 'subject_id' in data.columns else 1,
            'n_tasks': data['task_id'].nunique() if 'task_id' in data.columns else 1,
            'data_types': data.dtypes.to_dict()
        }
        
        validation_report['basic_stats'] = basic_stats
        
        print(f"  📊 Dimensions: {basic_stats['n_rows']} rows × {basic_stats['n_columns']} columns")
        print(f"  👥 Subjects: {basic_stats['n_subjects']}")
        print(f"  🎯 Tasks: {basic_stats['n_tasks']}")
        
        # Check for appropriate data types
        numeric_columns = ['time_s', 'knee_flexion_angle_rad', 'hip_flexion_angle_rad', 
                          'ankle_flexion_angle_rad', 'vertical_grf_N']
        
        print(f"  🔢 Data Types:")
        for col in numeric_columns:
            if col in data.columns:
                is_numeric = pd.api.types.is_numeric_dtype(data[col])
                print(f"    {col}: {'✅ Numeric' if is_numeric else '❌ Non-numeric'}")
                if not is_numeric:
                    validation_report['recommendations'].append(f"Convert {col} to numeric type")
        
        # 2. Range Validation with Biomechanical Context
        print("\n2️⃣ BIOMECHANICAL RANGE VALIDATION")
        
        # Define physiologically reasonable ranges
        validation_ranges = {
            'knee_flexion_angle_rad': {
                'min': np.radians(-10),   # Slight hyperextension
                'max': np.radians(140),   # Deep flexion
                'typical_min': np.radians(0),
                'typical_max': np.radians(70),
                'unit': 'degrees'
            },
            'hip_flexion_angle_rad': {
                'min': np.radians(-30),   # Extension
                'max': np.radians(120),   # Deep flexion
                'typical_min': np.radians(-10),
                'typical_max': np.radians(45),
                'unit': 'degrees'
            },
            'ankle_flexion_angle_rad': {
                'min': np.radians(-40),   # Plantarflexion
                'max': np.radians(30),    # Dorsiflexion
                'typical_min': np.radians(-20),
                'typical_max': np.radians(20),
                'unit': 'degrees'
            },
            'vertical_grf_N': {
                'min': 0,                 # No negative vertical forces
                'max': 3000,              # ~4x body weight (jumping/running)
                'typical_min': 400,       # Light contact
                'typical_max': 1200,      # Normal walking
                'unit': 'Newtons'
            }
        }
        
        range_results = {}
        
        for variable, ranges in validation_ranges.items():
            if variable in data.columns:
                values = data[variable].dropna()
                
                # Convert angles to degrees for reporting
                if 'angle' in variable:
                    values_display = np.degrees(values)
                    min_range_display = np.degrees(ranges['min'])
                    max_range_display = np.degrees(ranges['max'])
                    typical_min_display = np.degrees(ranges['typical_min'])
                    typical_max_display = np.degrees(ranges['typical_max'])
                else:
                    values_display = values
                    min_range_display = ranges['min']
                    max_range_display = ranges['max']
                    typical_min_display = ranges['typical_min']
                    typical_max_display = ranges['typical_max']
                
                # Check for outliers
                extreme_outliers = ((values < ranges['min']) | (values > ranges['max'])).sum()
                atypical_values = ((values < ranges['typical_min']) | (values > ranges['typical_max'])).sum()
                
                outlier_percentage = extreme_outliers / len(values) * 100
                atypical_percentage = atypical_values / len(values) * 100
                
                range_results[variable] = {
                    'extreme_outliers': extreme_outliers,
                    'outlier_percentage': outlier_percentage,
                    'atypical_values': atypical_values,
                    'atypical_percentage': atypical_percentage,
                    'min_observed': values_display.min(),
                    'max_observed': values_display.max(),
                    'mean_observed': values_display.mean()
                }
                
                # Reporting
                print(f"\n  📏 {variable}:")
                print(f"    Observed range: {values_display.min():.1f} to {values_display.max():.1f} {ranges['unit']}")
                print(f"    Expected range: {min_range_display:.1f} to {max_range_display:.1f} {ranges['unit']}")
                print(f"    Typical range: {typical_min_display:.1f} to {typical_max_display:.1f} {ranges['unit']}")
                
                if extreme_outliers > 0:
                    print(f"    ❌ Extreme outliers: {extreme_outliers} ({outlier_percentage:.1f}%)")
                    validation_report['recommendations'].append(f"Investigate extreme values in {variable}")
                else:
                    print(f"    ✅ No extreme outliers")
                
                if atypical_percentage > 20:
                    print(f"    ⚠️ Atypical values: {atypical_values} ({atypical_percentage:.1f}%)")
                    validation_report['recommendations'].append(f"Review atypical values in {variable}")
                else:
                    print(f"    ✅ Most values within typical range")
        
        validation_report['range_validation'] = range_results
        
        # 3. Temporal Validation
        print("\n3️⃣ TEMPORAL CONSISTENCY VALIDATION")
        
        if 'time_s' in data.columns:
            time_diff = np.diff(data['time_s'])
            
            # Expected sampling rate analysis
            if len(time_diff) > 0:
                median_dt = np.median(time_diff)
                std_dt = np.std(time_diff)
                irregular_samples = np.sum(np.abs(time_diff - median_dt) > median_dt * 0.1)
                
                sampling_rate = 1 / median_dt if median_dt > 0 else 0
                
                temporal_results = {
                    'median_sampling_interval': median_dt,
                    'sampling_rate_hz': sampling_rate,
                    'temporal_std': std_dt,
                    'irregular_samples': irregular_samples,
                    'irregularity_percentage': irregular_samples / len(time_diff) * 100
                }
                
                validation_report['temporal_validation'] = temporal_results
                
                print(f"  ⏱️ Sampling Analysis:")
                print(f"    Median interval: {median_dt:.4f} s")
                print(f"    Sampling rate: {sampling_rate:.1f} Hz")
                print(f"    Temporal variability: {std_dt:.6f} s")
                print(f"    Irregular samples: {irregular_samples}/{len(time_diff)} ({irregular_samples/len(time_diff)*100:.1f}%)")
                
                if irregular_samples / len(time_diff) > 0.05:
                    print(f"    ⚠️ High temporal irregularity detected")
                    validation_report['recommendations'].append("Review temporal sampling consistency")
                else:
                    print(f"    ✅ Temporal sampling is consistent")
        
        # 4. Signal Quality Assessment
        print("\n4️⃣ SIGNAL QUALITY ASSESSMENT")
        
        signal_vars = ['knee_flexion_angle_rad', 'hip_flexion_angle_rad', 'vertical_grf_N']
        signal_results = {}
        
        for variable in signal_vars:
            if variable in data.columns:
                signal = data[variable].dropna()
                
                if len(signal) > 10:
                    # Signal-to-noise ratio estimation
                    signal_power = np.var(signal)
                    
                    # Estimate noise from high-frequency components
                    diff_signal = np.diff(signal)
                    noise_power = np.var(diff_signal) / 2
                    
                    snr_db = 10 * np.log10(signal_power / noise_power) if noise_power > 0 else float('inf')
                    
                    # Spike detection (values beyond 3 standard deviations)
                    z_scores = np.abs(stats.zscore(signal))
                    spikes = np.sum(z_scores > 3)
                    spike_percentage = spikes / len(signal) * 100
                    
                    # Flatline detection
                    consecutive_identical = 0
                    max_consecutive = 0
                    for i in range(1, len(signal)):
                        if signal.iloc[i] == signal.iloc[i-1]:
                            consecutive_identical += 1
                            max_consecutive = max(max_consecutive, consecutive_identical)
                        else:
                            consecutive_identical = 0
                    
                    signal_results[variable] = {
                        'snr_db': snr_db,
                        'spikes': spikes,
                        'spike_percentage': spike_percentage,
                        'max_consecutive_identical': max_consecutive,
                        'signal_mean': signal.mean(),
                        'signal_std': signal.std()
                    }
                    
                    print(f"\n  📡 {variable}:")
                    print(f"    SNR: {snr_db:.1f} dB")
                    print(f"    Spikes (>3σ): {spikes} ({spike_percentage:.2f}%)")
                    print(f"    Max consecutive identical: {max_consecutive}")
                    
                    # Quality assessment
                    quality_issues = []
                    if snr_db < 15:
                        quality_issues.append("Low SNR")
                    if spike_percentage > 2:
                        quality_issues.append("High spike rate")
                    if max_consecutive > 5:
                        quality_issues.append("Potential flatline segments")
                    
                    if quality_issues:
                        print(f"    ⚠️ Issues: {', '.join(quality_issues)}")
                        validation_report['recommendations'].extend([f"Address {issue} in {variable}" for issue in quality_issues])
                    else:
                        print(f"    ✅ Good signal quality")
        
        validation_report['signal_quality'] = signal_results
        
        # 5. Overall Assessment and Recommendations
        print("\n5️⃣ OVERALL ASSESSMENT")
        
        # Calculate overall quality score
        quality_score = 100
        
        # Deduct points for issues
        if validation_report['recommendations']:
            quality_score -= len(validation_report['recommendations']) * 10
        
        # Range validation impact
        for var, results in range_results.items():
            if results['outlier_percentage'] > 5:
                quality_score -= 20
            elif results['outlier_percentage'] > 1:
                quality_score -= 10
        
        # Signal quality impact
        for var, results in signal_results.items():
            if results['snr_db'] < 15:
                quality_score -= 15
            if results['spike_percentage'] > 2:
                quality_score -= 10
        
        # Temporal quality impact
        if 'temporal_validation' in validation_report:
            if validation_report['temporal_validation']['irregularity_percentage'] > 5:
                quality_score -= 15
        
        quality_score = max(0, quality_score)
        
        print(f"\n  🏆 Overall Quality Score: {quality_score}/100")
        
        if quality_score >= 90:
            grade = "A"
            status = "✅ EXCELLENT - Ready for analysis"
        elif quality_score >= 80:
            grade = "B"
            status = "✅ GOOD - Minor improvements recommended"
        elif quality_score >= 70:
            grade = "C"
            status = "⚠️ ACCEPTABLE - Some improvements needed"
        elif quality_score >= 60:
            grade = "D"
            status = "⚠️ POOR - Significant improvements required"
        else:
            grade = "F"
            status = "❌ FAIL - Major data quality issues"
        
        print(f"  📊 Grade: {grade}")
        print(f"  📝 Status: {status}")
        
        # Priority recommendations
        if validation_report['recommendations']:
            print(f"\n  💡 Priority Recommendations:")
            for i, rec in enumerate(validation_report['recommendations'][:5], 1):
                print(f"    {i}. {rec}")
            if len(validation_report['recommendations']) > 5:
                print(f"    ... and {len(validation_report['recommendations']) - 5} more")
        
        validation_report['overall_score'] = quality_score
        validation_report['grade'] = grade
        
        return validation_report
    
    # Run comprehensive validation
    print("🚀 Running comprehensive validation on test dataset...")
    validation_report = comprehensive_validation('docs/user_guide/docs/tutorials/test_files/locomotion_data.csv')
    
    print(f"\n📋 VALIDATION COMPLETE")
    print(f"Final Grade: {validation_report['grade']} ({validation_report['overall_score']}/100)")
    ```

</div>

### Validation Visualization Dashboard

<div class="validation-container" markdown>

**Time Required:** 10 minutes  
**Purpose:** Visual exploration of validation results

=== "Python"
    ```python
    def create_validation_dashboard(data_file, validation_report):
        """Create comprehensive validation visualization dashboard"""
        
        data = pd.read_csv(data_file)
        
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle('Data Validation Dashboard', fontsize=16)
        
        # Plot 1: Data completeness heatmap
        ax1 = axes[0, 0]
        
        # Calculate missing data percentage for each column
        missing_data = data.isnull().sum() / len(data) * 100
        
        # Create bar plot
        bars = ax1.bar(range(len(missing_data)), missing_data.values, 
                      color=['red' if x > 10 else 'orange' if x > 5 else 'green' for x in missing_data.values])
        
        ax1.set_xlabel('Columns')
        ax1.set_ylabel('Missing Data (%)')
        ax1.set_title('Data Completeness Assessment')
        ax1.set_xticks(range(len(missing_data)))
        ax1.set_xticklabels(missing_data.index, rotation=45, ha='right')
        ax1.axhline(y=5, color='orange', linestyle='--', alpha=0.7, label='5% threshold')
        ax1.axhline(y=10, color='red', linestyle='--', alpha=0.7, label='10% threshold')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Range validation results
        ax2 = axes[0, 1]
        
        if 'range_validation' in validation_report:
            variables = list(validation_report['range_validation'].keys())
            outlier_percentages = [validation_report['range_validation'][var]['outlier_percentage'] 
                                 for var in variables]
            
            bars = ax2.bar(range(len(variables)), outlier_percentages,
                          color=['red' if x > 5 else 'orange' if x > 1 else 'green' for x in outlier_percentages])
            
            ax2.set_xlabel('Variables')
            ax2.set_ylabel('Outlier Percentage (%)')
            ax2.set_title('Range Validation Results')
            ax2.set_xticks(range(len(variables)))
            ax2.set_xticklabels([var.replace('_', '\n') for var in variables], rotation=45, ha='right')
            ax2.axhline(y=1, color='orange', linestyle='--', alpha=0.7, label='1% threshold')
            ax2.axhline(y=5, color='red', linestyle='--', alpha=0.7, label='5% threshold')
            ax2.legend()
            ax2.grid(True, alpha=0.3)
        
        # Plot 3: Signal quality assessment
        ax3 = axes[0, 2]
        
        if 'signal_quality' in validation_report:
            signal_vars = list(validation_report['signal_quality'].keys())
            snr_values = [validation_report['signal_quality'][var]['snr_db'] for var in signal_vars]
            
            bars = ax3.bar(range(len(signal_vars)), snr_values,
                          color=['green' if x > 20 else 'orange' if x > 15 else 'red' for x in snr_values])
            
            ax3.set_xlabel('Variables')
            ax3.set_ylabel('SNR (dB)')
            ax3.set_title('Signal Quality (SNR)')
            ax3.set_xticks(range(len(signal_vars)))
            ax3.set_xticklabels([var.replace('_', '\n') for var in signal_vars], rotation=45, ha='right')
            ax3.axhline(y=15, color='orange', linestyle='--', alpha=0.7, label='15 dB threshold')
            ax3.axhline(y=20, color='green', linestyle='--', alpha=0.7, label='20 dB threshold')
            ax3.legend()
            ax3.grid(True, alpha=0.3)
        
        # Plot 4: Temporal consistency
        ax4 = axes[1, 0]
        
        if 'time_s' in data.columns:
            time_diff = np.diff(data['time_s'])
            
            ax4.plot(time_diff * 1000, 'b-', linewidth=1, alpha=0.7)
            ax4.set_xlabel('Sample Index')
            ax4.set_ylabel('Time Interval (ms)')
            ax4.set_title('Temporal Sampling Consistency')
            
            if len(time_diff) > 0:
                median_dt = np.median(time_diff) * 1000
                ax4.axhline(y=median_dt, color='red', linestyle='--', alpha=0.7, 
                           label=f'Median: {median_dt:.1f}ms')
                ax4.legend()
            
            ax4.grid(True, alpha=0.3)
        
        # Plot 5: Distribution analysis
        ax5 = axes[1, 1]
        
        # Focus on knee flexion for distribution analysis
        if 'knee_flexion_angle_rad' in data.columns:
            knee_deg = np.degrees(data['knee_flexion_angle_rad'].dropna())
            
            ax5.hist(knee_deg, bins=20, alpha=0.7, color='skyblue', density=True)
            ax5.axvline(x=knee_deg.mean(), color='red', linestyle='--', linewidth=2, 
                       label=f'Mean: {knee_deg.mean():.1f}°')
            ax5.axvline(x=knee_deg.mean() + 2*knee_deg.std(), color='orange', 
                       linestyle='--', alpha=0.7, label='±2σ')
            ax5.axvline(x=knee_deg.mean() - 2*knee_deg.std(), color='orange', 
                       linestyle='--', alpha=0.7)
            
            ax5.set_xlabel('Knee Flexion (degrees)')
            ax5.set_ylabel('Probability Density')
            ax5.set_title('Distribution Analysis')
            ax5.legend()
            ax5.grid(True, alpha=0.3)
        
        # Plot 6: Overall quality summary
        ax6 = axes[1, 2]
        
        # Create quality score visualization
        score = validation_report['overall_score']
        grade = validation_report['grade']
        
        # Donut chart for quality score
        sizes = [score, 100 - score]
        colors = ['green' if score >= 80 else 'orange' if score >= 60 else 'red', 'lightgray']
        
        wedges, texts = ax6.pie(sizes, colors=colors, startangle=90, counterclock=False)
        
        # Add center text
        ax6.text(0, 0, f'{score}\n{grade}', ha='center', va='center', 
                fontsize=20, fontweight='bold')
        
        ax6.set_title('Overall Quality Score')
        
        # Add recommendations text
        if validation_report['recommendations']:
            recommendations_text = "Top Issues:\n" + "\n".join([f"• {rec}" for rec in validation_report['recommendations'][:3]])
            if len(validation_report['recommendations']) > 3:
                recommendations_text += f"\n... and {len(validation_report['recommendations']) - 3} more"
            
            plt.figtext(0.02, 0.02, recommendations_text, fontsize=9, 
                       bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8),
                       verticalalignment='bottom')
        
        plt.tight_layout()
        plt.subplots_adjust(bottom=0.15)  # Make room for recommendations
        plt.savefig('validation_dashboard.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        print("📊 Validation dashboard created!")
        print("📁 Saved as 'validation_dashboard.png'")
    
    # Create the validation dashboard
    print("\n🎨 Creating validation visualization dashboard...")
    create_validation_dashboard('docs/user_guide/docs/tutorials/test_files/locomotion_data.csv', validation_report)
    ```

</div>

### Automated Quality Improvement

<div class="validation-container" markdown>

**Time Required:** 20 minutes  
**Purpose:** Automated data cleaning and quality enhancement

=== "Python"
    ```python
    def automated_quality_improvement(data_file, validation_report):
        """Automated data quality improvement based on validation results"""
        
        data = pd.read_csv(data_file)
        original_data = data.copy()
        
        print("🔧 AUTOMATED QUALITY IMPROVEMENT")
        print("=" * 50)
        
        improvements_made = []
        
        # 1. Handle missing data
        print("\n1️⃣ ADDRESSING MISSING DATA")
        
        missing_threshold = 5  # 5% threshold for interpolation
        
        for column in data.columns:
            if data[column].isnull().sum() > 0:
                missing_percentage = data[column].isnull().sum() / len(data) * 100
                
                if missing_percentage <= missing_threshold:
                    # Interpolate small amounts of missing data
                    if pd.api.types.is_numeric_dtype(data[column]):
                        data[column] = data[column].interpolate(method='linear')
                        improvements_made.append(f"Interpolated {missing_percentage:.1f}% missing values in {column}")
                        print(f"  ✅ Interpolated {missing_percentage:.1f}% missing values in {column}")
                    else:
                        # Forward fill for non-numeric data
                        data[column] = data[column].fillna(method='ffill')
                        improvements_made.append(f"Forward-filled missing values in {column}")
                        print(f"  ✅ Forward-filled missing values in {column}")
                else:
                    print(f"  ⚠️ {column}: {missing_percentage:.1f}% missing (exceeds threshold, manual review needed)")
        
        # 2. Outlier handling
        print("\n2️⃣ OUTLIER DETECTION AND HANDLING")
        
        angle_columns = [col for col in data.columns if 'angle' in col.lower() and 'rad' in col.lower()]
        force_columns = [col for col in data.columns if 'grf' in col.lower() or 'force' in col.lower()]
        
        for column in angle_columns + force_columns:
            if column in data.columns and pd.api.types.is_numeric_dtype(data[column]):
                values = data[column].dropna()
                
                # Use IQR method for outlier detection
                Q1 = values.quantile(0.25)
                Q3 = values.quantile(0.75)
                IQR = Q3 - Q1
                
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                
                outliers_mask = (data[column] < lower_bound) | (data[column] > upper_bound)
                n_outliers = outliers_mask.sum()
                
                if n_outliers > 0:
                    outlier_percentage = n_outliers / len(data) * 100
                    
                    if outlier_percentage <= 2:  # Only auto-fix if <2% outliers
                        # Cap outliers to bounds
                        data.loc[data[column] < lower_bound, column] = lower_bound
                        data.loc[data[column] > upper_bound, column] = upper_bound
                        
                        improvements_made.append(f"Capped {n_outliers} outliers in {column}")
                        print(f"  ✅ Capped {n_outliers} outliers ({outlier_percentage:.1f}%) in {column}")
                    else:
                        print(f"  ⚠️ {column}: {n_outliers} outliers ({outlier_percentage:.1f}%) - manual review recommended")
        
        # 3. Signal smoothing for noisy data
        print("\n3️⃣ SIGNAL QUALITY ENHANCEMENT")
        
        if 'signal_quality' in validation_report:
            for variable, quality_info in validation_report['signal_quality'].items():
                if quality_info['snr_db'] < 20 and variable in data.columns:  # Low SNR threshold
                    # Apply mild smoothing
                    from scipy.signal import savgol_filter
                    
                    try:
                        original_signal = data[variable].dropna()
                        if len(original_signal) > 10:  # Need sufficient data for smoothing
                            # Use Savitzky-Golay filter for mild smoothing
                            window_length = min(7, len(original_signal) // 3)
                            if window_length % 2 == 0:
                                window_length += 1  # Must be odd
                            
                            if window_length >= 3:
                                smoothed = savgol_filter(original_signal, window_length, 2)
                                data.loc[data[variable].notna(), variable] = smoothed
                                
                                improvements_made.append(f"Applied signal smoothing to {variable}")
                                print(f"  ✅ Applied signal smoothing to {variable} (SNR: {quality_info['snr_db']:.1f} dB)")
                    except Exception as e:
                        print(f"  ⚠️ Could not smooth {variable}: {str(e)}")
        
        # 4. Temporal consistency improvement
        print("\n4️⃣ TEMPORAL CONSISTENCY ENHANCEMENT")
        
        if 'time_s' in data.columns:
            time_values = data['time_s']
            time_diff = np.diff(time_values)
            
            if len(time_diff) > 0:
                median_dt = np.median(time_diff)
                
                # Check for large gaps or irregularities
                irregular_mask = np.abs(time_diff - median_dt) > median_dt * 0.5
                n_irregular = irregular_mask.sum()
                
                if n_irregular > 0 and n_irregular / len(time_diff) < 0.1:  # <10% irregular
                    # Attempt to regularize time series
                    regular_time = np.arange(time_values.iloc[0], 
                                           time_values.iloc[-1] + median_dt, 
                                           median_dt)
                    
                    if len(regular_time) == len(data):
                        data['time_s'] = regular_time
                        improvements_made.append("Regularized temporal sampling")
                        print(f"  ✅ Regularized temporal sampling ({n_irregular} irregular intervals)")
                    else:
                        print(f"  ⚠️ Could not regularize time series (length mismatch)")
        
        # 5. Data type optimization
        print("\n5️⃣ DATA TYPE OPTIMIZATION")
        
        # Convert appropriate columns to optimal data types
        for column in data.columns:
            if column in ['subject_id', 'task_id', 'step_id']:
                # Convert IDs to category to save memory
                data[column] = data[column].astype('category')
                improvements_made.append(f"Optimized data type for {column}")
                print(f"  ✅ Converted {column} to category type")
            elif pd.api.types.is_numeric_dtype(data[column]):
                # Check if we can use float32 instead of float64
                if data[column].dtype == 'float64':
                    min_val = data[column].min()
                    max_val = data[column].max()
                    
                    # Check if values fit in float32 range
                    if (min_val >= np.finfo(np.float32).min and 
                        max_val <= np.finfo(np.float32).max):
                        data[column] = data[column].astype('float32')
                        improvements_made.append(f"Optimized precision for {column}")
                        print(f"  ✅ Optimized precision for {column} (float64 → float32)")
        
        # 6. Summary of improvements
        print("\n6️⃣ IMPROVEMENT SUMMARY")
        
        # Calculate memory savings
        original_memory = original_data.memory_usage().sum() / 1024**2
        improved_memory = data.memory_usage().sum() / 1024**2
        memory_savings = (original_memory - improved_memory) / original_memory * 100
        
        print(f"\n  📊 Results:")
        print(f"    Improvements made: {len(improvements_made)}")
        print(f"    Memory usage: {original_memory:.1f} MB → {improved_memory:.1f} MB ({memory_savings:+.1f}%)")
        
        if improvements_made:
            print(f"\n  ✅ Improvements applied:")
            for improvement in improvements_made:
                print(f"    • {improvement}")
        else:
            print(f"\n  ℹ️ No automated improvements were necessary")
        
        # Save improved dataset
        improved_filename = 'improved_' + data_file.split('/')[-1]
        data.to_csv(improved_filename, index=False)
        print(f"\n  💾 Improved dataset saved as: {improved_filename}")
        
        # Re-run validation on improved dataset
        print(f"\n  🔄 Re-validating improved dataset...")
        
        # Quick validation comparison
        improved_validation = quick_validation_check(improved_filename)
        
        print(f"\n  📈 Quality Improvement:")
        print(f"    Original grade: {validation_report['grade']}")
        print(f"    Improved grade: {improved_validation['grade']}")
        
        if improved_validation['grade'] > validation_report['grade']:
            print(f"    ✅ Quality improved!")
        elif improved_validation['grade'] == validation_report['grade']:
            print(f"    ➖ Quality maintained")
        else:
            print(f"    ⚠️ Unexpected quality change - review recommended")
        
        return data, improvements_made
    
    # Run automated quality improvement
    print("\n🚀 Running automated quality improvement...")
    improved_data, improvements = automated_quality_improvement('docs/user_guide/docs/tutorials/test_files/locomotion_data.csv', validation_report)
    
    print(f"\n🎉 Quality improvement process complete!")
    print(f"Total improvements made: {len(improvements)}")
    ```

</div>

## Validation Workflows

### Clinical Data Validation

For clinical applications, use these additional validation criteria:

- **Patient Safety**: Verify no extreme values that could indicate sensor malfunctions
- **Clinical Relevance**: Ensure measurements align with expected pathological patterns
- **Temporal Consistency**: Validate that improvements/deteriorations follow expected timelines
- **Bilateral Symmetry**: Check for appropriate left-right differences in pathological conditions

### Research Data Validation

For research studies, implement these additional checks:

- **Protocol Compliance**: Verify data collection followed study protocols
- **Statistical Power**: Ensure adequate sample sizes for planned analyses
- **Effect Size Detection**: Validate sensitivity to detect meaningful differences
- **Publication Standards**: Meet journal requirements for data quality reporting

### Multi-Site Validation

For multi-institutional studies:

- **Cross-Site Calibration**: Validate measurement consistency across sites
- **Protocol Standardization**: Ensure uniform data collection procedures
- **Bias Detection**: Identify systematic differences between institutions
- **Harmonization**: Apply standardization procedures when appropriate

## Best Practices

1. **Regular Validation**: Implement validation checks as part of routine data processing
2. **Documentation**: Maintain detailed logs of all validation results and corrections
3. **Version Control**: Track changes made during quality improvement processes
4. **Expert Review**: Have domain experts review validation criteria and results
5. **Continuous Improvement**: Update validation criteria based on new findings and standards

## Next Steps

- **[Advanced Analysis](code_walkthroughs/)** - Use validated data for biomechanical analysis
- **[Case Studies](case_studies/)** - Apply validation in real-world research contexts
- **[Custom Validation](../contributor_guide/validation_tuning/)** - Develop domain-specific validation criteria
- **[Quality Reporting](../reference/validation_reports/)** - Generate comprehensive quality reports

---

*All validation criteria are based on established biomechanical norms and can be customized for specific populations or research contexts. Regular review and updating of validation parameters is recommended.*