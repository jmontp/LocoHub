#!/usr/bin/env python3
"""
Post-Build Validation Hook

Created: 2025-06-19 with user permission
Purpose: MkDocs hook that validates generated documentation site after build

Intent: This hook validates the generated documentation site to ensure all links
work, search is functional, and verification status is properly displayed.
It catches issues that only appear in the final generated site.
"""

import os
import sys
import json
import requests
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse
from typing import Dict, List, Any, Set
from dataclasses import dataclass
from bs4 import BeautifulSoup
import logging

@dataclass
class LinkValidationResult:
    """Result from validating a link"""
    url: str
    source_file: str
    status_code: int
    error: str = None
    redirect_chain: List[str] = None

class PostBuildValidator:
    """Validates the generated documentation site"""
    
    def __init__(self, site_dir: str, site_url: str = None):
        self.site_dir = Path(site_dir)
        self.site_url = site_url or "http://localhost:8000"
        self.validation_results = {}
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Track validated URLs to avoid duplicates
        self.validated_urls = set()
        
    def validate_internal_links(self) -> Dict[str, Any]:
        """Validate all internal links in the generated site"""
        self.logger.info("Validating internal links...")
        
        broken_links = []
        working_links = []
        total_links = 0
        
        try:
            # Find all HTML files
            html_files = list(self.site_dir.rglob("*.html"))
            
            for html_file in html_files:
                try:
                    with open(html_file, 'r', encoding='utf-8') as f:
                        soup = BeautifulSoup(f.read(), 'html.parser')
                    
                    # Find all links
                    links = soup.find_all('a', href=True)
                    
                    for link in links:
                        href = link['href']
                        total_links += 1
                        
                        # Skip external links, anchors, and javascript
                        if (href.startswith(('http://', 'https://')) or 
                            href.startswith('#') or 
                            href.startswith('javascript:') or
                            href.startswith('mailto:')):
                            continue
                        
                        # Resolve relative paths
                        if href.startswith('./') or href.startswith('../'):
                            target_path = (html_file.parent / href).resolve()
                        elif href.startswith('/'):
                            target_path = self.site_dir / href.lstrip('/')
                        else:
                            target_path = html_file.parent / href
                        
                        # Check if target exists
                        if not target_path.exists():
                            # Try with .html extension
                            if not target_path.suffix:
                                target_path = target_path.with_suffix('.html')
                            
                            # Try index.html in directory
                            if target_path.is_dir():
                                target_path = target_path / 'index.html'
                        
                        if target_path.exists():
                            working_links.append({
                                'source': str(html_file.relative_to(self.site_dir)),
                                'target': href,
                                'resolved': str(target_path.relative_to(self.site_dir))
                            })
                        else:
                            broken_links.append({
                                'source': str(html_file.relative_to(self.site_dir)),
                                'target': href,
                                'attempted_path': str(target_path)
                            })
                
                except Exception as e:
                    self.logger.error(f"Error processing {html_file}: {str(e)}")
            
            return {
                'total_links': total_links,
                'working_links': len(working_links),
                'broken_links': len(broken_links),
                'broken_link_details': broken_links,
                'success': len(broken_links) == 0
            }
            
        except Exception as e:
            return {
                'error': f"Internal link validation failed: {str(e)}",
                'success': False
            }
    
    def validate_search_functionality(self) -> Dict[str, Any]:
        """Validate that search index was generated correctly"""
        self.logger.info("Validating search functionality...")
        
        try:
            search_index_path = self.site_dir / 'search' / 'search_index.json'
            
            if not search_index_path.exists():
                return {
                    'error': 'Search index not found',
                    'success': False
                }
            
            # Load and validate search index
            with open(search_index_path, 'r', encoding='utf-8') as f:
                search_index = json.load(f)
            
            # Check structure
            if not isinstance(search_index, dict):
                return {
                    'error': 'Search index is not a valid JSON object',
                    'success': False
                }
            
            # Check for required fields
            docs = search_index.get('docs', [])
            config = search_index.get('config', {})
            
            if not docs:
                return {
                    'error': 'Search index contains no documents',
                    'success': False
                }
            
            # Validate document structure
            invalid_docs = []
            for i, doc in enumerate(docs):
                required_fields = ['title', 'location']
                missing_fields = [field for field in required_fields if field not in doc]
                if missing_fields:
                    invalid_docs.append({
                        'doc_index': i,
                        'missing_fields': missing_fields
                    })
            
            # Check for verification-related content
            verification_docs = [
                doc for doc in docs 
                if 'verification' in doc.get('title', '').lower() or 
                   'verification' in doc.get('text', '').lower()
            ]
            
            return {
                'total_documents': len(docs),
                'invalid_documents': len(invalid_docs),
                'verification_documents': len(verification_docs),
                'search_config': config,
                'invalid_doc_details': invalid_docs,
                'success': len(invalid_docs) == 0
            }
            
        except Exception as e:
            return {
                'error': f"Search validation failed: {str(e)}",
                'success': False
            }
    
    def validate_verification_status_display(self) -> Dict[str, Any]:
        """Validate that verification status is properly displayed"""
        self.logger.info("Validating verification status display...")
        
        try:
            # Check if verification report exists
            verification_report_path = self.site_dir.parent / 'docs' / 'infrastructure' / 'verification_report.json'
            
            if not verification_report_path.exists():
                return {
                    'error': 'Verification report not found',
                    'success': False
                }
            
            # Load verification report
            with open(verification_report_path, 'r') as f:
                verification_report = json.load(f)
            
            # Check for verification status in generated HTML
            index_path = self.site_dir / 'index.html'
            verification_displayed = False
            
            if index_path.exists():
                with open(index_path, 'r', encoding='utf-8') as f:
                    soup = BeautifulSoup(f.read(), 'html.parser')
                
                # Look for verification-related elements
                verification_elements = soup.find_all(attrs={'class': lambda x: x and 'verification' in x.lower()})
                verification_displayed = len(verification_elements) > 0
            
            # Check verification-specific pages
            verification_pages = list(self.site_dir.rglob("*verification*"))
            
            return {
                'verification_report_exists': True,
                'verification_displayed_on_index': verification_displayed,
                'verification_pages': len(verification_pages),
                'verification_summary': verification_report.get('summary', {}),
                'success': verification_displayed or len(verification_pages) > 0
            }
            
        except Exception as e:
            return {
                'error': f"Verification status validation failed: {str(e)}",
                'success': False
            }
    
    def validate_responsive_design(self) -> Dict[str, Any]:
        """Validate basic responsive design elements"""
        self.logger.info("Validating responsive design...")
        
        try:
            responsive_issues = []
            checked_files = 0
            
            # Check CSS files for responsive design rules
            css_files = list(self.site_dir.rglob("*.css"))
            
            has_responsive_css = False
            for css_file in css_files:
                try:
                    with open(css_file, 'r', encoding='utf-8') as f:
                        css_content = f.read()
                    
                    # Check for media queries
                    if '@media' in css_content:
                        has_responsive_css = True
                    
                    checked_files += 1
                    
                except Exception as e:
                    responsive_issues.append(f"Error reading {css_file}: {str(e)}")
            
            # Check HTML files for viewport meta tag
            has_viewport_meta = False
            html_files = list(self.site_dir.rglob("*.html"))
            
            for html_file in html_files[:5]:  # Check first 5 HTML files
                try:
                    with open(html_file, 'r', encoding='utf-8') as f:
                        soup = BeautifulSoup(f.read(), 'html.parser')
                    
                    viewport_meta = soup.find('meta', attrs={'name': 'viewport'})
                    if viewport_meta:
                        has_viewport_meta = True
                        break
                
                except Exception as e:
                    responsive_issues.append(f"Error reading {html_file}: {str(e)}")
            
            return {
                'has_responsive_css': has_responsive_css,
                'has_viewport_meta': has_viewport_meta,
                'css_files_checked': len(css_files),
                'issues': responsive_issues,
                'success': has_responsive_css and has_viewport_meta
            }
            
        except Exception as e:
            return {
                'error': f"Responsive design validation failed: {str(e)}",
                'success': False
            }
    
    def validate_performance_optimizations(self) -> Dict[str, Any]:
        """Validate basic performance optimizations"""
        self.logger.info("Validating performance optimizations...")
        
        try:
            # Check file sizes
            large_files = []
            total_size = 0
            file_count = 0
            
            for file_path in self.site_dir.rglob("*"):
                if file_path.is_file():
                    file_size = file_path.stat().st_size
                    total_size += file_size
                    file_count += 1
                    
                    # Flag large files (>1MB)
                    if file_size > 1024 * 1024:
                        large_files.append({
                            'file': str(file_path.relative_to(self.site_dir)),
                            'size_mb': round(file_size / (1024 * 1024), 2)
                        })
            
            # Check for minified assets
            css_files = list(self.site_dir.rglob("*.css"))
            js_files = list(self.site_dir.rglob("*.js"))
            
            minified_css = sum(1 for f in css_files if '.min.' in f.name)
            minified_js = sum(1 for f in js_files if '.min.' in f.name)
            
            # Check for gzip/compression indicators
            compressed_files = list(self.site_dir.rglob("*.gz"))
            
            return {
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'file_count': file_count,
                'large_files': large_files,
                'css_files': len(css_files),
                'minified_css': minified_css,
                'js_files': len(js_files),
                'minified_js': minified_js,
                'compressed_files': len(compressed_files),
                'success': len(large_files) < 5  # Arbitrary threshold
            }
            
        except Exception as e:
            return {
                'error': f"Performance validation failed: {str(e)}",
                'success': False
            }
    
    def run_all_validations(self) -> Dict[str, Any]:
        """Run all post-build validations"""
        self.logger.info("Starting post-build validation...")
        
        validations = {
            'internal_links': self.validate_internal_links,
            'search_functionality': self.validate_search_functionality,
            'verification_status': self.validate_verification_status_display,
            'responsive_design': self.validate_responsive_design,
            'performance': self.validate_performance_optimizations,
        }
        
        results = {}
        overall_success = True
        
        for name, validation_func in validations.items():
            try:
                self.logger.info(f"Running {name} validation...")
                result = validation_func()
                results[name] = result
                
                if result.get('success', False):
                    self.logger.info(f"✅ {name}: PASSED")
                else:
                    self.logger.error(f"❌ {name}: FAILED")
                    if 'error' in result:
                        self.logger.error(f"   Error: {result['error']}")
                    overall_success = False
                    
            except Exception as e:
                self.logger.error(f"❌ {name}: CRASHED - {str(e)}")
                results[name] = {
                    'error': f"Validation crashed: {str(e)}",
                    'success': False
                }
                overall_success = False
        
        # Generate summary
        summary = {
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'overall_success': overall_success,
            'total_validations': len(validations),
            'passed_validations': sum(1 for r in results.values() if r.get('success', False)),
            'site_directory': str(self.site_dir),
            'validations': results
        }
        
        return summary
    
    def generate_validation_badge(self, results: Dict[str, Any]) -> str:
        """Generate a validation status badge"""
        if results['overall_success']:
            badge_color = "brightgreen"
            badge_text = "verified"
        else:
            badge_color = "red"
            badge_text = "issues"
        
        # Simple badge URL (shields.io format)
        badge_url = f"https://img.shields.io/badge/documentation-{badge_text}-{badge_color}"
        
        return badge_url

def on_post_build(config):
    """MkDocs hook called after build completes"""
    
    # Get the site directory
    site_dir = config.get('site_dir', 'site')
    site_url = config.get('site_url', 'http://localhost:8000')
    
    # Initialize validator
    validator = PostBuildValidator(site_dir, site_url)
    
    # Run all validations
    results = validator.run_all_validations()
    
    # Save validation results
    results_path = Path(site_dir) / 'validation_results.json'
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Generate badge
    badge_url = validator.generate_validation_badge(results)
    
    # Print summary
    print("\n" + "="*60)
    print("📋 POST-BUILD VALIDATION RESULTS")
    print("="*60)
    print(f"Overall Status: {'✅ PASSED' if results['overall_success'] else '❌ FAILED'}")
    print(f"Validations: {results['passed_validations']}/{results['total_validations']} passed")
    
    # Show specific results
    for name, result in results['validations'].items():
        status = "✅ PASSED" if result.get('success', False) else "❌ FAILED"
        print(f"  {name}: {status}")
        
        if not result.get('success', False) and 'error' in result:
            print(f"    Error: {result['error']}")
        
        # Show key metrics
        if name == 'internal_links' and 'broken_links' in result:
            if result['broken_links'] > 0:
                print(f"    Broken links: {result['broken_links']}")
        
        elif name == 'search_functionality' and 'total_documents' in result:
            print(f"    Indexed documents: {result['total_documents']}")
        
        elif name == 'performance' and 'total_size_mb' in result:
            print(f"    Site size: {result['total_size_mb']} MB")
    
    print(f"\nValidation badge: {badge_url}")
    print(f"Full results: {results_path}")
    print("="*60)
    
    # Warning if validations failed (but don't fail the build)
    if not results['overall_success']:
        print("\n⚠️  Post-build validation found issues. See results for details.")
        print("Build completed but site may have problems.")
    else:
        print("\n✅ Post-build validation passed. Site is ready!")
    
    return config

# If run directly, perform standalone validation
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Run post-build validation')
    parser.add_argument('--site-dir', default='site', help='Generated site directory')
    parser.add_argument('--site-url', help='Site URL for validation')
    args = parser.parse_args()
    
    validator = PostBuildValidator(args.site_dir, args.site_url)
    results = validator.run_all_validations()
    
    print(json.dumps(results, indent=2))
    
    if not results['overall_success']:
        sys.exit(1)