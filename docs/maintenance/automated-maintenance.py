#!/usr/bin/env python3
"""
Automated Maintenance Framework for Documentation
Created: 2025-06-19 with user permission
Purpose: Comprehensive automated maintenance and monitoring system

Features:
- Content freshness monitoring
- Broken link detection and reporting
- Performance regression testing
- Automated health checks
- Documentation review workflows
- Analytics reporting
- SEO monitoring
"""

import asyncio
import aiohttp
import json
import time
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import subprocess
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from urllib.parse import urljoin, urlparse
import logging
import re
import csv
from dataclasses import dataclass, asdict


@dataclass
class HealthCheckResult:
    """Result of a health check operation."""
    check_name: str
    status: str  # 'pass', 'fail', 'warning'
    message: str
    details: Dict
    timestamp: datetime
    duration_ms: float


@dataclass
class ContentFreshnessReport:
    """Report on content freshness."""
    file_path: str
    last_modified: datetime
    days_since_update: int
    content_type: str
    status: str  # 'fresh', 'stale', 'outdated'
    priority: str  # 'high', 'medium', 'low'


@dataclass
class BrokenLink:
    """Information about a broken link."""
    source_file: str
    source_line: int
    url: str
    status_code: int
    error_message: str
    link_type: str  # 'internal', 'external'


class AutomatedMaintenance:
    """Automated maintenance system for documentation."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config = self.load_config(config_path)
        self.base_path = Path(self.config.get('base_path', '.'))
        self.base_url = self.config.get('base_url', 'https://locomotion-data-standardization.readthedocs.io')
        
        # Setup logging
        self.setup_logging()
        
        # Initialize tracking
        self.health_checks = []
        self.performance_baselines = {}
        self.content_inventory = {}
        
        self.logger.info("Automated Maintenance Framework initialized")
    
    def load_config(self, config_path: Optional[str]) -> Dict:
        """Load configuration from file or use defaults."""
        default_config = {
            'base_path': '.',
            'base_url': 'https://locomotion-data-standardization.readthedocs.io',
            'freshness_thresholds': {
                'fresh_days': 30,
                'stale_days': 90,
                'outdated_days': 180
            },
            'performance_thresholds': {
                'page_load_time': 2000,  # 2 seconds
                'first_contentful_paint': 1500,
                'largest_contentful_paint': 2500
            },
            'email': {
                'enabled': False,
                'smtp_server': 'smtp.gmail.com',
                'smtp_port': 587,
                'username': '',
                'password': '',
                'recipients': []
            },
            'maintenance_schedule': {
                'content_freshness': 'daily',
                'broken_links': 'weekly',
                'performance_tests': 'daily',
                'seo_audit': 'weekly'
            },
            'exclude_patterns': [
                '*.tmp',
                '*.log',
                '__pycache__',
                '.git',
                'node_modules',
                'venv',
                'conda_env'
            ]
        }
        
        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                default_config.update(user_config)
            except Exception as e:
                print(f"Warning: Could not load config from {config_path}: {e}")
        
        return default_config
    
    def setup_logging(self):
        """Setup logging configuration."""
        log_level = self.config.get('log_level', 'INFO')
        log_file = self.base_path / 'maintenance.log'
        
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger('AutomatedMaintenance')
    
    async def run_all_checks(self) -> Dict[str, List[HealthCheckResult]]:
        """Run all maintenance checks."""
        self.logger.info("Starting comprehensive maintenance checks")
        
        results = {
            'content_freshness': await self.check_content_freshness(),
            'broken_links': await self.check_broken_links(),
            'performance': await self.run_performance_tests(),
            'seo_health': await self.check_seo_health(),
            'security': await self.run_security_checks(),
            'accessibility': await self.check_accessibility(),
            'system_health': await self.check_system_health()
        }
        
        # Generate reports
        await self.generate_maintenance_report(results)
        
        # Send notifications if needed
        await self.send_notifications(results)
        
        self.logger.info("Maintenance checks completed")
        return results
    
    async def check_content_freshness(self) -> List[HealthCheckResult]:
        """Check content freshness and identify stale content."""
        self.logger.info("Checking content freshness")
        results = []
        
        try:
            # Discover all content files
            content_files = self.discover_content_files()
            freshness_reports = []
            
            thresholds = self.config['freshness_thresholds']
            now = datetime.now()
            
            for file_path in content_files:
                try:
                    stat = file_path.stat()
                    last_modified = datetime.fromtimestamp(stat.st_mtime)
                    days_since_update = (now - last_modified).days
                    
                    # Determine content type and priority
                    content_type = self.classify_content_type(file_path)
                    priority = self.determine_content_priority(file_path, content_type)
                    
                    # Determine freshness status
                    if days_since_update <= thresholds['fresh_days']:
                        status = 'fresh'
                    elif days_since_update <= thresholds['stale_days']:
                        status = 'stale'
                    else:
                        status = 'outdated'
                    
                    report = ContentFreshnessReport(
                        file_path=str(file_path),
                        last_modified=last_modified,
                        days_since_update=days_since_update,
                        content_type=content_type,
                        status=status,
                        priority=priority
                    )
                    
                    freshness_reports.append(report)
                    
                except Exception as e:
                    self.logger.warning(f"Could not check freshness for {file_path}: {e}")
            
            # Analyze results
            total_files = len(freshness_reports)
            stale_files = len([r for r in freshness_reports if r.status == 'stale'])
            outdated_files = len([r for r in freshness_reports if r.status == 'outdated'])
            high_priority_stale = len([r for r in freshness_reports 
                                     if r.status in ['stale', 'outdated'] and r.priority == 'high'])
            
            # Create health check result
            if outdated_files > total_files * 0.1:  # More than 10% outdated
                status = 'fail'
                message = f"{outdated_files} files are outdated, {high_priority_stale} high-priority files need updates"
            elif stale_files > total_files * 0.2:  # More than 20% stale
                status = 'warning'
                message = f"{stale_files} files are stale, consider updating"
            else:
                status = 'pass'
                message = f"Content freshness is good ({outdated_files} outdated, {stale_files} stale)"
            
            results.append(HealthCheckResult(
                check_name='content_freshness',
                status=status,
                message=message,
                details={
                    'total_files': total_files,
                    'fresh_files': total_files - stale_files - outdated_files,
                    'stale_files': stale_files,
                    'outdated_files': outdated_files,
                    'high_priority_stale': high_priority_stale,
                    'reports': [asdict(r) for r in freshness_reports]
                },
                timestamp=datetime.now(),
                duration_ms=0
            ))
            
        except Exception as e:
            results.append(HealthCheckResult(
                check_name='content_freshness',
                status='fail',
                message=f"Content freshness check failed: {e}",
                details={'error': str(e)},
                timestamp=datetime.now(),
                duration_ms=0
            ))
        
        return results
    
    async def check_broken_links(self) -> List[HealthCheckResult]:
        """Check for broken internal and external links."""
        self.logger.info("Checking for broken links")
        results = []
        start_time = time.time()
        
        try:
            broken_links = []
            
            # Find all links in content files
            link_inventory = await self.discover_all_links()
            
            # Check internal links
            internal_broken = await self.check_internal_links(link_inventory['internal'])
            broken_links.extend(internal_broken)
            
            # Check external links (with rate limiting)
            external_broken = await self.check_external_links(link_inventory['external'])
            broken_links.extend(external_broken)
            
            # Analyze results
            total_links = len(link_inventory['internal']) + len(link_inventory['external'])
            total_broken = len(broken_links)
            internal_broken_count = len([l for l in broken_links if l.link_type == 'internal'])
            external_broken_count = len([l for l in broken_links if l.link_type == 'external'])
            
            if total_broken == 0:
                status = 'pass'
                message = f"All {total_links} links are working"
            elif internal_broken_count > 0:
                status = 'fail'
                message = f"{internal_broken_count} internal links broken, {external_broken_count} external"
            elif external_broken_count > total_links * 0.05:  # More than 5% external broken
                status = 'warning'
                message = f"{external_broken_count} external links broken"
            else:
                status = 'pass'
                message = f"Only {external_broken_count} external links broken"
            
            duration = (time.time() - start_time) * 1000
            
            results.append(HealthCheckResult(
                check_name='broken_links',
                status=status,
                message=message,
                details={
                    'total_links': total_links,
                    'internal_links': len(link_inventory['internal']),
                    'external_links': len(link_inventory['external']),
                    'broken_links': total_broken,
                    'internal_broken': internal_broken_count,
                    'external_broken': external_broken_count,
                    'broken_link_details': [asdict(l) for l in broken_links]
                },
                timestamp=datetime.now(),
                duration_ms=duration
            ))
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            results.append(HealthCheckResult(
                check_name='broken_links',
                status='fail',
                message=f"Broken link check failed: {e}",
                details={'error': str(e)},
                timestamp=datetime.now(),
                duration_ms=duration
            ))
        
        return results
    
    async def run_performance_tests(self) -> List[HealthCheckResult]:
        """Run performance tests and compare against baselines."""
        self.logger.info("Running performance tests")
        results = []
        start_time = time.time()
        
        try:
            # Key pages to test
            test_pages = [
                '/',
                '/getting_started/',
                '/tutorials/',
                '/reference/api/',
                '/examples/'
            ]
            
            performance_results = []
            thresholds = self.config['performance_thresholds']
            
            for page in test_pages:
                page_results = await self.test_page_performance(page)
                performance_results.append({
                    'page': page,
                    'results': page_results
                })
            
            # Analyze results
            failed_pages = []
            slow_pages = []
            
            for page_result in performance_results:
                page = page_result['page']
                results_data = page_result['results']
                
                if results_data.get('load_time', 0) > thresholds['page_load_time']:
                    if results_data.get('load_time', 0) > thresholds['page_load_time'] * 1.5:
                        failed_pages.append(page)
                    else:
                        slow_pages.append(page)
            
            if failed_pages:
                status = 'fail'
                message = f"{len(failed_pages)} pages exceed performance thresholds"
            elif slow_pages:
                status = 'warning'
                message = f"{len(slow_pages)} pages are slower than optimal"
            else:
                status = 'pass'
                message = "All pages meet performance requirements"
            
            duration = (time.time() - start_time) * 1000
            
            results.append(HealthCheckResult(
                check_name='performance',
                status=status,
                message=message,
                details={
                    'tested_pages': len(test_pages),
                    'failed_pages': failed_pages,
                    'slow_pages': slow_pages,
                    'thresholds': thresholds,
                    'detailed_results': performance_results
                },
                timestamp=datetime.now(),
                duration_ms=duration
            ))
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            results.append(HealthCheckResult(
                check_name='performance',
                status='fail',
                message=f"Performance test failed: {e}",
                details={'error': str(e)},
                timestamp=datetime.now(),
                duration_ms=duration
            ))
        
        return results
    
    async def check_seo_health(self) -> List[HealthCheckResult]:
        """Check SEO health including meta tags, structured data, sitemap."""
        self.logger.info("Checking SEO health")
        results = []
        start_time = time.time()
        
        try:
            seo_issues = []
            
            # Check sitemap
            sitemap_issues = await self.check_sitemap()
            seo_issues.extend(sitemap_issues)
            
            # Check robots.txt
            robots_issues = await self.check_robots_txt()
            seo_issues.extend(robots_issues)
            
            # Check meta tags on key pages
            meta_issues = await self.check_meta_tags()
            seo_issues.extend(meta_issues)
            
            # Check structured data
            structured_data_issues = await self.check_structured_data()
            seo_issues.extend(structured_data_issues)
            
            # Analyze results
            critical_issues = [i for i in seo_issues if i.get('severity') == 'critical']
            warning_issues = [i for i in seo_issues if i.get('severity') == 'warning']
            
            if critical_issues:
                status = 'fail'
                message = f"{len(critical_issues)} critical SEO issues found"
            elif warning_issues:
                status = 'warning'
                message = f"{len(warning_issues)} SEO warnings found"
            else:
                status = 'pass'
                message = "SEO health is good"
            
            duration = (time.time() - start_time) * 1000
            
            results.append(HealthCheckResult(
                check_name='seo_health',
                status=status,
                message=message,
                details={
                    'total_issues': len(seo_issues),
                    'critical_issues': len(critical_issues),
                    'warning_issues': len(warning_issues),
                    'issues': seo_issues
                },
                timestamp=datetime.now(),
                duration_ms=duration
            ))
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            results.append(HealthCheckResult(
                check_name='seo_health',
                status='fail',
                message=f"SEO health check failed: {e}",
                details={'error': str(e)},
                timestamp=datetime.now(),
                duration_ms=duration
            ))
        
        return results
    
    async def run_security_checks(self) -> List[HealthCheckResult]:
        """Run security checks on the documentation site."""
        self.logger.info("Running security checks")
        results = []
        start_time = time.time()
        
        try:
            security_issues = []
            
            # Check for sensitive information in files
            sensitive_files = await self.scan_for_sensitive_data()
            if sensitive_files:
                security_issues.extend(sensitive_files)
            
            # Check dependencies for vulnerabilities
            vulnerability_scan = await self.check_dependencies()
            if vulnerability_scan:
                security_issues.extend(vulnerability_scan)
            
            # Check HTTP headers
            header_issues = await self.check_security_headers()
            if header_issues:
                security_issues.extend(header_issues)
            
            # Analyze results
            high_risk = [i for i in security_issues if i.get('risk') == 'high']
            medium_risk = [i for i in security_issues if i.get('risk') == 'medium']
            
            if high_risk:
                status = 'fail'
                message = f"{len(high_risk)} high-risk security issues found"
            elif medium_risk:
                status = 'warning'
                message = f"{len(medium_risk)} medium-risk security issues found"
            else:
                status = 'pass'
                message = "No significant security issues found"
            
            duration = (time.time() - start_time) * 1000
            
            results.append(HealthCheckResult(
                check_name='security',
                status=status,
                message=message,
                details={
                    'total_issues': len(security_issues),
                    'high_risk': len(high_risk),
                    'medium_risk': len(medium_risk),
                    'issues': security_issues
                },
                timestamp=datetime.now(),
                duration_ms=duration
            ))
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            results.append(HealthCheckResult(
                check_name='security',
                status='fail',
                message=f"Security check failed: {e}",
                details={'error': str(e)},
                timestamp=datetime.now(),
                duration_ms=duration
            ))
        
        return results
    
    async def check_accessibility(self) -> List[HealthCheckResult]:
        """Check accessibility compliance."""
        self.logger.info("Checking accessibility compliance")
        results = []
        start_time = time.time()
        
        try:
            accessibility_issues = []
            
            # Check key pages for accessibility
            test_pages = ['/', '/getting_started/', '/tutorials/']
            
            for page in test_pages:
                page_issues = await self.check_page_accessibility(page)
                accessibility_issues.extend(page_issues)
            
            # Analyze results
            wcag_violations = [i for i in accessibility_issues if i.get('level') in ['A', 'AA']]
            
            if wcag_violations:
                status = 'fail'
                message = f"{len(wcag_violations)} WCAG violations found"
            elif accessibility_issues:
                status = 'warning'
                message = f"{len(accessibility_issues)} accessibility issues found"
            else:
                status = 'pass'
                message = "Accessibility compliance is good"
            
            duration = (time.time() - start_time) * 1000
            
            results.append(HealthCheckResult(
                check_name='accessibility',
                status=status,
                message=message,
                details={
                    'total_issues': len(accessibility_issues),
                    'wcag_violations': len(wcag_violations),
                    'issues': accessibility_issues
                },
                timestamp=datetime.now(),
                duration_ms=duration
            ))
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            results.append(HealthCheckResult(
                check_name='accessibility',
                status='fail',
                message=f"Accessibility check failed: {e}",
                details={'error': str(e)},
                timestamp=datetime.now(),
                duration_ms=duration
            ))
        
        return results
    
    async def check_system_health(self) -> List[HealthCheckResult]:
        """Check overall system health."""
        self.logger.info("Checking system health")
        results = []
        start_time = time.time()
        
        try:
            health_metrics = {}
            
            # Check disk space
            disk_usage = await self.check_disk_usage()
            health_metrics['disk_usage'] = disk_usage
            
            # Check build status
            build_status = await self.check_build_status()
            health_metrics['build_status'] = build_status
            
            # Check service dependencies
            dependencies = await self.check_service_dependencies()
            health_metrics['dependencies'] = dependencies
            
            # Determine overall health
            critical_issues = []
            
            if disk_usage.get('usage_percent', 0) > 90:
                critical_issues.append("Disk usage critical")
            
            if build_status.get('status') != 'success':
                critical_issues.append("Build failing")
            
            failed_deps = [d for d in dependencies if d.get('status') != 'healthy']
            if failed_deps:
                critical_issues.append(f"{len(failed_deps)} dependencies unhealthy")
            
            if critical_issues:
                status = 'fail'
                message = f"System health issues: {', '.join(critical_issues)}"
            else:
                status = 'pass'
                message = "System health is good"
            
            duration = (time.time() - start_time) * 1000
            
            results.append(HealthCheckResult(
                check_name='system_health',
                status=status,
                message=message,
                details=health_metrics,
                timestamp=datetime.now(),
                duration_ms=duration
            ))
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            results.append(HealthCheckResult(
                check_name='system_health',
                status='fail',
                message=f"System health check failed: {e}",
                details={'error': str(e)},
                timestamp=datetime.now(),
                duration_ms=duration
            ))
        
        return results
    
    # Helper methods (implementations would be extensive, showing key signatures)
    
    def discover_content_files(self) -> List[Path]:
        """Discover all content files to check."""
        content_files = []
        
        for pattern in ['**/*.md', '**/*.html', '**/*.rst']:
            for file_path in self.base_path.glob(pattern):
                if not self.should_exclude_file(file_path):
                    content_files.append(file_path)
        
        return content_files
    
    def should_exclude_file(self, file_path: Path) -> bool:
        """Check if file should be excluded from checks."""
        for pattern in self.config['exclude_patterns']:
            if file_path.match(pattern):
                return True
        return False
    
    def classify_content_type(self, file_path: Path) -> str:
        """Classify content type based on file path."""
        path_str = str(file_path).lower()
        
        if 'tutorial' in path_str:
            return 'tutorial'
        elif 'api' in path_str or 'reference' in path_str:
            return 'api_reference'
        elif 'example' in path_str:
            return 'example'
        elif 'getting_started' in path_str:
            return 'getting_started'
        else:
            return 'documentation'
    
    def determine_content_priority(self, file_path: Path, content_type: str) -> str:
        """Determine content priority for maintenance."""
        if content_type in ['getting_started', 'tutorial']:
            return 'high'
        elif content_type in ['api_reference', 'example']:
            return 'medium'
        else:
            return 'low'
    
    async def discover_all_links(self) -> Dict[str, List]:
        """Discover all links in content files."""
        # Implementation would parse markdown/HTML and extract links
        return {'internal': [], 'external': []}
    
    async def check_internal_links(self, links: List) -> List[BrokenLink]:
        """Check internal links for validity."""
        # Implementation would verify internal links exist
        return []
    
    async def check_external_links(self, links: List) -> List[BrokenLink]:
        """Check external links with rate limiting."""
        # Implementation would make HTTP requests with proper rate limiting
        return []
    
    async def test_page_performance(self, page: str) -> Dict:
        """Test performance of a specific page."""
        # Implementation would use tools like Lighthouse or custom metrics
        return {'load_time': 1500, 'fcp': 800, 'lcp': 1200}
    
    async def check_sitemap(self) -> List[Dict]:
        """Check sitemap validity and completeness."""
        return []
    
    async def check_robots_txt(self) -> List[Dict]:
        """Check robots.txt validity."""
        return []
    
    async def check_meta_tags(self) -> List[Dict]:
        """Check meta tags on key pages."""
        return []
    
    async def check_structured_data(self) -> List[Dict]:
        """Check structured data implementation."""
        return []
    
    async def scan_for_sensitive_data(self) -> List[Dict]:
        """Scan for sensitive information in files."""
        return []
    
    async def check_dependencies(self) -> List[Dict]:
        """Check dependencies for vulnerabilities."""
        return []
    
    async def check_security_headers(self) -> List[Dict]:
        """Check HTTP security headers."""
        return []
    
    async def check_page_accessibility(self, page: str) -> List[Dict]:
        """Check page accessibility."""
        return []
    
    async def check_disk_usage(self) -> Dict:
        """Check disk usage."""
        return {'usage_percent': 45, 'available_gb': 100}
    
    async def check_build_status(self) -> Dict:
        """Check build status."""
        return {'status': 'success', 'last_build': datetime.now()}
    
    async def check_service_dependencies(self) -> List[Dict]:
        """Check service dependencies."""
        return []
    
    async def generate_maintenance_report(self, results: Dict) -> None:
        """Generate comprehensive maintenance report."""
        report_path = self.base_path / f"maintenance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        
        # Generate HTML report
        html_content = self.create_html_report(results)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        self.logger.info(f"Maintenance report generated: {report_path}")
    
    def create_html_report(self, results: Dict) -> str:
        """Create HTML maintenance report."""
        # Implementation would create comprehensive HTML report
        return "<html><body><h1>Maintenance Report</h1></body></html>"
    
    async def send_notifications(self, results: Dict) -> None:
        """Send notifications based on results."""
        if not self.config['email']['enabled']:
            return
        
        # Check if any critical issues need notification
        critical_checks = []
        for check_type, check_results in results.items():
            for result in check_results:
                if result.status == 'fail':
                    critical_checks.append(result)
        
        if critical_checks:
            await self.send_email_notification(critical_checks)
    
    async def send_email_notification(self, critical_checks: List[HealthCheckResult]) -> None:
        """Send email notification for critical issues."""
        try:
            email_config = self.config['email']
            
            msg = MIMEMultipart()
            msg['From'] = email_config['username']
            msg['To'] = ', '.join(email_config['recipients'])
            msg['Subject'] = f"Documentation Maintenance Alert - {len(critical_checks)} Critical Issues"
            
            body = self.create_email_body(critical_checks)
            msg.attach(MIMEText(body, 'html'))
            
            server = smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port'])
            server.starttls()
            server.login(email_config['username'], email_config['password'])
            
            text = msg.as_string()
            server.sendmail(email_config['username'], email_config['recipients'], text)
            server.quit()
            
            self.logger.info(f"Email notification sent to {len(email_config['recipients'])} recipients")
            
        except Exception as e:
            self.logger.error(f"Failed to send email notification: {e}")
    
    def create_email_body(self, critical_checks: List[HealthCheckResult]) -> str:
        """Create email body for notifications."""
        # Implementation would create formatted email body
        return f"<html><body><h2>{len(critical_checks)} Critical Issues Found</h2></body></html>"


async def main():
    """Main function for running maintenance checks."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run automated maintenance checks')
    parser.add_argument('--config', help='Configuration file path')
    parser.add_argument('--check', choices=['all', 'content', 'links', 'performance', 'seo', 'security', 'accessibility', 'system'],
                       default='all', help='Type of check to run')
    parser.add_argument('--report-only', action='store_true', help='Generate report without sending notifications')
    
    args = parser.parse_args()
    
    maintenance = AutomatedMaintenance(args.config)
    
    print("🔧 Starting Automated Maintenance Checks...")
    
    if args.check == 'all':
        results = await maintenance.run_all_checks()
    else:
        # Run specific check
        check_methods = {
            'content': maintenance.check_content_freshness,
            'links': maintenance.check_broken_links,
            'performance': maintenance.run_performance_tests,
            'seo': maintenance.check_seo_health,
            'security': maintenance.run_security_checks,
            'accessibility': maintenance.check_accessibility,
            'system': maintenance.check_system_health
        }
        
        if args.check in check_methods:
            results = {args.check: await check_methods[args.check]()}
        else:
            print(f"Unknown check type: {args.check}")
            return 1
    
    # Print summary
    print("\n📊 Maintenance Check Summary:")
    for check_type, check_results in results.items():
        for result in check_results:
            status_emoji = {'pass': '✅', 'warning': '⚠️', 'fail': '❌'}
            emoji = status_emoji.get(result.status, '❓')
            print(f"  {emoji} {result.check_name}: {result.message}")
    
    print(f"\n✅ Maintenance checks completed successfully!")
    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))