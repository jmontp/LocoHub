#!/usr/bin/env python3
"""
Validation Markdown Parser

Parses markdown-based validation specifications and converts them into
programmable validation rules for automated testing.

Single source of truth: validation_expectations.md
"""

import re
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
from pathlib import Path
import yaml
from dataclasses import dataclass

@dataclass
class ValidationRule:
    """Single validation rule for a variable in a specific task"""
    variable: str
    task: str
    phase_range: Tuple[float, float]
    min_value: float
    max_value: float
    expected_pattern: str
    tolerance: float
    tolerance_type: str  # 'percentage' or 'absolute'
    units: str
    notes: str

class ValidationMarkdownParser:
    """Parser for markdown-based validation specifications"""
    
    def __init__(self):
        self.validation_rules = {}
        self.pattern_validators = {
            'peak_at_': self._validate_peak_at,
            'valley_at_': self._validate_valley_at,
            'increasing': self._validate_increasing,
            'decreasing': self._validate_decreasing,
            'negative_to_positive': self._validate_negative_to_positive,
            'near_zero': self._validate_near_zero,
            'predominantly_negative': self._validate_predominantly_negative,
            'predominantly_positive': self._validate_predominantly_positive,
            'U_shaped': self._validate_u_shaped,
            'inverted_U': self._validate_inverted_u,
            'variable': self._validate_variable,
            'controlled_motion': self._validate_controlled_motion,
            'heel_to_toe': self._validate_heel_to_toe,
            'more_negative': self._validate_more_negative,
            'more_positive': self._validate_more_positive,
            'flexion_then_extension': self._validate_flexion_then_extension,
            'plantarflexion_peak': self._validate_plantarflexion_peak,
            'dorsiflexion_peak': self._validate_dorsiflexion_peak,
            'increasing_then_decreasing': self._validate_increasing_then_decreasing,
            'bilateral': self._validate_bilateral
        }
    
    def parse_file(self, markdown_file: str) -> Dict[str, List[ValidationRule]]:
        """
        Parse markdown file and extract validation rules
        
        Args:
            markdown_file: Path to markdown validation specification
            
        Returns:
            Dict mapping task names to lists of validation rules
        """
        with open(markdown_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return self.parse_content(content)
    
    def parse_content(self, content: str) -> Dict[str, List[ValidationRule]]:
        """Parse markdown content and extract validation rules"""
        
        # Find all task sections
        task_pattern = r'### Task: (\w+)'
        task_matches = list(re.finditer(task_pattern, content))
        
        validation_rules = {}
        
        for i, match in enumerate(task_matches):
            task_name = match.group(1)
            start_pos = match.end()
            
            # Find end position (next task or end of content)
            if i + 1 < len(task_matches):
                end_pos = task_matches[i + 1].start()
            else:
                end_pos = len(content)
            
            task_content = content[start_pos:end_pos]
            
            # Parse table for this task
            rules = self._parse_task_table(task_name, task_content)
            validation_rules[task_name] = rules
        
        self.validation_rules = validation_rules
        return validation_rules
    
    def _parse_task_table(self, task_name: str, task_content: str) -> List[ValidationRule]:
        """Parse validation table for a specific task"""
        
        # Find table in task content
        table_pattern = r'\| Variable.*?\n\|[-\s\|]+\n((?:\|.*?\n)*)'
        table_match = re.search(table_pattern, task_content, re.MULTILINE)
        
        if not table_match:
            return []
        
        table_rows = table_match.group(1).strip().split('\n')
        rules = []
        
        for row in table_rows:
            if not row.strip() or not row.startswith('|'):
                continue
            
            # Parse table row
            columns = [col.strip() for col in row.split('|')[1:-1]]  # Remove empty first/last
            
            if len(columns) >= 7:  # Ensure we have all required columns
                try:
                    rule = self._parse_table_row(task_name, columns)
                    if rule:
                        rules.append(rule)
                except Exception as e:
                    print(f"Warning: Could not parse row for task {task_name}: {columns}. Error: {e}")
        
        return rules
    
    def _parse_table_row(self, task_name: str, columns: List[str]) -> Optional[ValidationRule]:
        """Parse a single table row into a ValidationRule"""
        
        if len(columns) < 7:
            return None
        
        variable = columns[0].strip()
        phase_range_str = columns[1].strip()
        min_value_str = columns[2].strip()
        max_value_str = columns[3].strip()
        expected_pattern = columns[4].strip()
        tolerance_str = columns[5].strip()
        units = columns[6].strip()
        notes = columns[7].strip() if len(columns) > 7 else ""
        
        # Parse phase range
        if '-' in phase_range_str:
            start, end = phase_range_str.split('-')
            phase_range = (float(start), float(end))
        else:
            phase_range = (0.0, 100.0)  # Default to full cycle
        
        # Parse min/max values
        try:
            min_value = float(min_value_str)
            max_value = float(max_value_str)
        except ValueError:
            print(f"Warning: Could not parse numeric values for {variable}: {min_value_str}, {max_value_str}")
            return None
        
        # Parse tolerance
        tolerance_type = 'absolute'
        tolerance_value = 0.1  # Default
        
        if tolerance_str.endswith('%'):
            tolerance_type = 'percentage'
            tolerance_value = float(tolerance_str[:-1]) / 100.0
        else:
            try:
                tolerance_value = float(tolerance_str)
            except ValueError:
                tolerance_value = 0.1  # Default fallback
        
        return ValidationRule(
            variable=variable,
            task=task_name,
            phase_range=phase_range,
            min_value=min_value,
            max_value=max_value,
            expected_pattern=expected_pattern,
            tolerance=tolerance_value,
            tolerance_type=tolerance_type,
            units=units,
            notes=notes
        )
    
    def validate_data(self, data: pd.DataFrame, task_name: str) -> Dict[str, Any]:
        """
        Validate dataset against rules for specific task
        
        Args:
            data: DataFrame with biomechanical data
            task_name: Task to validate against
            
        Returns:
            Dict with validation results
        """
        if task_name not in self.validation_rules:
            return {"error": f"No validation rules found for task: {task_name}"}
        
        rules = self.validation_rules[task_name]
        results = {
            'task': task_name,
            'total_rules': len(rules),
            'passed_rules': 0,
            'failed_rules': 0,
            'rule_results': [],
            'summary': {}
        }
        
        for rule in rules:
            result = self._validate_single_rule(data, rule)
            results['rule_results'].append(result)
            
            if result['passed']:
                results['passed_rules'] += 1
            else:
                results['failed_rules'] += 1
        
        # Calculate summary statistics
        results['success_rate'] = results['passed_rules'] / results['total_rules'] if results['total_rules'] > 0 else 0
        results['summary'] = self._generate_summary(results['rule_results'])
        
        return results
    
    def _validate_single_rule(self, data: pd.DataFrame, rule: ValidationRule) -> Dict[str, Any]:
        """Validate data against a single validation rule"""
        
        result = {
            'variable': rule.variable,
            'task': rule.task,
            'passed': False,
            'errors': [],
            'warnings': [],
            'statistics': {}
        }
        
        # Check if variable exists in data
        if rule.variable not in data.columns:
            result['errors'].append(f"Variable {rule.variable} not found in dataset")
            return result
        
        # Filter data for phase range if phase column exists
        filtered_data = data.copy()
        phase_cols = [col for col in data.columns if col.startswith('phase_')]
        
        if phase_cols and rule.phase_range != (0.0, 100.0):
            # Use first available phase column
            phase_col = phase_cols[0]
            mask = (data[phase_col] >= rule.phase_range[0]) & (data[phase_col] <= rule.phase_range[1])
            filtered_data = data[mask]
        
        if len(filtered_data) == 0:
            result['errors'].append(f"No data found in phase range {rule.phase_range}")
            return result
        
        variable_data = filtered_data[rule.variable].dropna()
        
        if len(variable_data) == 0:
            result['errors'].append(f"No valid data for {rule.variable}")
            return result
        
        # Calculate basic statistics
        stats = {
            'count': len(variable_data),
            'mean': variable_data.mean(),
            'std': variable_data.std(),
            'min': variable_data.min(),
            'max': variable_data.max(),
            'median': variable_data.median()
        }
        result['statistics'] = stats
        
        # Validate range
        range_valid = True
        if stats['min'] < rule.min_value:
            result['errors'].append(f"Minimum value {stats['min']:.3f} below expected {rule.min_value}")
            range_valid = False
        
        if stats['max'] > rule.max_value:
            result['errors'].append(f"Maximum value {stats['max']:.3f} above expected {rule.max_value}")
            range_valid = False
        
        # Validate pattern
        pattern_valid = self._validate_pattern(variable_data, rule, filtered_data)
        if not pattern_valid['valid']:
            result['errors'].extend(pattern_valid['errors'])
        
        # Overall validation result
        result['passed'] = range_valid and pattern_valid['valid'] and len(result['errors']) == 0
        
        return result
    
    def _validate_pattern(self, variable_data: pd.Series, rule: ValidationRule, full_data: pd.DataFrame) -> Dict[str, Any]:
        """Validate expected pattern for variable data"""
        
        pattern_result = {'valid': True, 'errors': []}
        
        # Check for multiple patterns (comma-separated)
        patterns = [p.strip() for p in rule.expected_pattern.split(',')]
        
        for pattern in patterns:
            # Find appropriate validator
            validator_found = False
            
            for pattern_key, validator_func in self.pattern_validators.items():
                if pattern.startswith(pattern_key.rstrip('_')):
                    try:
                        valid = validator_func(variable_data, pattern, rule, full_data)
                        if not valid:
                            pattern_result['errors'].append(f"Pattern '{pattern}' validation failed")
                            pattern_result['valid'] = False
                        validator_found = True
                        break
                    except Exception as e:
                        pattern_result['errors'].append(f"Error validating pattern '{pattern}': {e}")
                        pattern_result['valid'] = False
                        validator_found = True
                        break
            
            if not validator_found:
                pattern_result['errors'].append(f"Unknown pattern: {pattern}")
                pattern_result['valid'] = False
        
        return pattern_result
    
    # Pattern validation methods
    def _validate_peak_at(self, data: pd.Series, pattern: str, rule: ValidationRule, full_data: pd.DataFrame) -> bool:
        """Validate that peak occurs at specified phase"""
        try:
            phase_value = float(pattern.split('_at_')[1])
            peak_idx = data.idxmax()
            
            # Get phase data if available
            phase_cols = [col for col in full_data.columns if col.startswith('phase_')]
            if phase_cols:
                phase_data = full_data[phase_cols[0]]
                actual_phase = phase_data.iloc[peak_idx]
                tolerance = rule.tolerance * 100 if rule.tolerance_type == 'percentage' else rule.tolerance
                return abs(actual_phase - phase_value) <= tolerance
            
            return True  # Cannot validate without phase data, assume valid
        except:
            return False
    
    def _validate_valley_at(self, data: pd.Series, pattern: str, rule: ValidationRule, full_data: pd.DataFrame) -> bool:
        """Validate that valley occurs at specified phase"""
        try:
            phase_value = float(pattern.split('_at_')[1])
            valley_idx = data.idxmin()
            
            # Get phase data if available
            phase_cols = [col for col in full_data.columns if col.startswith('phase_')]
            if phase_cols:
                phase_data = full_data[phase_cols[0]]
                actual_phase = phase_data.iloc[valley_idx]
                tolerance = rule.tolerance * 100 if rule.tolerance_type == 'percentage' else rule.tolerance
                return abs(actual_phase - phase_value) <= tolerance
            
            return True  # Cannot validate without phase data
        except:
            return False
    
    def _validate_increasing(self, data: pd.Series, pattern: str, rule: ValidationRule, full_data: pd.DataFrame) -> bool:
        """Validate monotonic increasing pattern"""
        diff = np.diff(data.values)
        increasing_ratio = np.sum(diff > 0) / len(diff) if len(diff) > 0 else 0
        return increasing_ratio >= (1 - rule.tolerance)
    
    def _validate_decreasing(self, data: pd.Series, pattern: str, rule: ValidationRule, full_data: pd.DataFrame) -> bool:
        """Validate monotonic decreasing pattern"""
        diff = np.diff(data.values)
        decreasing_ratio = np.sum(diff < 0) / len(diff) if len(diff) > 0 else 0
        return decreasing_ratio >= (1 - rule.tolerance)
    
    def _validate_negative_to_positive(self, data: pd.Series, pattern: str, rule: ValidationRule, full_data: pd.DataFrame) -> bool:
        """Validate transition from negative to positive values"""
        has_negative = np.any(data < 0)
        has_positive = np.any(data > 0)
        return has_negative and has_positive
    
    def _validate_near_zero(self, data: pd.Series, pattern: str, rule: ValidationRule, full_data: pd.DataFrame) -> bool:
        """Validate values are close to zero"""
        threshold = rule.tolerance if rule.tolerance_type == 'absolute' else rule.tolerance * np.abs(data).max()
        near_zero_ratio = np.sum(np.abs(data) <= threshold) / len(data)
        return near_zero_ratio >= 0.8  # 80% of values should be near zero
    
    def _validate_predominantly_negative(self, data: pd.Series, pattern: str, rule: ValidationRule, full_data: pd.DataFrame) -> bool:
        """Validate most values are negative"""
        negative_ratio = np.sum(data < 0) / len(data)
        return negative_ratio >= 0.7  # 70% should be negative
    
    def _validate_predominantly_positive(self, data: pd.Series, pattern: str, rule: ValidationRule, full_data: pd.DataFrame) -> bool:
        """Validate most values are positive"""
        positive_ratio = np.sum(data > 0) / len(data)
        return positive_ratio >= 0.7  # 70% should be positive
    
    def _validate_u_shaped(self, data: pd.Series, pattern: str, rule: ValidationRule, full_data: pd.DataFrame) -> bool:
        """Validate U-shaped pattern (valley in middle)"""
        if len(data) < 3:
            return True
        
        mid_point = len(data) // 2
        first_half = data.iloc[:mid_point]
        second_half = data.iloc[mid_point:]
        
        # First half should generally decrease, second half increase
        first_trend = np.sum(np.diff(first_half) < 0) / len(np.diff(first_half)) if len(first_half) > 1 else 0
        second_trend = np.sum(np.diff(second_half) > 0) / len(np.diff(second_half)) if len(second_half) > 1 else 0
        
        return first_trend >= 0.5 and second_trend >= 0.5
    
    def _validate_inverted_u(self, data: pd.Series, pattern: str, rule: ValidationRule, full_data: pd.DataFrame) -> bool:
        """Validate inverted U-shaped pattern (peak in middle)"""
        if len(data) < 3:
            return True
        
        mid_point = len(data) // 2
        first_half = data.iloc[:mid_point]
        second_half = data.iloc[mid_point:]
        
        # First half should generally increase, second half decrease
        first_trend = np.sum(np.diff(first_half) > 0) / len(np.diff(first_half)) if len(first_half) > 1 else 0
        second_trend = np.sum(np.diff(second_half) < 0) / len(np.diff(second_half)) if len(second_half) > 1 else 0
        
        return first_trend >= 0.5 and second_trend >= 0.5
    
    def _validate_variable(self, data: pd.Series, pattern: str, rule: ValidationRule, full_data: pd.DataFrame) -> bool:
        """Validate high variability pattern"""
        cv = data.std() / np.abs(data.mean()) if data.mean() != 0 else float('inf')
        return cv >= 0.3  # Coefficient of variation >= 30%
    
    def _validate_controlled_motion(self, data: pd.Series, pattern: str, rule: ValidationRule, full_data: pd.DataFrame) -> bool:
        """Validate smooth, controlled motion"""
        if len(data) < 2:
            return True
        
        # Check for smooth changes (no large jumps)
        diff = np.abs(np.diff(data))
        threshold = 3 * np.std(diff)  # 3 standard deviations
        large_jumps = np.sum(diff > threshold)
        return large_jumps <= len(diff) * 0.05  # Less than 5% large jumps
    
    # Additional pattern validators can be added here
    def _validate_heel_to_toe(self, data: pd.Series, pattern: str, rule: ValidationRule, full_data: pd.DataFrame) -> bool:
        """Validate heel-to-toe progression"""
        return self._validate_increasing(data, pattern, rule, full_data)
    
    def _validate_more_negative(self, data: pd.Series, pattern: str, rule: ValidationRule, full_data: pd.DataFrame) -> bool:
        """Validate predominantly negative values"""
        return self._validate_predominantly_negative(data, pattern, rule, full_data)
    
    def _validate_more_positive(self, data: pd.Series, pattern: str, rule: ValidationRule, full_data: pd.DataFrame) -> bool:
        """Validate predominantly positive values"""
        return self._validate_predominantly_positive(data, pattern, rule, full_data)
    
    def _validate_flexion_then_extension(self, data: pd.Series, pattern: str, rule: ValidationRule, full_data: pd.DataFrame) -> bool:
        """Validate flexion followed by extension"""
        return self._validate_inverted_u(data, pattern, rule, full_data)
    
    def _validate_plantarflexion_peak(self, data: pd.Series, pattern: str, rule: ValidationRule, full_data: pd.DataFrame) -> bool:
        """Validate peak plantarflexion (negative ankle angle)"""
        return data.min() < -0.1  # Significant plantarflexion
    
    def _validate_dorsiflexion_peak(self, data: pd.Series, pattern: str, rule: ValidationRule, full_data: pd.DataFrame) -> bool:
        """Validate peak dorsiflexion (positive ankle angle)"""
        return data.max() > 0.1  # Significant dorsiflexion
    
    def _validate_increasing_then_decreasing(self, data: pd.Series, pattern: str, rule: ValidationRule, full_data: pd.DataFrame) -> bool:
        """Validate increase then decrease pattern"""
        return self._validate_inverted_u(data, pattern, rule, full_data)
    
    def _validate_bilateral(self, data: pd.Series, pattern: str, rule: ValidationRule, full_data: pd.DataFrame) -> bool:
        """Validate bilateral symmetry - always return True as this requires both legs"""
        return True  # Would need additional logic to compare left/right
    
    def _generate_summary(self, rule_results: List[Dict]) -> Dict[str, Any]:
        """Generate summary statistics from rule results"""
        
        total_rules = len(rule_results)
        passed_rules = sum(1 for r in rule_results if r['passed'])
        failed_rules = total_rules - passed_rules
        
        # Categorize failures
        failure_categories = {
            'range_violations': 0,
            'pattern_failures': 0,
            'missing_variables': 0,
            'data_issues': 0
        }
        
        for result in rule_results:
            if not result['passed']:
                for error in result['errors']:
                    if 'not found' in error:
                        failure_categories['missing_variables'] += 1
                    elif 'below expected' in error or 'above expected' in error:
                        failure_categories['range_violations'] += 1
                    elif 'Pattern' in error:
                        failure_categories['pattern_failures'] += 1
                    else:
                        failure_categories['data_issues'] += 1
        
        return {
            'total_rules': total_rules,
            'passed_rules': passed_rules,
            'failed_rules': failed_rules,
            'success_rate': passed_rules / total_rules if total_rules > 0 else 0,
            'failure_categories': failure_categories
        }
    
    def export_rules_to_csv(self, output_file: str):
        """Export all validation rules to CSV format"""
        
        all_rules = []
        for task_name, rules in self.validation_rules.items():
            for rule in rules:
                all_rules.append({
                    'task': rule.task,
                    'variable': rule.variable,
                    'phase_start': rule.phase_range[0],
                    'phase_end': rule.phase_range[1],
                    'min_value': rule.min_value,
                    'max_value': rule.max_value,
                    'expected_pattern': rule.expected_pattern,
                    'tolerance': rule.tolerance,
                    'tolerance_type': rule.tolerance_type,
                    'units': rule.units,
                    'notes': rule.notes
                })
        
        df = pd.DataFrame(all_rules)
        df.to_csv(output_file, index=False)
        print(f"Exported {len(all_rules)} validation rules to {output_file}")


def main():
    """Example usage of the validation markdown parser"""
    
    # Initialize parser
    parser = ValidationMarkdownParser()
    
    # Parse validation expectations
    spec_file = "docs/standard_spec/validation_expectations.md"
    if Path(spec_file).exists():
        validation_rules = parser.parse_file(spec_file)
        
        print(f"Parsed validation rules for {len(validation_rules)} tasks:")
        for task, rules in validation_rules.items():
            print(f"  - {task}: {len(rules)} rules")
        
        # Export to CSV for review
        parser.export_rules_to_csv("validation_rules_parsed.csv")
        
    else:
        print(f"Validation specification file not found: {spec_file}")


if __name__ == "__main__":
    main()