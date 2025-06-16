"""
Code Agent Framework

Created: 2025-01-16 with user permission
Purpose: Code Agent framework for interface contract processing and code generation

Intent: Implements the three-agent development orchestration pattern with contract-driven
development. The Code Agent generates high-quality implementations from interface contracts
without accessing test implementations to ensure unbiased, optimal code generation.
"""

from .core import CodeAgent
from .contract_parser import InterfaceContractParser
from .code_generator import CodeGenerator
from .validation_framework import ImplementationValidator
from .performance_optimizer import PerformanceOptimizer

__all__ = [
    'CodeAgent',
    'InterfaceContractParser', 
    'CodeGenerator',
    'ImplementationValidator',
    'PerformanceOptimizer'
]

__version__ = '1.0.0'