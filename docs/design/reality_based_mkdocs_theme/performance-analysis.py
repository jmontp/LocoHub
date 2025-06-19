#!/usr/bin/env python3
"""
Documentation Site Performance Analysis
Created: 2025-06-19 with user permission
Purpose: Analyze and optimize documentation site performance

This script analyzes the performance characteristics of the documentation
site and provides recommendations for optimization.
"""

import os
import gzip
import json
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class PerformanceMetrics:
    """Performance metrics for documentation files."""
    file_path: str
    file_size: int
    gzipped_size: int
    compression_ratio: float
    complexity_score: int
    load_time_estimate: float


class DocumentationPerformanceAnalyzer:
    """Analyzes documentation site performance characteristics."""
    
    def __init__(self, docs_root: str):
        self.docs_root = Path(docs_root)
        self.css_file = self.docs_root / "docs/design/reality_based_mkdocs_theme/extra.css"
        self.js_file = self.docs_root / "docs/design/reality_based_mkdocs_theme/enhanced-interactivity.js"
        self.results = {}
        
    def analyze_css_performance(self) -> Dict:
        """Analyze CSS file performance characteristics."""
        if not self.css_file.exists():
            return {"error": "CSS file not found"}
            
        with open(self.css_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Calculate file sizes
        original_size = len(content.encode('utf-8'))
        gzipped_content = gzip.compress(content.encode('utf-8'))
        gzipped_size = len(gzipped_content)
        compression_ratio = (original_size - gzipped_size) / original_size * 100
        
        # Analyze CSS complexity
        selectors = content.count('{')
        properties = content.count(':')
        media_queries = content.count('@media')
        custom_properties = content.count('--')
        
        # Calculate performance metrics
        complexity_score = selectors + (properties * 0.1) + (media_queries * 2)
        load_time_estimate = gzipped_size / 1024 / 100  # Rough estimate in seconds
        
        return {
            "file": "extra.css",
            "original_size_kb": round(original_size / 1024, 2),
            "gzipped_size_kb": round(gzipped_size / 1024, 2),
            "compression_ratio": round(compression_ratio, 1),
            "selectors_count": selectors,
            "properties_count": properties,
            "media_queries": media_queries,
            "custom_properties": custom_properties,
            "complexity_score": round(complexity_score, 1),
            "estimated_load_time_ms": round(load_time_estimate * 1000, 1),
            "performance_grade": self._calculate_css_grade(original_size, complexity_score)
        }
    
    def analyze_js_performance(self) -> Dict:
        """Analyze JavaScript file performance characteristics."""
        if not self.js_file.exists():
            return {"error": "JavaScript file not found"}
            
        with open(self.js_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Calculate file sizes
        original_size = len(content.encode('utf-8'))
        gzipped_content = gzip.compress(content.encode('utf-8'))
        gzipped_size = len(gzipped_content)
        compression_ratio = (original_size - gzipped_size) / original_size * 100
        
        # Analyze JavaScript complexity
        functions = content.count('function') + content.count('=>')
        event_listeners = content.count('addEventListener')
        dom_queries = content.count('querySelector') + content.count('getElementById')
        loops = content.count('forEach') + content.count('for (') + content.count('while (')
        
        # Calculate performance metrics
        complexity_score = functions + (event_listeners * 2) + (dom_queries * 1.5) + (loops * 1.2)
        load_time_estimate = gzipped_size / 1024 / 200  # Rough estimate in seconds
        
        return {
            "file": "enhanced-interactivity.js",
            "original_size_kb": round(original_size / 1024, 2),
            "gzipped_size_kb": round(gzipped_size / 1024, 2),
            "compression_ratio": round(compression_ratio, 1),
            "functions_count": functions,
            "event_listeners": event_listeners,
            "dom_queries": dom_queries,
            "loops_count": loops,
            "complexity_score": round(complexity_score, 1),
            "estimated_load_time_ms": round(load_time_estimate * 1000, 1),
            "performance_grade": self._calculate_js_grade(original_size, complexity_score)
        }
    
    def analyze_accessibility_features(self) -> Dict:
        """Analyze accessibility features implementation."""
        css_content = ""
        js_content = ""
        
        if self.css_file.exists():
            with open(self.css_file, 'r', encoding='utf-8') as f:
                css_content = f.read()
                
        if self.js_file.exists():
            with open(self.js_file, 'r', encoding='utf-8') as f:
                js_content = f.read()
        
        # Check accessibility features in CSS
        css_features = {
            "high_contrast_support": "prefers-contrast: high" in css_content,
            "reduced_motion_support": "prefers-reduced-motion" in css_content,
            "focus_indicators": "outline:" in css_content and "focus" in css_content,
            "skip_links": "skip-link" in css_content,
            "screen_reader_support": "sr-only" in css_content,
            "keyboard_navigation": "focus-visible" in css_content,
            "aria_support": "aria-" in css_content
        }
        
        # Check accessibility features in JavaScript
        js_features = {
            "keyboard_event_handling": "keydown" in js_content or "keyup" in js_content,
            "aria_management": "aria-" in js_content,
            "focus_management": "focus(" in js_content,
            "screen_reader_announcements": "announce" in js_content,
            "live_regions": "aria-live" in js_content,
            "tab_trapping": "tabindex" in js_content
        }
        
        total_features = len(css_features) + len(js_features)
        implemented_features = sum(css_features.values()) + sum(js_features.values())
        accessibility_score = (implemented_features / total_features) * 100
        
        return {
            "css_accessibility_features": css_features,
            "js_accessibility_features": js_features,
            "total_features_checked": total_features,
            "implemented_features": implemented_features,
            "accessibility_score": round(accessibility_score, 1),
            "wcag_compliance_estimate": "AA" if accessibility_score >= 90 else "A" if accessibility_score >= 70 else "Partial"
        }
    
    def analyze_mobile_optimization(self) -> Dict:
        """Analyze mobile optimization features."""
        css_content = ""
        
        if self.css_file.exists():
            with open(self.css_file, 'r', encoding='utf-8') as f:
                css_content = f.read()
        
        mobile_features = {
            "mobile_first_design": "max-width: 768px" in css_content,
            "responsive_grid": "grid-template-columns: repeat(auto-fit" in css_content,
            "flexible_spacing": "--spacing-" in css_content,
            "touch_friendly_targets": "44px" in css_content or "2.75rem" in css_content,
            "viewport_optimization": "@media screen" in css_content,
            "flexible_typography": "clamp(" in css_content or "rem" in css_content
        }
        
        implemented_mobile = sum(mobile_features.values())
        total_mobile = len(mobile_features)
        mobile_score = (implemented_mobile / total_mobile) * 100
        
        return {
            "mobile_features": mobile_features,
            "implemented_features": implemented_mobile,
            "total_features": total_mobile,
            "mobile_optimization_score": round(mobile_score, 1),
            "mobile_grade": "Excellent" if mobile_score >= 90 else "Good" if mobile_score >= 70 else "Needs Improvement"
        }
    
    def generate_optimization_recommendations(self, analysis_results: Dict) -> List[str]:
        """Generate optimization recommendations based on analysis."""
        recommendations = []
        
        # CSS recommendations
        css_results = analysis_results.get("css_analysis", {})
        if css_results.get("original_size_kb", 0) > 50:
            recommendations.append("Consider splitting CSS into critical and non-critical parts")
        if css_results.get("complexity_score", 0) > 500:
            recommendations.append("CSS complexity is high - consider modularization")
        
        # JavaScript recommendations
        js_results = analysis_results.get("js_analysis", {})
        if js_results.get("original_size_kb", 0) > 30:
            recommendations.append("Consider lazy loading non-critical JavaScript features")
        if js_results.get("dom_queries", 0) > 20:
            recommendations.append("Cache DOM queries for better performance")
        
        # Accessibility recommendations
        a11y_results = analysis_results.get("accessibility_analysis", {})
        if a11y_results.get("accessibility_score", 0) < 90:
            recommendations.append("Implement additional accessibility features for WCAG AA compliance")
        
        # Mobile recommendations
        mobile_results = analysis_results.get("mobile_analysis", {})
        if mobile_results.get("mobile_optimization_score", 0) < 80:
            recommendations.append("Enhance mobile optimization with better touch targets and responsive design")
        
        if not recommendations:
            recommendations.append("Excellent performance! Continue monitoring and maintaining current optimizations")
        
        return recommendations
    
    def run_complete_analysis(self) -> Dict:
        """Run complete performance analysis."""
        print("🔍 Running Documentation Performance Analysis...")
        
        start_time = time.time()
        
        analysis_results = {
            "analysis_timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "css_analysis": self.analyze_css_performance(),
            "js_analysis": self.analyze_js_performance(),
            "accessibility_analysis": self.analyze_accessibility_features(),
            "mobile_analysis": self.analyze_mobile_optimization()
        }
        
        analysis_results["optimization_recommendations"] = self.generate_optimization_recommendations(analysis_results)
        
        analysis_time = time.time() - start_time
        analysis_results["analysis_duration_ms"] = round(analysis_time * 1000, 1)
        
        return analysis_results
    
    def _calculate_css_grade(self, file_size: int, complexity: float) -> str:
        """Calculate CSS performance grade."""
        if file_size < 30720 and complexity < 300:  # 30KB, low complexity
            return "A+"
        elif file_size < 51200 and complexity < 500:  # 50KB, medium complexity
            return "A"
        elif file_size < 102400 and complexity < 800:  # 100KB, high complexity
            return "B"
        else:
            return "C"
    
    def _calculate_js_grade(self, file_size: int, complexity: float) -> str:
        """Calculate JavaScript performance grade."""
        if file_size < 20480 and complexity < 200:  # 20KB, low complexity
            return "A+"
        elif file_size < 40960 and complexity < 400:  # 40KB, medium complexity
            return "A"
        elif file_size < 81920 and complexity < 600:  # 80KB, high complexity
            return "B"
        else:
            return "C"
    
    def save_analysis_report(self, results: Dict, output_file: str = None):
        """Save analysis results to a file."""
        if output_file is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            output_file = f"performance_analysis_{timestamp}.json"
        
        output_path = self.docs_root / output_file
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        
        print(f"📊 Analysis report saved to: {output_path}")
        return output_path
    
    def print_summary_report(self, results: Dict):
        """Print a formatted summary report."""
        print("\n" + "="*60)
        print("📈 DOCUMENTATION PERFORMANCE ANALYSIS SUMMARY")
        print("="*60)
        
        # CSS Analysis
        css = results.get("css_analysis", {})
        print(f"\n🎨 CSS Performance:")
        print(f"   File Size: {css.get('original_size_kb', 0)} KB (gzipped: {css.get('gzipped_size_kb', 0)} KB)")
        print(f"   Compression: {css.get('compression_ratio', 0)}%")
        print(f"   Performance Grade: {css.get('performance_grade', 'N/A')}")
        print(f"   Load Time Estimate: {css.get('estimated_load_time_ms', 0)} ms")
        
        # JavaScript Analysis
        js = results.get("js_analysis", {})
        print(f"\n⚡ JavaScript Performance:")
        print(f"   File Size: {js.get('original_size_kb', 0)} KB (gzipped: {js.get('gzipped_size_kb', 0)} KB)")
        print(f"   Compression: {js.get('compression_ratio', 0)}%")
        print(f"   Performance Grade: {js.get('performance_grade', 'N/A')}")
        print(f"   Load Time Estimate: {js.get('estimated_load_time_ms', 0)} ms")
        
        # Accessibility Analysis
        a11y = results.get("accessibility_analysis", {})
        print(f"\n♿ Accessibility Compliance:")
        print(f"   Score: {a11y.get('accessibility_score', 0)}%")
        print(f"   WCAG Compliance: {a11y.get('wcag_compliance_estimate', 'Unknown')}")
        print(f"   Features Implemented: {a11y.get('implemented_features', 0)}/{a11y.get('total_features_checked', 0)}")
        
        # Mobile Optimization
        mobile = results.get("mobile_analysis", {})
        print(f"\n📱 Mobile Optimization:")
        print(f"   Score: {mobile.get('mobile_optimization_score', 0)}%")
        print(f"   Grade: {mobile.get('mobile_grade', 'Unknown')}")
        
        # Recommendations
        recommendations = results.get("optimization_recommendations", [])
        print(f"\n💡 Optimization Recommendations:")
        for i, rec in enumerate(recommendations, 1):
            print(f"   {i}. {rec}")
        
        print(f"\nAnalysis completed in {results.get('analysis_duration_ms', 0)} ms")
        print("="*60)


def main():
    """Main function to run performance analysis."""
    # Get the documentation root directory (project root)
    current_dir = Path.cwd()
    
    # Initialize analyzer
    analyzer = DocumentationPerformanceAnalyzer(str(current_dir))
    
    # Run complete analysis
    try:
        results = analyzer.run_complete_analysis()
        
        # Print summary report
        analyzer.print_summary_report(results)
        
        # Save detailed report
        report_file = analyzer.save_analysis_report(results)
        
        print(f"\n✅ Performance analysis completed successfully!")
        print(f"📄 Detailed report available at: {report_file}")
        
    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())