"""
Agent Configuration Management

Created: 2025-01-16 with user permission  
Purpose: Configuration management for three-agent framework

Intent: Provides centralized configuration for agent workspaces, quality gates,
and orchestration parameters following the documented specifications.
"""

import os
import yaml
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any


@dataclass
class QualityGates:
    """Quality gate thresholds and requirements"""
    test_coverage_threshold: float = 0.90
    acceptance_criteria_coverage: float = 0.95
    interface_compliance_threshold: float = 1.0
    performance_benchmark_threshold: float = 1.0
    code_quality_threshold: float = 0.85
    integration_success_threshold: float = 0.95


@dataclass
class AgentWorkspaceConfig:
    """Configuration for individual agent workspaces"""
    workspace_path: str
    templates_path: str
    output_path: str
    isolated_environment: bool = True
    max_memory_mb: int = 2048
    timeout_minutes: int = 60


def create_default_config(workspace_root: Path):
    """Create default configuration for agent framework"""
    
    # Quality gates based on documentation specifications
    quality_gates = QualityGates(
        test_coverage_threshold=0.90,  # >90% coverage of acceptance criteria
        acceptance_criteria_coverage=0.95,  # 95% of criteria must be tested
        interface_compliance_threshold=1.0,  # 100% contract adherence
        performance_benchmark_threshold=1.0,  # All benchmarks must be met
        code_quality_threshold=0.85,  # Code quality score threshold
        integration_success_threshold=0.95  # 95% integration success rate
    )
    
    return {
        'workspace_root': str(workspace_root),
        'quality_gates': asdict(quality_gates),
        'test_agent': {
            'workspace_path': str(workspace_root / "test_agent" / "workspace"),
            'templates_path': str(workspace_root / "test_agent" / "templates"),
            'output_path': str(workspace_root / "test_agent" / "output"),
            'requirements_source': "docs/software_engineering/docs/01e_USER_STORY_MAPPING.md",
            'interface_specs_source': "docs/software_engineering/docs/04_INTERFACE_SPEC.md",
            'test_framework': "pytest",
            'mock_framework': "unittest.mock"
        },
        'code_agent': {
            'workspace_path': str(workspace_root / "code_agent" / "workspace"),
            'templates_path': str(workspace_root / "code_agent" / "templates"),
            'output_path': str(workspace_root / "code_agent" / "output"),
            'interface_specs_source': "docs/software_engineering/docs/04_INTERFACE_SPEC.md",
            'technical_specs_source': "docs/software_engineering/docs/02_REQUIREMENTS.md",
            'code_style': "black",
            'linter': "flake8"
        },
        'integration_agent': {
            'workspace_path': str(workspace_root / "integration_agent" / "workspace"),
            'templates_path': str(workspace_root / "integration_agent" / "templates"),
            'output_path': str(workspace_root / "integration_agent" / "output"),
            'test_runner': "pytest",
            'retry_attempts': 3
        }
    }


def save_config(config: Dict[str, Any], config_path: Path) -> None:
    """Save configuration to YAML file"""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, indent=2)


def load_config(config_path: Path) -> Dict[str, Any]:
    """Load configuration from YAML file"""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)