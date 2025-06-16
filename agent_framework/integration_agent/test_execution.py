"""
Test Execution Framework for Integration Agent

Created: 2025-01-16 with user permission
Purpose: Comprehensive test execution orchestration and result collection

Intent: Executes Test Agent test suites against Code Agent implementations with
comprehensive result capture, performance monitoring, and systematic reporting.
Maintains neutrality by executing all tests without bias toward pass/fail outcomes.
"""

import time
import traceback
import statistics
import numpy as np
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import concurrent.futures
import threading
import logging


class TestStatus(Enum):
    """Test execution status"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"
    TIMEOUT = "timeout"


class TestType(Enum):
    """Types of tests in test suite"""
    UNIT = "unit"
    INTEGRATION = "integration"
    PERFORMANCE = "performance"
    ERROR_HANDLING = "error_handling"
    USER_ACCEPTANCE = "user_acceptance"
    REGRESSION = "regression"


@dataclass
class TestCase:
    """Individual test case definition"""
    
    name: str
    test_type: TestType
    description: str
    expected_behavior: str
    test_function: callable
    setup_function: Optional[callable] = None
    teardown_function: Optional[callable] = None
    timeout_seconds: float = 30.0
    retry_count: int = 0
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestSuite:
    """Collection of test cases organized by category"""
    
    name: str
    test_cases: List[TestCase]
    setup_suite: Optional[callable] = None
    teardown_suite: Optional[callable] = None
    parallel_execution: bool = True
    timeout_seconds: float = 300.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_tests_by_type(self, test_type: TestType) -> List[TestCase]:
        """Get all tests of specific type"""
        return [test for test in self.test_cases if test.test_type == test_type]


@dataclass
class TestPackage:
    """Complete package of Test Agent output"""
    
    unit_tests: TestSuite
    integration_tests: TestSuite
    performance_tests: TestSuite
    error_handling_tests: TestSuite
    user_acceptance_tests: TestSuite
    performance_requirements: Dict[str, Any]
    behavioral_specifications: Dict[str, Any]
    interface_contracts: Dict[str, Any]
    
    def get_all_test_suites(self) -> List[TestSuite]:
        """Get all test suites in package"""
        return [
            self.unit_tests,
            self.integration_tests,
            self.performance_tests,
            self.error_handling_tests,
            self.user_acceptance_tests
        ]


@dataclass
class ImplementationPackage:
    """Complete package of Code Agent output"""
    
    implementations: Dict[str, Any]
    interface_implementations: Dict[str, Any]
    performance_optimizations: Dict[str, Any]
    error_handling_systems: Dict[str, Any]
    documentation: Dict[str, str]
    architecture_decisions: List[str]
    
    def get_implementation(self, name: str) -> Optional[Any]:
        """Get specific implementation by name"""
        return self.implementations.get(name)
    
    def get_method_signatures(self) -> Dict[str, Any]:
        """Extract method signatures from implementations"""
        signatures = {}
        for name, impl in self.implementations.items():
            # Extract method signatures using reflection
            if hasattr(impl, '__dict__'):
                for attr_name, attr_value in impl.__dict__.items():
                    if callable(attr_value):
                        signatures[f"{name}.{attr_name}"] = attr_value
        return signatures


@dataclass
class TestResult:
    """Individual test execution result"""
    
    test_case: TestCase
    status: TestStatus
    execution_time: float
    start_time: float
    end_time: float
    
    # Result details
    assertion_results: List[Dict[str, Any]] = field(default_factory=list)
    captured_output: str = ""
    error_details: Optional[str] = None
    stack_trace: Optional[str] = None
    
    # Performance metrics
    memory_usage: Dict[str, float] = field(default_factory=dict)
    cpu_usage: float = 0.0
    resource_metrics: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    retry_count: int = 0
    environment_info: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def passed(self) -> bool:
        """Check if test passed"""
        return self.status == TestStatus.PASSED
    
    @property
    def failed(self) -> bool:
        """Check if test failed"""
        return self.status in [TestStatus.FAILED, TestStatus.ERROR, TestStatus.TIMEOUT]


@dataclass
class TestSuiteResult:
    """Results from executing a test suite"""
    
    test_suite: TestSuite
    test_results: List[TestResult]
    execution_time: float
    start_time: float
    end_time: float
    
    # Summary statistics
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    error_tests: int = 0
    
    # Performance summary
    average_execution_time: float = 0.0
    total_memory_usage: float = 0.0
    peak_memory_usage: float = 0.0
    
    def __post_init__(self):
        """Calculate summary statistics"""
        self.total_tests = len(self.test_results)
        self.passed_tests = sum(1 for result in self.test_results if result.status == TestStatus.PASSED)
        self.failed_tests = sum(1 for result in self.test_results if result.status == TestStatus.FAILED)
        self.skipped_tests = sum(1 for result in self.test_results if result.status == TestStatus.SKIPPED)
        self.error_tests = sum(1 for result in self.test_results if result.status == TestStatus.ERROR)
        
        if self.test_results:
            self.average_execution_time = statistics.mean(result.execution_time for result in self.test_results)
            memory_usages = [result.memory_usage.get('peak', 0) for result in self.test_results]
            self.total_memory_usage = sum(memory_usages)
            self.peak_memory_usage = max(memory_usages) if memory_usages else 0
    
    @property
    def pass_rate(self) -> float:
        """Calculate test pass rate"""
        if self.total_tests == 0:
            return 0.0
        return self.passed_tests / self.total_tests
    
    @property
    def success(self) -> bool:
        """Check if suite execution was successful"""
        return self.failed_tests == 0 and self.error_tests == 0


@dataclass
class ComprehensiveTestResults:
    """Complete results from test execution orchestration"""
    
    session_id: str
    test_package: TestPackage
    implementation_package: ImplementationPackage
    
    # Suite results
    unit_test_results: TestSuiteResult
    integration_test_results: TestSuiteResult
    performance_test_results: TestSuiteResult
    error_handling_results: TestSuiteResult
    user_acceptance_results: TestSuiteResult
    
    # Overall metrics
    total_execution_time: float
    overall_pass_rate: float
    overall_success: bool
    
    # Performance metrics
    performance_compliance: Dict[str, Any] = field(default_factory=dict)
    resource_utilization: Dict[str, Any] = field(default_factory=dict)
    
    # Environment information
    execution_environment: Dict[str, Any] = field(default_factory=dict)
    
    def get_all_failures(self) -> List[TestResult]:
        """Get all failed test results"""
        failures = []
        for suite_result in [
            self.unit_test_results,
            self.integration_test_results,
            self.performance_test_results,
            self.error_handling_results,
            self.user_acceptance_results
        ]:
            failures.extend([result for result in suite_result.test_results if result.failed])
        return failures
    
    def has_failures(self) -> bool:
        """Check if any tests failed"""
        return len(self.get_all_failures()) > 0
    
    def get_pass_rate(self) -> float:
        """Get overall pass rate"""
        return self.overall_pass_rate


class TestEnvironment:
    """Test execution environment management"""
    
    def __init__(self):
        self.environment_vars = {}
        self.temp_directories = []
        self.active_resources = []
        
    def setup_environment(self, test_case: TestCase) -> Dict[str, Any]:
        """Setup environment for test case execution"""
        env_info = {
            'test_name': test_case.name,
            'setup_time': time.time(),
            'environment_id': f"env_{int(time.time() * 1000000)}"
        }
        
        # Execute test-specific setup
        if test_case.setup_function:
            test_case.setup_function()
        
        return env_info
    
    def cleanup_environment(self, test_case: TestCase, env_info: Dict[str, Any]):
        """Cleanup environment after test execution"""
        # Execute test-specific teardown
        if test_case.teardown_function:
            test_case.teardown_function()
        
        # Cleanup resources
        self._cleanup_resources()
    
    def _cleanup_resources(self):
        """Internal resource cleanup"""
        # Clean up temporary resources
        pass


class TestExecutionEngine:
    """Core engine for test execution with comprehensive monitoring"""
    
    def __init__(self):
        self.environment = TestEnvironment()
        self.logger = logging.getLogger(__name__)
        
    def execute_test_case(
        self, 
        test_case: TestCase, 
        implementation: Any, 
        environment_info: Dict[str, Any]
    ) -> TestResult:
        """Execute individual test case with comprehensive monitoring"""
        
        start_time = time.perf_counter()
        result = TestResult(
            test_case=test_case,
            status=TestStatus.RUNNING,
            execution_time=0.0,
            start_time=start_time,
            end_time=0.0,
            environment_info=environment_info
        )
        
        try:
            # Setup test environment
            env_setup = self.environment.setup_environment(test_case)
            result.environment_info.update(env_setup)
            
            # Execute test with timeout
            test_execution_result = self._execute_with_timeout(
                test_case.test_function,
                implementation,
                test_case.timeout_seconds
            )
            
            # Process test result
            if test_execution_result['success']:
                result.status = TestStatus.PASSED
                result.assertion_results = test_execution_result.get('assertions', [])
            else:
                result.status = TestStatus.FAILED
                result.error_details = test_execution_result.get('error', 'Test failed')
                result.stack_trace = test_execution_result.get('traceback', '')
            
            result.captured_output = test_execution_result.get('output', '')
            
        except TimeoutError:
            result.status = TestStatus.TIMEOUT
            result.error_details = f"Test exceeded timeout of {test_case.timeout_seconds} seconds"
            
        except Exception as e:
            result.status = TestStatus.ERROR
            result.error_details = str(e)
            result.stack_trace = traceback.format_exc()
            
        finally:
            # Finalize result
            end_time = time.perf_counter()
            result.end_time = end_time
            result.execution_time = end_time - start_time
            
            # Collect performance metrics
            result.memory_usage = self._collect_memory_metrics()
            result.cpu_usage = self._collect_cpu_metrics()
            
            # Cleanup environment
            self.environment.cleanup_environment(test_case, result.environment_info)
        
        return result
    
    def _execute_with_timeout(self, test_function: callable, implementation: Any, timeout: float) -> Dict[str, Any]:
        """Execute test function with timeout protection"""
        
        result = {'success': False, 'assertions': [], 'output': '', 'error': None}
        
        def test_execution():
            try:
                # Capture stdout/stderr
                import io
                import sys
                captured_output = io.StringIO()
                original_stdout = sys.stdout
                original_stderr = sys.stderr
                
                try:
                    sys.stdout = captured_output
                    sys.stderr = captured_output
                    
                    # Execute test function
                    test_result = test_function(implementation)
                    
                    # Process result
                    result['success'] = True
                    result['output'] = captured_output.getvalue()
                    if isinstance(test_result, dict) and 'assertions' in test_result:
                        result['assertions'] = test_result['assertions']
                    
                finally:
                    sys.stdout = original_stdout
                    sys.stderr = original_stderr
                    
            except Exception as e:
                result['success'] = False
                result['error'] = str(e)
                result['traceback'] = traceback.format_exc()
        
        # Execute with timeout
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(test_execution)
            try:
                future.result(timeout=timeout)
            except concurrent.futures.TimeoutError:
                raise TimeoutError(f"Test execution exceeded {timeout} seconds")
        
        return result
    
    def _collect_memory_metrics(self) -> Dict[str, float]:
        """Collect memory usage metrics"""
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            return {
                'rss': memory_info.rss / 1024 / 1024,  # MB
                'vms': memory_info.vms / 1024 / 1024,  # MB
                'peak': process.memory_info().rss / 1024 / 1024  # MB
            }
        except ImportError:
            return {'rss': 0.0, 'vms': 0.0, 'peak': 0.0}
    
    def _collect_cpu_metrics(self) -> float:
        """Collect CPU usage metrics"""
        try:
            import psutil
            return psutil.cpu_percent(interval=None)
        except ImportError:
            return 0.0


class TestResultCollector:
    """Collects and aggregates test execution results"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def collect_suite_results(
        self, 
        test_suite: TestSuite, 
        test_results: List[TestResult]
    ) -> TestSuiteResult:
        """Collect and aggregate results from test suite execution"""
        
        if not test_results:
            return TestSuiteResult(
                test_suite=test_suite,
                test_results=[],
                execution_time=0.0,
                start_time=time.time(),
                end_time=time.time()
            )
        
        # Calculate timing
        start_time = min(result.start_time for result in test_results)
        end_time = max(result.end_time for result in test_results)
        execution_time = end_time - start_time
        
        return TestSuiteResult(
            test_suite=test_suite,
            test_results=test_results,
            execution_time=execution_time,
            start_time=start_time,
            end_time=end_time
        )
    
    def collect_comprehensive_results(
        self,
        session_id: str,
        test_package: TestPackage,
        implementation_package: ImplementationPackage,
        suite_results: Dict[str, TestSuiteResult]
    ) -> ComprehensiveTestResults:
        """Collect comprehensive results from all test suite executions"""
        
        # Calculate overall metrics
        total_tests = sum(suite.total_tests for suite in suite_results.values())
        total_passed = sum(suite.passed_tests for suite in suite_results.values())
        overall_pass_rate = total_passed / total_tests if total_tests > 0 else 0.0
        overall_success = all(suite.success for suite in suite_results.values())
        
        total_execution_time = sum(suite.execution_time for suite in suite_results.values())
        
        return ComprehensiveTestResults(
            session_id=session_id,
            test_package=test_package,
            implementation_package=implementation_package,
            unit_test_results=suite_results.get('unit', self._empty_suite_result()),
            integration_test_results=suite_results.get('integration', self._empty_suite_result()),
            performance_test_results=suite_results.get('performance', self._empty_suite_result()),
            error_handling_results=suite_results.get('error_handling', self._empty_suite_result()),
            user_acceptance_results=suite_results.get('user_acceptance', self._empty_suite_result()),
            total_execution_time=total_execution_time,
            overall_pass_rate=overall_pass_rate,
            overall_success=overall_success
        )
    
    def _empty_suite_result(self) -> TestSuiteResult:
        """Create empty suite result for missing test types"""
        empty_suite = TestSuite("empty", [])
        return TestSuiteResult(
            test_suite=empty_suite,
            test_results=[],
            execution_time=0.0,
            start_time=time.time(),
            end_time=time.time()
        )


class TestExecutionOrchestrator:
    """Orchestrates comprehensive test execution across all test categories"""
    
    def __init__(self):
        self.execution_engine = TestExecutionEngine()
        self.result_collector = TestResultCollector()
        self.logger = logging.getLogger(__name__)
        
    def execute_complete_test_suite(
        self, 
        test_package: TestPackage, 
        implementation_package: ImplementationPackage
    ) -> ComprehensiveTestResults:
        """Execute complete test suite against implementation package"""
        
        session_id = f"test_session_{int(time.time())}"
        self.logger.info(f"Starting comprehensive test execution: {session_id}")
        
        suite_results = {}
        
        # Execute each test suite type
        test_suite_mapping = {
            'unit': test_package.unit_tests,
            'integration': test_package.integration_tests,
            'performance': test_package.performance_tests,
            'error_handling': test_package.error_handling_tests,
            'user_acceptance': test_package.user_acceptance_tests
        }
        
        for suite_name, test_suite in test_suite_mapping.items():
            if test_suite and test_suite.test_cases:
                self.logger.info(f"Executing {suite_name} test suite")
                suite_result = self._execute_test_suite(test_suite, implementation_package)
                suite_results[suite_name] = suite_result
            else:
                self.logger.warning(f"No {suite_name} tests found, skipping")
        
        # Collect comprehensive results
        comprehensive_results = self.result_collector.collect_comprehensive_results(
            session_id,
            test_package,
            implementation_package,
            suite_results
        )
        
        self.logger.info(f"Test execution completed: {comprehensive_results.overall_pass_rate:.2%} pass rate")
        
        return comprehensive_results
    
    def _execute_test_suite(
        self, 
        test_suite: TestSuite, 
        implementation_package: ImplementationPackage
    ) -> TestSuiteResult:
        """Execute individual test suite with comprehensive monitoring"""
        
        self.logger.debug(f"Executing test suite: {test_suite.name}")
        
        # Suite setup
        if test_suite.setup_suite:
            test_suite.setup_suite()
        
        try:
            # Execute tests (parallel or sequential based on suite configuration)
            if test_suite.parallel_execution:
                test_results = self._execute_tests_parallel(test_suite, implementation_package)
            else:
                test_results = self._execute_tests_sequential(test_suite, implementation_package)
            
        finally:
            # Suite teardown
            if test_suite.teardown_suite:
                test_suite.teardown_suite()
        
        # Collect suite results
        suite_result = self.result_collector.collect_suite_results(test_suite, test_results)
        
        self.logger.debug(f"Suite completed: {suite_result.pass_rate:.2%} pass rate")
        
        return suite_result
    
    def _execute_tests_parallel(
        self, 
        test_suite: TestSuite, 
        implementation_package: ImplementationPackage
    ) -> List[TestResult]:
        """Execute tests in parallel for performance"""
        
        test_results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            # Submit all test executions
            future_to_test = {}
            for test_case in test_suite.test_cases:
                implementation = implementation_package.get_implementation(test_case.name)
                env_info = {'execution_mode': 'parallel'}
                
                future = executor.submit(
                    self.execution_engine.execute_test_case,
                    test_case,
                    implementation,
                    env_info
                )
                future_to_test[future] = test_case
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_test):
                try:
                    result = future.result()
                    test_results.append(result)
                except Exception as e:
                    test_case = future_to_test[future]
                    self.logger.error(f"Test execution failed: {test_case.name}: {e}")
                    
                    # Create error result
                    error_result = TestResult(
                        test_case=test_case,
                        status=TestStatus.ERROR,
                        execution_time=0.0,
                        start_time=time.time(),
                        end_time=time.time(),
                        error_details=str(e)
                    )
                    test_results.append(error_result)
        
        return test_results
    
    def _execute_tests_sequential(
        self, 
        test_suite: TestSuite, 
        implementation_package: ImplementationPackage
    ) -> List[TestResult]:
        """Execute tests sequentially for reliability"""
        
        test_results = []
        
        for test_case in test_suite.test_cases:
            try:
                implementation = implementation_package.get_implementation(test_case.name)
                env_info = {'execution_mode': 'sequential'}
                
                result = self.execution_engine.execute_test_case(
                    test_case,
                    implementation,
                    env_info
                )
                test_results.append(result)
                
            except Exception as e:
                self.logger.error(f"Test execution failed: {test_case.name}: {e}")
                
                # Create error result
                error_result = TestResult(
                    test_case=test_case,
                    status=TestStatus.ERROR,
                    execution_time=0.0,
                    start_time=time.time(),
                    end_time=time.time(),
                    error_details=str(e)
                )
                test_results.append(error_result)
        
        return test_results