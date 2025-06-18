#!/usr/bin/env python3
"""
Validation Range Updater

Created: 2025-06-18 with user permission
Purpose: Memory-conscious system for updating validation ranges with literature tracking

Intent: Provides a lightweight system for updating validation ranges based on
literature with proper version control, conflict detection, and rollback capabilities.
Designed for extreme memory efficiency using simple data structures and minimal
external dependencies.
"""

import json
import copy
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

from .validation_expectations_parser import ValidationExpectationsParser


@dataclass
class RangeUpdate:
    """
    Represents a single validation range update with full tracking information.
    
    Memory-efficient dataclass for tracking individual range updates with
    literature citations and change rationale.
    """
    task: str
    phase: int
    variable: str
    new_min: float
    new_max: float
    citation: str
    rationale: str
    reviewer: str
    timestamp: datetime = None
    old_min: float = None
    old_max: float = None
    
    def __post_init__(self):
        """Set timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RangeUpdate':
        """Create from dictionary for JSON deserialization."""
        if 'timestamp' in data and isinstance(data['timestamp'], str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


class RangeUpdater:
    """
    Memory-conscious validation range updater with version control.
    
    Provides functionality to update validation ranges with proper tracking,
    literature citations, conflict detection, and rollback capabilities.
    Uses simple data structures for minimal memory footprint.
    """
    
    def __init__(self):
        """Initialize the range updater."""
        self.parser = ValidationExpectationsParser()
    
    def load_validation_data(self, file_path: str) -> Dict[str, Dict[int, Dict[str, Dict[str, float]]]]:
        """
        Load validation data from markdown file.
        
        Args:
            file_path: Path to validation expectations markdown file
            
        Returns:
            Validation data dictionary
        """
        return self.parser.read_validation_data(file_path)
    
    def apply_range_update(self, validation_data: Dict[str, Dict[int, Dict[str, Dict[str, float]]]], 
                          update: RangeUpdate) -> Dict[str, Dict[int, Dict[str, Dict[str, float]]]]:
        """
        Apply a single range update to validation data.
        
        Args:
            validation_data: Current validation data
            update: Range update to apply
            
        Returns:
            Updated validation data with new ranges
            
        Raises:
            ValueError: If update targets non-existent task/phase/variable
        """
        # Create deep copy to avoid modifying original data
        updated_data = copy.deepcopy(validation_data)
        
        # Validate update targets exist
        if update.task not in updated_data:
            raise ValueError(f"Task '{update.task}' not found in validation data")
        
        if update.phase not in updated_data[update.task]:
            raise ValueError(f"Phase {update.phase} not found for task '{update.task}'")
        
        if update.variable not in updated_data[update.task][update.phase]:
            raise ValueError(f"Variable '{update.variable}' not found for task '{update.task}' phase {update.phase}")
        
        # Store old values if not already set
        if update.old_min is None or update.old_max is None:
            current_range = updated_data[update.task][update.phase][update.variable]
            update.old_min = current_range['min']
            update.old_max = current_range['max']
        
        # Apply update
        updated_data[update.task][update.phase][update.variable]['min'] = update.new_min
        updated_data[update.task][update.phase][update.variable]['max'] = update.new_max
        
        return updated_data
    
    def apply_batch_updates(self, validation_data: Dict[str, Dict[int, Dict[str, Dict[str, float]]]], 
                           updates: List[RangeUpdate]) -> Dict[str, Dict[int, Dict[str, Dict[str, float]]]]:
        """
        Apply multiple range updates efficiently.
        
        Args:
            validation_data: Current validation data
            updates: List of range updates to apply
            
        Returns:
            Updated validation data with all new ranges
            
        Raises:
            ValueError: If any update conflicts or targets invalid locations
        """
        # Check for conflicts first
        conflicts = self.detect_conflicts(updates)
        if conflicts:
            conflict_desc = ', '.join([f"{c['task']}.{c['phase']}.{c['variable']}" for c in conflicts])
            raise ValueError(f"Conflicting updates detected: {conflict_desc}")
        
        # Apply updates sequentially
        updated_data = validation_data
        for update in updates:
            updated_data = self.apply_range_update(updated_data, update)
        
        return updated_data
    
    def detect_conflicts(self, updates: List[RangeUpdate]) -> List[Dict[str, Any]]:
        """
        Detect conflicting range updates.
        
        Args:
            updates: List of range updates to check
            
        Returns:
            List of conflicts detected
        """
        conflicts = []
        
        # Group updates by target (task, phase, variable)
        targets = {}
        for i, update in enumerate(updates):
            target_key = (update.task, update.phase, update.variable)
            if target_key not in targets:
                targets[target_key] = []
            targets[target_key].append((i, update))
        
        # Check for multiple updates to same target
        for target_key, target_updates in targets.items():
            if len(target_updates) > 1:
                task, phase, variable = target_key
                conflicts.append({
                    'task': task,
                    'phase': phase,
                    'variable': variable,
                    'type': 'multiple_updates',
                    'count': len(target_updates),
                    'updates': [u[0] for u in target_updates]
                })
        
        # Check for logical conflicts (min > max, etc.)
        for update in updates:
            if update.new_min > update.new_max:
                conflicts.append({
                    'task': update.task,
                    'phase': update.phase,
                    'variable': update.variable,
                    'type': 'min_greater_than_max',
                    'new_min': update.new_min,
                    'new_max': update.new_max
                })
        
        return conflicts
    
    def save_version(self, version_file: str, update: RangeUpdate, version_number: int = None) -> int:
        """
        Save a version entry for tracking changes.
        
        Args:
            version_file: Path to version tracking JSON file
            update: Range update to save
            version_number: Specific version number (auto-increment if None)
            
        Returns:
            Version number assigned
        """
        # Load existing version data or create new
        version_data = self._load_version_file(version_file)
        
        # Determine version number
        if version_number is None:
            existing_versions = [v['version'] for v in version_data['versions']]
            version_number = max(existing_versions, default=0) + 1
        
        # Create version entry
        version_entry = {
            'version': version_number,
            'timestamp': update.timestamp.isoformat(),
            'task': update.task,
            'phase': update.phase,
            'variable': update.variable,
            'old_min': update.old_min,
            'old_max': update.old_max,
            'new_min': update.new_min,
            'new_max': update.new_max,
            'citation': update.citation,
            'rationale': update.rationale,
            'reviewer': update.reviewer
        }
        
        # Add to version data
        version_data['versions'].append(version_entry)
        version_data['last_updated'] = datetime.now().isoformat()
        
        # Save back to file
        with open(version_file, 'w') as f:
            json.dump(version_data, f, indent=2)
        
        return version_number
    
    def get_rollback_update(self, version_file: str, version: int) -> RangeUpdate:
        """
        Get rollback update for a specific version.
        
        Args:
            version_file: Path to version tracking JSON file
            version: Version number to rollback to
            
        Returns:
            RangeUpdate that would restore the specified version
            
        Raises:
            ValueError: If version not found
        """
        version_data = self._load_version_file(version_file)
        
        # Find the version entry
        target_entry = None
        for entry in version_data['versions']:
            if entry['version'] == version:
                target_entry = entry
                break
        
        if target_entry is None:
            raise ValueError(f"Version {version} not found in {version_file}")
        
        # Create rollback update - use the new values from that version as the target
        rollback_update = RangeUpdate(
            task=target_entry['task'],
            phase=target_entry['phase'],
            variable=target_entry['variable'],
            new_min=target_entry['new_min'],  # Use new values from target version
            new_max=target_entry['new_max'],
            citation=f"Rollback to version {version}",
            rationale=f"Rolling back change: {target_entry['rationale']}",
            reviewer="system_rollback",
            timestamp=datetime.now()
        )
        
        return rollback_update
    
    def get_version_history(self, version_file: str, task: str = None, 
                           variable: str = None) -> List[Dict[str, Any]]:
        """
        Get version history, optionally filtered by task/variable.
        
        Args:
            version_file: Path to version tracking JSON file
            task: Optional task filter
            variable: Optional variable filter
            
        Returns:
            List of version entries matching filters
        """
        version_data = self._load_version_file(version_file)
        
        versions = version_data['versions']
        
        # Apply filters
        if task:
            versions = [v for v in versions if v['task'] == task]
        if variable:
            versions = [v for v in versions if v['variable'] == variable]
        
        # Sort by version number descending (newest first)
        versions.sort(key=lambda x: x['version'], reverse=True)
        
        return versions
    
    def update_validation_file(self, file_path: str, updates: List[RangeUpdate],
                              version_file: str = None) -> None:
        """
        Update validation file with range updates and track versions.
        
        Args:
            file_path: Path to validation expectations markdown file
            updates: List of range updates to apply
            version_file: Path to version tracking file (optional)
        """
        # Load current data
        validation_data = self.load_validation_data(file_path)
        
        # Apply updates
        updated_data = self.apply_batch_updates(validation_data, updates)
        
        # Save versions if version file provided
        if version_file:
            for update in updates:
                self.save_version(version_file, update)
        
        # Determine dataset info for disclaimer
        dataset_info = self._extract_dataset_info(file_path)
        
        # Write updated data back to file
        self.parser.write_validation_data(
            file_path, 
            updated_data, 
            dataset_name=dataset_info.get('dataset_name'),
            method=dataset_info.get('method')
        )
    
    def _load_version_file(self, version_file: str) -> Dict[str, Any]:
        """Load version tracking file or create new structure."""
        if not Path(version_file).exists():
            return {
                'created': datetime.now().isoformat(),
                'last_updated': datetime.now().isoformat(),
                'versions': []
            }
        
        with open(version_file, 'r') as f:
            return json.load(f)
    
    def _extract_dataset_info(self, file_path: str) -> Dict[str, str]:
        """Extract dataset and method info from existing file for disclaimers."""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            dataset_info = {}
            
            # Look for existing disclaimers to preserve dataset/method info
            import re
            source_match = re.search(r'📊 \*\*Source\*\*: `([^`]+)`', content)
            if source_match:
                dataset_info['dataset_name'] = source_match.group(1)
            
            method_match = re.search(r'📈 \*\*Method\*\*: ([^|]+)', content)
            if method_match:
                method_text = method_match.group(1).strip()
                # Convert back to method code if possible
                if 'Percentile' in method_text:
                    dataset_info['method'] = 'percentile_95'
                elif 'Mean' in method_text:
                    dataset_info['method'] = 'mean_3std'
                else:
                    dataset_info['method'] = 'manual_update'
            
            return dataset_info
            
        except Exception:
            return {'method': 'manual_update'}


def create_range_update_from_input(task: str, phase: int, variable: str,
                                 new_min: float, new_max: float, citation: str,
                                 rationale: str, reviewer: str) -> RangeUpdate:
    """
    Convenience function to create RangeUpdate from user input.
    
    Args:
        task: Task name (e.g., 'level_walking')
        phase: Phase percentage (0, 25, 50, 75)
        variable: Variable name (e.g., 'hip_flexion_angle_ipsi')
        new_min: New minimum value
        new_max: New maximum value
        citation: Literature citation
        rationale: Rationale for the change
        reviewer: Name/ID of reviewer making the change
        
    Returns:
        RangeUpdate instance ready for application
    """
    return RangeUpdate(
        task=task,
        phase=phase,
        variable=variable,
        new_min=new_min,
        new_max=new_max,
        citation=citation,
        rationale=rationale,
        reviewer=reviewer
    )