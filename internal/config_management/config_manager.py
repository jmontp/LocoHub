#!/usr/bin/env python3
"""
Validation Config Manager

Manages validation range configurations with internal data storage.
Provides a stable API that hides the underlying data structure.
Automatically handles contralateral feature generation.
"""

import yaml
import warnings
from pathlib import Path
from typing import Dict, Optional, Any, Tuple, List
from datetime import datetime


class ValidationConfigManager:
    """
    Manages validation range configurations with internal state.
    
    The internal data structure matches YAML format:
    {
        'task_name': {
            'metadata': {
                'contralateral_offset': bool  # Whether to apply 50% phase offset
            },
            'phases': {
                phase_int: {
                    'variable_name': {'min': float, 'max': float}
                }
            }
        }
    }
    
    Only ipsilateral features are stored. Contralateral features are
    generated automatically based on the metadata flag.
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize the config manager.
        
        Args:
            config_path: Optional path to load initial data from.
                        If None, creates an empty configuration.
        """
        # Internal data storage - nested structure matching YAML
        self._data: Dict[str, Dict[str, Any]] = {}
        self._metadata: Dict[str, Any] = {
            'version': '2.0',
            'generated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Default config directory
        project_root = Path(__file__).parent.parent.parent
        self.config_dir = project_root / "contributor_tools" / "validation_ranges"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Default config file path
        self.default_config_path = self.config_dir / "default_ranges.yaml"
        
        # Load initial data if path provided
        if config_path:
            self.load(config_path)
    
    def load(self, config_path: Optional[Path] = None) -> None:
        """
        Load validation ranges from YAML file into internal storage.
        
        Args:
            config_path: Path to config file. If None, uses default.
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If phase values are invalid
        """
        # Use provided path or default
        if config_path is None:
            config_path = self.default_config_path
        else:
            config_path = Path(config_path)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Clear existing data
        self._data.clear()
        self._metadata.clear()
        
        # Extract metadata (everything except 'tasks')
        for key, value in config.items():
            if key != 'tasks':
                self._metadata[key] = value
        
        # Extract validation ranges with new nested structure
        if 'tasks' in config:
            for task_name, task_data in config['tasks'].items():
                self._data[task_name] = {}
                
                # Handle both old (flat) and new (nested) formats
                if 'phases' in task_data:
                    # New format with metadata
                    self._data[task_name]['metadata'] = task_data.get('metadata', {
                        'contralateral_offset': True  # Default for backward compatibility
                    })
                    phases_data = task_data['phases']
                else:
                    # Old format - assume it's all phase data
                    self._data[task_name]['metadata'] = {
                        'contralateral_offset': True  # Default for backward compatibility
                    }
                    phases_data = task_data
                
                # Process phases
                self._data[task_name]['phases'] = {}
                for phase, variables in phases_data.items():
                    # Handle both string and integer phases
                    if isinstance(phase, str):
                        try:
                            phase = int(phase)
                        except ValueError:
                            raise ValueError(f"Invalid phase '{phase}' in task {task_name}. Phase must be a number.")
                    
                    # Validate phase is between 0-100
                    if not 0 <= phase <= 100:
                        raise ValueError(f"Phase {phase} in task {task_name} is out of range. Must be 0-100.")
                    
                    # Filter out any contra features (shouldn't be in YAML)
                    filtered_vars = {}
                    for var_name, var_range in variables.items():
                        if '_contra' in var_name:
                            warnings.warn(f"Ignoring contralateral feature '{var_name}' in config. "
                                        f"Contralateral features are generated automatically.")
                            continue
                        filtered_vars[var_name] = var_range
                    
                    self._data[task_name]['phases'][phase] = filtered_vars
    
    def save(self, config_path: Optional[Path] = None) -> None:
        """
        Save internal validation ranges to YAML file.
        Only saves ipsilateral features; contralateral are generated.
        
        Args:
            config_path: Path to save to. If None, uses default.
        """
        if config_path is None:
            config_path = self.default_config_path
        else:
            config_path = Path(config_path)
        
        # Build config structure
        config = self._metadata.copy()
        
        # Update generation time
        config['generated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Add validation data - direct serialization of nested structure
        config['tasks'] = {}
        for task_name, task_data in self._data.items():
            config['tasks'][task_name] = {
                'metadata': task_data.get('metadata', {}),
                'phases': {}
            }
            
            # Only save ipsilateral features
            for phase, variables in task_data.get('phases', {}).items():
                filtered_vars = {}
                for var_name, var_range in variables.items():
                    if '_contra' not in var_name:  # Skip any contra that snuck in
                        filtered_vars[var_name] = var_range
                
                if filtered_vars:  # Only add phase if it has variables
                    config['tasks'][task_name]['phases'][phase] = filtered_vars
        
        # Write to file with nice formatting
        with open(config_path, 'w') as f:
            yaml.dump(config, f, 
                     default_flow_style=False, 
                     sort_keys=False,
                     width=120,
                     indent=2)
        
        print(f"✅ Saved validation config to: {config_path}")
    
    def get_range(self, task: str, phase: int, variable: str) -> Optional[Tuple[float, float]]:
        """
        Get min/max range for a specific variable.
        Works for both ipsi and contra variables (contra are generated).
        
        Args:
            task: Task name
            phase: Phase percentage (0-100)
            variable: Variable name (ipsi or contra)
            
        Returns:
            Tuple of (min, max) or None if not found
        """
        try:
            # Get task data with generated contra features
            task_data = self.get_task_data(task)
            if phase in task_data and variable in task_data[phase]:
                range_data = task_data[phase][variable]
                return (range_data['min'], range_data['max'])
            return None
        except (KeyError, TypeError):
            return None
    
    def set_range(self,
                  task: str,
                  phase: int,
                  variable: str,
                  min_val: float,
                  max_val: float) -> None:
        """
        Set min/max range for a specific variable.
        
        If a contralateral variable is provided, it's converted to ipsilateral
        with a warning.
        
        Args:
            task: Task name
            phase: Phase percentage (0-100)
            variable: Variable name
            min_val: Minimum value
            max_val: Maximum value
            
        Raises:
            ValueError: If phase is out of range
        """
        # Check for contralateral variable
        if '_contra' in variable:
            ipsi_var = variable.replace('_contra', '_ipsi')
            warnings.warn(f"Cannot set contralateral feature '{variable}'. "
                         f"Setting ipsilateral equivalent '{ipsi_var}' instead. "
                         f"Contralateral features are generated automatically.")
            variable = ipsi_var
        
        # Ensure phase is an integer
        phase = int(phase) if not isinstance(phase, int) else phase
        
        # Validate phase range
        if not 0 <= phase <= 100:
            raise ValueError(f"Phase {phase} is out of range. Must be 0-100.")
        
        # Ensure nested structure exists
        if task not in self._data:
            self._data[task] = {
                'metadata': {'contralateral_offset': True},  # Default
                'phases': {}
            }
        if 'phases' not in self._data[task]:
            self._data[task]['phases'] = {}
        if phase not in self._data[task]['phases']:
            self._data[task]['phases'][phase] = {}
        if variable not in self._data[task]['phases'][phase]:
            self._data[task]['phases'][phase][variable] = {}
        
        # Set values
        self._data[task]['phases'][phase][variable]['min'] = min_val
        self._data[task]['phases'][phase][variable]['max'] = max_val
    
    def get_tasks(self) -> List[str]:
        """
        Get list of all tasks in the configuration.
        
        Returns:
            List of task names
        """
        return list(self._data.keys())
    
    def get_task_data(self, task: str) -> Dict[int, Dict[str, Dict[str, float]]]:
        """
        Get validation data for a specific task with contralateral features generated.
        
        This returns the phase-indexed validation ranges for a single task,
        with contralateral features automatically generated based on the
        task's metadata settings.
        
        Args:
            task: Task name
            
        Returns:
            Dictionary with structure: {phase: {variable: {min, max}}}
            Includes both ipsi and generated contra features.
        """
        if task not in self._data:
            return {}
        
        task_info = self._data[task]
        phases_data = task_info.get('phases', {})
        metadata = task_info.get('metadata', {})
        
        # Check if we should apply contralateral offset
        apply_offset = metadata.get('contralateral_offset', True)
        
        # Generate contralateral features
        return self._generate_contralateral_features(phases_data, apply_offset)
    
    def _generate_contralateral_features(self, 
                                        phases_data: Dict[int, Dict[str, Dict[str, float]]],
                                        apply_offset: bool) -> Dict[int, Dict[str, Dict[str, float]]]:
        """
        Generate contralateral features from ipsilateral data.
        
        Args:
            phases_data: Dictionary of phases with ipsilateral features
            apply_offset: Whether to apply 50% phase offset for contralateral
            
        Returns:
            Dictionary with both ipsi and generated contra features
        """
        result = {}
        
        # First, copy all ipsi data as-is
        for phase in phases_data:
            result[phase] = phases_data[phase].copy()
        
        # Then, generate contra features at appropriate phases
        for phase in phases_data:
            # Calculate target phase for contralateral features
            if apply_offset:
                # Apply 50% offset for gait tasks
                # If ipsi is at phase 20, contra should be at phase 70
                contra_phase = (phase + 50) % 100
            else:
                # No offset for bilateral tasks (squat, jump, etc.)
                contra_phase = phase
            
            # Ensure the target phase exists in result
            if contra_phase not in result:
                result[contra_phase] = {}
            
            # Copy ipsi features from current phase to contra at target phase
            for var_name, var_range in phases_data[phase].items():
                if '_ipsi' in var_name:
                    contra_name = var_name.replace('_ipsi', '_contra')
                    result[contra_phase][contra_name] = var_range
        
        return result
    
    def get_phases(self, task: str) -> List[int]:
        """
        Get list of phases for a specific task.
        
        Args:
            task: Task name
            
        Returns:
            Sorted list of phase percentages
        """
        if task not in self._data:
            return []
        return sorted(self._data[task].get('phases', {}).keys())
    
    def get_variables(self, task: str, phase: int, include_contra: bool = True) -> List[str]:
        """
        Get list of variables for a specific task and phase.
        
        Args:
            task: Task name
            phase: Phase percentage
            include_contra: Whether to include generated contralateral features
            
        Returns:
            List of variable names
        """
        if include_contra:
            # Get data with generated contra features
            task_data = self.get_task_data(task)
            return list(task_data.get(phase, {}).keys())
        else:
            # Only return stored ipsi features
            try:
                return list(self._data[task]['phases'][phase].keys())
            except KeyError:
                return []
    
    def clear(self) -> None:
        """Clear all validation data (but keep metadata)."""
        self._data.clear()
    
    def set_metadata(self, key: str, value: Any) -> None:
        """
        Set a metadata field.
        
        Args:
            key: Metadata key
            value: Metadata value
        """
        self._metadata[key] = value
    
    def get_metadata(self, key: str = None) -> Any:
        """
        Get metadata.
        
        Args:
            key: Specific metadata key. If None, returns all metadata.
            
        Returns:
            Metadata value or entire metadata dict
        """
        if key is None:
            return self._metadata.copy()
        return self._metadata.get(key)
    
    def set_task_metadata(self, task: str, key: str, value: Any) -> None:
        """
        Set task-specific metadata.
        
        Args:
            task: Task name
            key: Metadata key (e.g., 'contralateral_offset')
            value: Metadata value
        """
        if task not in self._data:
            self._data[task] = {'metadata': {}, 'phases': {}}
        if 'metadata' not in self._data[task]:
            self._data[task]['metadata'] = {}
        self._data[task]['metadata'][key] = value
    
    def get_task_metadata(self, task: str, key: str = None) -> Any:
        """
        Get task-specific metadata.
        
        Args:
            task: Task name
            key: Specific metadata key. If None, returns all task metadata.
            
        Returns:
            Metadata value or entire task metadata dict
        """
        metadata = self._data.get(task, {}).get('metadata', {})
        if key is None:
            return metadata.copy()
        return metadata.get(key)
    
    def set_data(self, data: Dict[str, Any]) -> None:
        """
        Replace entire internal data structure.
        Handles both old flat format and new nested format.
        
        Args:
            data: Complete validation data dictionary
        """
        self._data.clear()
        
        for task_name, task_data in data.items():
            # Check if it's new nested format or old flat format
            if isinstance(task_data, dict) and 'phases' in task_data:
                # New format - use as is
                self._data[task_name] = task_data
            else:
                # Old flat format - wrap in new structure
                self._data[task_name] = {
                    'metadata': {'contralateral_offset': True},
                    'phases': {}
                }
                
                # Convert phases
                for phase, variables in task_data.items():
                    phase = int(phase) if not isinstance(phase, int) else phase
                    if not 0 <= phase <= 100:
                        raise ValueError(f"Phase {phase} in task {task_name} is out of range.")
                    
                    # Filter out contra features
                    filtered_vars = {}
                    for var_name, var_range in variables.items():
                        if '_contra' not in var_name:
                            filtered_vars[var_name] = var_range
                    
                    self._data[task_name]['phases'][phase] = filtered_vars
    
    def get_data(self) -> Dict[str, Dict[str, Any]]:
        """
        Get a copy of the entire internal data structure.
        For debugging purposes only.
        
        Returns:
            Copy of the internal validation data (without generated contra features)
        """
        return self._data.copy()
    
    def has_task(self, task: str) -> bool:
        """Check if a task exists in the configuration."""
        return task in self._data
    
    def has_variable(self, task: str, phase: int, variable: str) -> bool:
        """
        Check if a specific variable exists.
        Works for both ipsi (stored) and contra (generated) variables.
        """
        task_data = self.get_task_data(task)  # Gets data with generated contra
        return phase in task_data and variable in task_data[phase]