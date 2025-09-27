#!/usr/bin/env python3
"""Validation Config Manager

Manages validation range configurations with internal data storage.
Provides a stable API that hides the underlying data structure.
Stores ipsilateral and contralateral ranges exactly as defined in YAML.
"""

import copy
import yaml
from pathlib import Path
from typing import Dict, Optional, Any, Tuple, List
from datetime import datetime


class ValidationConfigManager:
    """Manage validation configurations with explicit ipsilateral/contralateral data."""
    
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
        
        tasks_block = config.get('tasks', {}) or {}

        for task_name, task_section in tasks_block.items():
            if not isinstance(task_section, dict):
                raise ValueError(f"Task '{task_name}' must be a mapping with 'phases'.")

            metadata = copy.deepcopy(task_section.get('metadata', {}) or {})
            phases_src = task_section.get('phases', {}) or {}

            normalized = self._normalize_phases(task_name, phases_src)

            self._data[task_name] = {
                'metadata': metadata,
                'phases': normalized
            }

    def _normalize_phases(
        self,
        task_name: str,
        phases: Dict[Any, Dict[str, Dict[str, float]]]
    ) -> Dict[int, Dict[str, Dict[str, float]]]:
        """Normalize phase keys to integers and deep-copy variable ranges."""
        normalized: Dict[int, Dict[str, Dict[str, float]]] = {}

        for phase_key, variables in (phases or {}).items():
            if isinstance(phase_key, str):
                try:
                    phase = int(float(phase_key))
                except ValueError as exc:
                    raise ValueError(
                        f"Invalid phase '{phase_key}' in task {task_name}. Phase must be numeric."
                    ) from exc
            else:
                phase = int(phase_key)

            if not 0 <= phase <= 100:
                raise ValueError(
                    f"Phase {phase} in task {task_name} is out of range. Must be 0-100."
                )

            normalized[phase] = {}
            for var_name, var_range in (variables or {}).items():
                if not isinstance(var_range, dict):
                    raise ValueError(
                        f"Variable '{var_name}' at phase {phase} in task {task_name} must be a dict with min/max."
                    )
                normalized[phase][var_name] = {
                    'min': var_range.get('min'),
                    'max': var_range.get('max')
                }

        return normalized

    def save(self, config_path: Optional[Path] = None) -> None:
        """
        Save internal validation ranges to YAML file.

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
            metadata = task_data.get('metadata', {}) or {}
            phases = task_data.get('phases', {}) or {}

            task_entry: Dict[str, Any] = {}
            if metadata:
                task_entry['metadata'] = copy.deepcopy(metadata)

            serialized_phases = {}
            for phase, variables in sorted(phases.items()):
                serialized_phases[int(phase)] = {
                    var_name: copy.deepcopy(var_range)
                    for var_name, var_range in variables.items()
                }

            task_entry['phases'] = serialized_phases
            config['tasks'][task_name] = task_entry
        
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
        Works for both ipsi and contra variables.
        
        Args:
            task: Task name
            phase: Phase percentage (0-100)
            variable: Variable name (ipsi or contra)
            
        Returns:
            Tuple of (min, max) or None if not found
        """
        task_data = self.get_task_data(task)
        phase_data = task_data.get(int(phase), {})
        range_data = phase_data.get(variable)
        if not range_data:
            return None
        return (range_data.get('min'), range_data.get('max'))
    
    def set_range(self,
                  task: str,
                  phase: int,
                  variable: str,
                  min_val: float,
                  max_val: float) -> None:
        """
        Set min/max range for a specific variable.

        Args:
            task: Task name
            phase: Phase percentage (0-100)
            variable: Variable name
            min_val: Minimum value
            max_val: Maximum value
            
        Raises:
            ValueError: If phase is out of range
        """
        # Ensure phase is an integer
        phase = int(phase) if not isinstance(phase, int) else phase
        
        # Validate phase range
        if not 0 <= phase <= 100:
            raise ValueError(f"Phase {phase} is out of range. Must be 0-100.")
        
        if task not in self._data:
            self._data[task] = {'metadata': {}, 'phases': {}}

        phases = self._data[task].setdefault('phases', {})
        phase_entry = phases.setdefault(phase, {})
        range_entry = phase_entry.setdefault(variable, {})
        range_entry['min'] = min_val
        range_entry['max'] = max_val
    
    def get_tasks(self) -> List[str]:
        """
        Get list of all tasks in the configuration.
        
        Returns:
            List of task names
        """
        return list(self._data.keys())
    
    def get_task_data(self, task: str) -> Dict[int, Dict[str, Dict[str, float]]]:
        """Return a deep copy of the stored validation ranges for a task."""
        task_info = self._data.get(task)
        if not task_info:
            return {}

        return {
            phase: {
                var_name: copy.deepcopy(var_range)
                for var_name, var_range in variables.items()
            }
            for phase, variables in task_info.get('phases', {}).items()
        }
    
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
            include_contra: Whether to include contralateral features
            
        Returns:
            List of variable names
        """
        task_data = self.get_task_data(task)
        variables = list(task_data.get(int(phase), {}).keys())

        if include_contra:
            return variables

        return [name for name in variables if '_contra' not in name]
    
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
            key: Metadata key
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
        """Replace the internal data structure with the provided dictionary."""
        self._data.clear()

        for task_name, task_block in data.items():
            if isinstance(task_block, dict) and 'phases' in task_block:
                metadata = copy.deepcopy(task_block.get('metadata', {}) or {})
                phases_src = task_block.get('phases', {}) or {}
            else:
                metadata = {}
                phases_src = task_block or {}

            normalized = self._normalize_phases(task_name, phases_src)
            explicit = {
                phase: {
                    var_name: copy.deepcopy(var_range)
                    for var_name, var_range in variables.items()
                }
                for phase, variables in normalized.items()
            }

            self._data[task_name] = {
                'metadata': metadata,
                'phases': explicit
            }
    
    def get_data(self) -> Dict[str, Dict[str, Any]]:
        """
        Get a copy of the entire internal data structure.
        For debugging purposes only.
        
        Returns:
            Deep copy of internal validation data.
        """
        return copy.deepcopy(self._data)
    
    def has_task(self, task: str) -> bool:
        """Check if a task exists in the configuration."""
        return task in self._data
    
    def has_variable(self, task: str, phase: int, variable: str) -> bool:
        """
        Check if a specific variable exists for a task/phase.
        """
        task_data = self.get_task_data(task)
        return phase in task_data and variable in task_data[phase]
