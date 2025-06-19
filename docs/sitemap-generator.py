#!/usr/bin/env python3
"""
Dynamic Sitemap Generator for Locomotion Data Standardization
Created: 2025-06-19 with user permission
Purpose: Generate comprehensive XML sitemaps for optimal SEO

Features:
- Dynamic discovery of all documentation pages
- Priority and frequency optimization for different content types
- Image sitemap generation
- Multilingual support preparation
- Research-specific metadata inclusion
"""

import os
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
import mimetypes
import json
from typing import List, Dict, Optional
import hashlib


class SitemapGenerator:
    """Generate comprehensive sitemaps for documentation site."""
    
    def __init__(self, docs_root: str, base_url: str):
        self.docs_root = Path(docs_root)
        self.base_url = base_url.rstrip('/')
        self.current_time = datetime.now(timezone.utc).isoformat()
        
        # Content type priorities and frequencies
        self.content_config = {
            'homepage': {'priority': '1.0', 'changefreq': 'daily'},
            'getting_started': {'priority': '0.9', 'changefreq': 'weekly'},
            'tutorials': {'priority': '0.8', 'changefreq': 'weekly'},
            'api_reference': {'priority': '0.8', 'changefreq': 'weekly'},
            'examples': {'priority': '0.7', 'changefreq': 'weekly'},
            'datasets': {'priority': '0.7', 'changefreq': 'monthly'},
            'contributing': {'priority': '0.6', 'changefreq': 'monthly'},
            'documentation': {'priority': '0.6', 'changefreq': 'weekly'},
            'default': {'priority': '0.5', 'changefreq': 'monthly'}
        }
        
        # File extensions to include
        self.include_extensions = {'.html', '.md', '.pdf'}
        self.image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp'}
        
    def generate_all_sitemaps(self) -> Dict[str, str]:
        """Generate all sitemaps and return file paths."""
        results = {}
        
        # Generate main sitemap
        main_sitemap = self.generate_main_sitemap()
        main_path = self.docs_root / 'sitemap.xml'
        self.write_xml(main_sitemap, main_path)
        results['main'] = str(main_path)
        
        # Generate image sitemap
        image_sitemap = self.generate_image_sitemap()
        image_path = self.docs_root / 'sitemap-images.xml'
        self.write_xml(image_sitemap, image_path)
        results['images'] = str(image_path)
        
        # Generate sitemap index
        index_sitemap = self.generate_sitemap_index(results)
        index_path = self.docs_root / 'sitemap-index.xml'
        self.write_xml(index_sitemap, index_path)
        results['index'] = str(index_path)
        
        return results
    
    def generate_main_sitemap(self) -> ET.Element:
        """Generate the main sitemap with all pages."""
        urlset = ET.Element('urlset')
        urlset.set('xmlns', 'http://www.sitemaps.org/schemas/sitemap/0.9')
        urlset.set('xmlns:image', 'http://www.google.com/schemas/sitemap-image/1.1')
        urlset.set('xmlns:news', 'http://www.google.com/schemas/sitemap-news/0.9')
        
        # Discover all pages
        pages = self.discover_pages()
        
        for page in pages:
            url_elem = self.create_url_element(page)
            if url_elem is not None:
                urlset.append(url_elem)
        
        return urlset
    
    def generate_image_sitemap(self) -> ET.Element:
        """Generate sitemap specifically for images."""
        urlset = ET.Element('urlset')
        urlset.set('xmlns', 'http://www.sitemaps.org/schemas/sitemap/0.9')
        urlset.set('xmlns:image', 'http://www.google.com/schemas/sitemap-image/1.1')
        
        # Find all images
        images = self.discover_images()
        
        # Group images by their parent page
        image_groups = {}
        for image in images:
            parent_url = self.get_parent_page_url(image)
            if parent_url not in image_groups:
                image_groups[parent_url] = []
            image_groups[parent_url].append(image)
        
        # Create URL elements with image references
        for parent_url, page_images in image_groups.items():
            url_elem = ET.SubElement(urlset, 'url')
            
            loc_elem = ET.SubElement(url_elem, 'loc')
            loc_elem.text = parent_url
            
            lastmod_elem = ET.SubElement(url_elem, 'lastmod')
            lastmod_elem.text = self.current_time
            
            # Add each image
            for image in page_images:
                image_elem = ET.SubElement(url_elem, 'image:image')
                
                image_loc = ET.SubElement(image_elem, 'image:loc')
                image_loc.text = self.get_image_url(image)
                
                # Try to extract image metadata
                image_title = self.get_image_title(image)
                if image_title:
                    title_elem = ET.SubElement(image_elem, 'image:title')
                    title_elem.text = image_title
                
                image_caption = self.get_image_caption(image)
                if image_caption:
                    caption_elem = ET.SubElement(image_elem, 'image:caption')
                    caption_elem.text = image_caption
        
        return urlset
    
    def generate_sitemap_index(self, sitemap_files: Dict[str, str]) -> ET.Element:
        """Generate sitemap index file."""
        sitemapindex = ET.Element('sitemapindex')
        sitemapindex.set('xmlns', 'http://www.sitemaps.org/schemas/sitemap/0.9')
        
        for sitemap_type, file_path in sitemap_files.items():
            if sitemap_type == 'index':  # Don't include index in itself
                continue
                
            sitemap_elem = ET.SubElement(sitemapindex, 'sitemap')
            
            loc_elem = ET.SubElement(sitemap_elem, 'loc')
            filename = Path(file_path).name
            loc_elem.text = f"{self.base_url}/{filename}"
            
            lastmod_elem = ET.SubElement(sitemap_elem, 'lastmod')
            lastmod_elem.text = self.current_time
        
        return sitemapindex
    
    def discover_pages(self) -> List[Dict]:
        """Discover all documentation pages."""
        pages = []
        
        # Add homepage
        pages.append({
            'path': '/',
            'file_path': self.docs_root / 'index.md',
            'type': 'homepage',
            'title': 'Locomotion Data Standardization'
        })
        
        # Recursively find all markdown and HTML files
        for file_path in self.docs_root.rglob('*'):
            if file_path.is_file() and file_path.suffix in self.include_extensions:
                # Skip certain directories
                if self.should_skip_path(file_path):
                    continue
                
                relative_path = file_path.relative_to(self.docs_root)
                url_path = self.convert_to_url_path(relative_path)
                
                page_info = {
                    'path': url_path,
                    'file_path': file_path,
                    'type': self.classify_page_type(url_path),
                    'title': self.extract_page_title(file_path),
                    'last_modified': self.get_file_modified_time(file_path)
                }
                
                pages.append(page_info)
        
        return pages
    
    def discover_images(self) -> List[Path]:
        """Discover all images in the documentation."""
        images = []
        
        for file_path in self.docs_root.rglob('*'):
            if (file_path.is_file() and 
                file_path.suffix.lower() in self.image_extensions and
                not self.should_skip_path(file_path)):
                images.append(file_path)
        
        return images
    
    def create_url_element(self, page: Dict) -> Optional[ET.Element]:
        """Create URL element for a page."""
        if not page['path']:
            return None
        
        url_elem = ET.Element('url')
        
        # Location
        loc_elem = ET.SubElement(url_elem, 'loc')
        full_url = f"{self.base_url}{page['path']}"
        loc_elem.text = full_url
        
        # Last modified
        lastmod_elem = ET.SubElement(url_elem, 'lastmod')
        lastmod_elem.text = page.get('last_modified', self.current_time)
        
        # Change frequency and priority based on content type
        config = self.content_config.get(page['type'], self.content_config['default'])
        
        changefreq_elem = ET.SubElement(url_elem, 'changefreq')
        changefreq_elem.text = config['changefreq']
        
        priority_elem = ET.SubElement(url_elem, 'priority')
        priority_elem.text = config['priority']
        
        # Add any images on this page
        page_images = self.find_page_images(page['file_path'])
        for image in page_images:
            image_elem = ET.SubElement(url_elem, 'image:image')
            
            image_loc = ET.SubElement(image_elem, 'image:loc')
            image_loc.text = self.get_image_url(image)
            
            # Add image metadata if available
            image_title = self.get_image_title(image)
            if image_title:
                title_elem = ET.SubElement(image_elem, 'image:title')
                title_elem.text = image_title
        
        return url_elem
    
    def classify_page_type(self, url_path: str) -> str:
        """Classify page type based on URL path."""
        path_lower = url_path.lower()
        
        if url_path == '/':
            return 'homepage'
        elif '/getting_started/' in path_lower or '/getting-started/' in path_lower:
            return 'getting_started'
        elif '/tutorials/' in path_lower:
            return 'tutorials'
        elif '/api/' in path_lower or '/reference/' in path_lower:
            return 'api_reference'
        elif '/examples/' in path_lower:
            return 'examples'
        elif '/datasets/' in path_lower or '/data/' in path_lower:
            return 'datasets'
        elif '/contributing/' in path_lower or '/contribute/' in path_lower:
            return 'contributing'
        else:
            return 'documentation'
    
    def should_skip_path(self, file_path: Path) -> bool:
        """Check if path should be skipped."""
        skip_patterns = [
            '__pycache__',
            '.git',
            'node_modules',
            'venv',
            'conda_env',
            '.pytest_cache',
            'htmlcov',
            '.coverage',
            'build',
            'dist',
            '.tmp',
            '.temp',
            'draft',
            'private',
            '.DS_Store'
        ]
        
        path_str = str(file_path).lower()
        return any(pattern in path_str for pattern in skip_patterns)
    
    def convert_to_url_path(self, relative_path: Path) -> str:
        """Convert file path to URL path."""
        # Convert to POSIX path
        url_path = relative_path.as_posix()
        
        # Remove file extensions for certain files
        if url_path.endswith('.md'):
            url_path = url_path[:-3]
        elif url_path.endswith('/index.html'):
            url_path = url_path[:-11]
        elif url_path.endswith('.html'):
            url_path = url_path[:-5]
        
        # Ensure path starts with /
        if not url_path.startswith('/'):
            url_path = '/' + url_path
        
        # Handle index files
        if url_path.endswith('/index'):
            url_path = url_path[:-6]
        
        # Ensure directory paths end with /
        if not url_path.endswith('/') and not '.' in Path(url_path).name:
            url_path += '/'
        
        return url_path
    
    def extract_page_title(self, file_path: Path) -> str:
        """Extract title from page file."""
        try:
            if file_path.suffix == '.md':
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Look for YAML front matter title
                if content.startswith('---'):
                    end_marker = content.find('---', 3)
                    if end_marker != -1:
                        front_matter = content[3:end_marker]
                        for line in front_matter.split('\n'):
                            if line.strip().startswith('title:'):
                                return line.split(':', 1)[1].strip().strip('"\'')
                
                # Look for first heading
                for line in content.split('\n'):
                    line = line.strip()
                    if line.startswith('# '):
                        return line[2:].strip()
            
            elif file_path.suffix == '.html':
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Simple title extraction
                    start = content.find('<title>')
                    if start != -1:
                        end = content.find('</title>', start)
                        if end != -1:
                            return content[start+7:end].strip()
        
        except Exception:
            pass
        
        # Fallback to filename
        return file_path.stem.replace('_', ' ').replace('-', ' ').title()
    
    def get_file_modified_time(self, file_path: Path) -> str:
        """Get file modification time in ISO format."""
        try:
            mtime = file_path.stat().st_mtime
            dt = datetime.fromtimestamp(mtime, timezone.utc)
            return dt.isoformat()
        except Exception:
            return self.current_time
    
    def find_page_images(self, page_file: Path) -> List[Path]:
        """Find images referenced in a page."""
        images = []
        
        try:
            with open(page_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Simple image detection (could be enhanced with proper parsing)
            import re
            
            # Markdown images: ![alt](path)
            md_images = re.findall(r'!\[.*?\]\(([^)]+)\)', content)
            
            # HTML images: <img src="path">
            html_images = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', content)
            
            all_image_refs = md_images + html_images
            
            for img_ref in all_image_refs:
                # Convert to absolute path
                if img_ref.startswith('http'):
                    continue  # External image
                
                if img_ref.startswith('/'):
                    img_path = self.docs_root / img_ref[1:]
                else:
                    img_path = page_file.parent / img_ref
                
                if img_path.exists() and img_path.suffix.lower() in self.image_extensions:
                    images.append(img_path.resolve())
        
        except Exception:
            pass
        
        return images
    
    def get_parent_page_url(self, image_path: Path) -> str:
        """Get the URL of the page that contains this image."""
        # For now, assume images belong to their directory's index page
        parent_dir = image_path.parent
        relative_to_docs = parent_dir.relative_to(self.docs_root)
        url_path = '/' + relative_to_docs.as_posix()
        
        if not url_path.endswith('/'):
            url_path += '/'
        
        return f"{self.base_url}{url_path}"
    
    def get_image_url(self, image_path: Path) -> str:
        """Get the full URL for an image."""
        relative_path = image_path.relative_to(self.docs_root)
        return f"{self.base_url}/{relative_path.as_posix()}"
    
    def get_image_title(self, image_path: Path) -> str:
        """Get title for an image."""
        # Use filename as title, cleaned up
        title = image_path.stem.replace('_', ' ').replace('-', ' ')
        return title.title()
    
    def get_image_caption(self, image_path: Path) -> Optional[str]:
        """Get caption for an image if available."""
        # Could be enhanced to read from metadata or nearby text
        return None
    
    def write_xml(self, root: ET.Element, file_path: Path) -> None:
        """Write XML to file with proper formatting."""
        # Create XML declaration
        xml_str = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml_str += ET.tostring(root, encoding='unicode')
        
        # Pretty print (basic formatting)
        xml_str = self.format_xml(xml_str)
        
        # Write to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(xml_str)
    
    def format_xml(self, xml_str: str) -> str:
        """Basic XML formatting."""
        try:
            import xml.dom.minidom
            dom = xml.dom.minidom.parseString(xml_str)
            return dom.toprettyxml(indent='  ', encoding=None)
        except Exception:
            return xml_str


def main():
    """Main function to generate sitemaps."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate sitemaps for documentation site')
    parser.add_argument('--docs-root', default='.',
                       help='Root directory of documentation')
    parser.add_argument('--base-url', 
                       default='https://locomotion-data-standardization.readthedocs.io',
                       help='Base URL of the site')
    parser.add_argument('--output-dir', default=None,
                       help='Output directory for sitemaps (defaults to docs-root)')
    
    args = parser.parse_args()
    
    docs_root = Path(args.docs_root).resolve()
    output_dir = Path(args.output_dir).resolve() if args.output_dir else docs_root
    
    print(f"Generating sitemaps for {docs_root}")
    print(f"Base URL: {args.base_url}")
    print(f"Output directory: {output_dir}")
    
    generator = SitemapGenerator(str(docs_root), args.base_url)
    
    try:
        results = generator.generate_all_sitemaps()
        
        print("\n✅ Successfully generated sitemaps:")
        for sitemap_type, file_path in results.items():
            print(f"   {sitemap_type}: {file_path}")
        
        print(f"\n📊 Sitemap Statistics:")
        
        # Count URLs in main sitemap
        try:
            with open(results['main'], 'r') as f:
                content = f.read()
                url_count = content.count('<loc>')
                print(f"   Main sitemap: {url_count} URLs")
        except Exception as e:
            print(f"   Could not read main sitemap: {e}")
        
        # Count images in image sitemap
        try:
            with open(results['images'], 'r') as f:
                content = f.read()
                image_count = content.count('<image:image>')
                print(f"   Image sitemap: {image_count} images")
        except Exception as e:
            print(f"   Could not read image sitemap: {e}")
        
        print(f"\n🌐 URLs to submit to search engines:")
        print(f"   {args.base_url}/sitemap-index.xml")
        print(f"   {args.base_url}/sitemap.xml")
        print(f"   {args.base_url}/sitemap-images.xml")
        
    except Exception as e:
        print(f"❌ Error generating sitemaps: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())