#!/usr/bin/env python3
"""
Validation Config Manager

Manages validation range configurations stored in YAML files.
Provides a clean API for reading and writing validation ranges.

This replaces the previous markdown-based storage with a dedicated
configuration file approach, separating data from documentation.
"""

import yaml
from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime


class ValidationConfigManager:
    """
    Manages validation range configurations stored in YAML files.
    
    This class provides a centralized interface for reading and writing
    validation ranges, replacing the previous markdown-based approach.
    """
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize the config manager.
        
        Args:
            config_dir: Directory containing config files. If None, uses project default.
        """
        if config_dir is None:
            # Default to project_root/contributor_scripts/validation_ranges/
            project_root = Path(__file__).parent.parent.parent
            self.config_dir = project_root / "contributor_scripts" / "validation_ranges"
        else:
            self.config_dir = Path(config_dir)
        
        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Define config file paths
        self.kinematic_config = self.config_dir / "kinematic_ranges.yaml"
        self.kinetic_config = self.config_dir / "kinetic_ranges.yaml"
    
    def load_validation_ranges(self, mode: str) -> Dict[str, Dict[int, Dict[str, Dict[str, float]]]]:
        """
        Load validation ranges from YAML config file.
        
        Args:
            mode: 'kinematic' or 'kinetic'
            
        Returns:
            Dictionary structured as: {task_name: {phase: {variable: {min, max}}}}
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If mode is invalid
        """
        if mode == 'kinematic':
            config_file = self.kinematic_config
        elif mode == 'kinetic':
            config_file = self.kinetic_config
        else:
            raise ValueError(f"Invalid mode: {mode}. Must be 'kinematic' or 'kinetic'")
        
        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {config_file}")
        
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        # Extract and convert the validation ranges
        # Convert string phase keys to integers
        validation_data = {}
        if 'tasks' in config:
            for task_name, task_data in config['tasks'].items():
                validation_data[task_name] = {}
                if 'phases' in task_data:
                    for phase_str, variables in task_data['phases'].items():
                        phase = int(phase_str)
                        validation_data[task_name][phase] = variables
        
        return validation_data
    
    def save_validation_ranges(self, 
                              mode: str,
                              validation_data: Dict[str, Dict[int, Dict[str, Dict[str, float]]]],
                              metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Save validation ranges to YAML config file.
        
        Args:
            mode: 'kinematic' or 'kinetic'
            validation_data: Validation data dictionary
            metadata: Optional metadata (dataset, method, etc.)
        """
        if mode == 'kinematic':
            config_file = self.kinematic_config
        elif mode == 'kinetic':
            config_file = self.kinetic_config
        else:
            raise ValueError(f"Invalid mode: {mode}. Must be 'kinematic' or 'kinetic'")
        
        # Build config structure
        config = {
            'version': '1.0',
            'generated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        
        # Add metadata if provided
        if metadata:
            config.update(metadata)
        
        # Convert validation data to YAML-friendly format
        # Convert integer phase keys to strings for YAML
        config['tasks'] = {}
        for task_name, task_data in validation_data.items():
            config['tasks'][task_name] = {'phases': {}}
            for phase, variables in task_data.items():
                config['tasks'][task_name]['phases'][str(phase)] = variables
        
        # Write to file with nice formatting
        with open(config_file, 'w') as f:
            yaml.dump(config, f, 
                     default_flow_style=False, 
                     sort_keys=False,
                     width=120,
                     indent=2)
        
        print(f"✅ Saved validation config to: {config_file}")
    
    def get_task_ranges(self, mode: str, task_name: str) -> Dict[int, Dict[str, Dict[str, float]]]:
        """
        Get validation ranges for a specific task.
        
        Args:
            mode: 'kinematic' or 'kinetic'
            task_name: Name of the task (e.g., 'level_walking')
            
        Returns:
            Dictionary structured as: {phase: {variable: {min, max}}}
            
        Raises:
            ValueError: If task not found
        """
        all_ranges = self.load_validation_ranges(mode)
        
        if task_name not in all_ranges:
            available_tasks = list(all_ranges.keys())
            raise ValueError(f"Task '{task_name}' not found. Available tasks: {available_tasks}")
        
        return all_ranges[task_name]
    
    def get_metadata(self, mode: str) -> Dict[str, Any]:
        """
        Get metadata from config file (version, dataset, method, etc.).
        
        Args:
            mode: 'kinematic' or 'kinetic'
            
        Returns:
            Dictionary with metadata fields
        """
        if mode == 'kinematic':
            config_file = self.kinematic_config
        elif mode == 'kinetic':
            config_file = self.kinetic_config
        else:
            raise ValueError(f"Invalid mode: {mode}. Must be 'kinematic' or 'kinetic'")
        
        if not config_file.exists():
            return {}
        
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        # Extract metadata (everything except 'tasks')
        metadata = {k: v for k, v in config.items() if k != 'tasks'}
        return metadata
    
    def config_exists(self, mode: str) -> bool:
        """
        Check if config file exists for the given mode.
        
        Args:
            mode: 'kinematic' or 'kinetic'
            
        Returns:
            True if config file exists, False otherwise
        """
        if mode == 'kinematic':
            return self.kinematic_config.exists()
        elif mode == 'kinetic':
            return self.kinetic_config.exists()
        else:
            raise ValueError(f"Invalid mode: {mode}. Must be 'kinematic' or 'kinetic'")