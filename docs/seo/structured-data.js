/*
SEO Structured Data Implementation
Created: 2025-06-19 with user permission
Purpose: Advanced SEO optimization with structured data for biomechanics research

Features:
- Schema.org markup for scientific documentation
- Open Graph and Twitter Card meta tags
- Dynamic meta tag generation
- Research publication structured data
- Dataset schema markup
- Software application markup
*/

class SEOStructuredData {
    constructor() {
        this.baseUrl = window.location.origin;
        this.siteName = 'Locomotion Data Standardization';
        this.siteDescription = 'Transform biomechanical datasets into unified, quality-assured formats for reproducible research';
        this.organizationSchema = this.createOrganizationSchema();
        
        this.init();
    }

    init() {
        this.addBasicMetaTags();
        this.addStructuredData();
        this.addOpenGraphTags();
        this.addTwitterCardTags();
        this.addResearchSpecificTags();
        this.trackPageView();
    }

    // Create Organization Schema for the research project
    createOrganizationSchema() {
        return {
            "@context": "https://schema.org",
            "@type": "ResearchProject",
            "name": this.siteName,
            "description": this.siteDescription,
            "url": this.baseUrl,
            "sameAs": [
                "https://github.com/your-org/locomotion-data-standardization"
            ],
            "keywords": [
                "biomechanics",
                "gait analysis",
                "motion capture",
                "data standardization",
                "locomotion research",
                "scientific computing",
                "machine learning",
                "prosthetics research",
                "rehabilitation engineering"
            ],
            "about": {
                "@type": "Thing",
                "name": "Biomechanical Data Analysis",
                "description": "Standardization of biomechanical datasets for scientific research"
            },
            "applicationCategory": "Scientific Software",
            "operatingSystem": "Cross-platform",
            "programmingLanguage": ["Python", "MATLAB"],
            "targetAudience": {
                "@type": "Audience",
                "audienceType": ["Researchers", "Engineers", "Clinicians", "Data Scientists"]
            }
        };
    }

    // Add basic meta tags for SEO
    addBasicMetaTags() {
        const currentUrl = window.location.href;
        const pageTitle = document.title || this.siteName;
        const pageDescription = this.getPageDescription();
        
        this.setMetaTag('description', pageDescription);
        this.setMetaTag('robots', 'index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1');
        this.setMetaTag('googlebot', 'index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1');
        this.setMetaTag('bingbot', 'index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1');
        
        // Canonical URL
        this.setLinkTag('canonical', currentUrl);
        
        // Language and locale
        this.setMetaTag('language', 'en-US');
        document.documentElement.lang = 'en';
        
        // Viewport (ensure it's optimized)
        this.setMetaTag('viewport', 'width=device-width, initial-scale=1.0, viewport-fit=cover');
        
        // Theme color for mobile browsers
        this.setMetaTag('theme-color', '#1e40af');
        this.setMetaTag('msapplication-TileColor', '#1e40af');
    }

    // Add comprehensive structured data
    addStructuredData() {
        const pageType = this.getPageType();
        let structuredData = [];

        // Always include organization schema
        structuredData.push(this.organizationSchema);

        // Add page-specific schema
        switch (pageType) {
            case 'documentation':
                structuredData.push(this.createDocumentationSchema());
                break;
            case 'tutorial':
                structuredData.push(this.createTutorialSchema());
                break;
            case 'api':
                structuredData.push(this.createAPISchema());
                break;
            case 'dataset':
                structuredData.push(this.createDatasetSchema());
                break;
            case 'home':
                structuredData.push(this.createWebsiteSchema());
                break;
            default:
                structuredData.push(this.createWebPageSchema());
        }

        // Add breadcrumb schema if applicable
        const breadcrumbSchema = this.createBreadcrumbSchema();
        if (breadcrumbSchema) {
            structuredData.push(breadcrumbSchema);
        }

        // Insert structured data
        this.insertJSONLD(structuredData);
    }

    // Create documentation-specific schema
    createDocumentationSchema() {
        return {
            "@context": "https://schema.org",
            "@type": "TechArticle",
            "headline": document.title,
            "description": this.getPageDescription(),
            "url": window.location.href,
            "datePublished": this.getPublishedDate(),
            "dateModified": this.getModifiedDate(),
            "author": {
                "@type": "Organization",
                "name": "Locomotion Data Standardization Project"
            },
            "publisher": {
                "@type": "Organization",
                "name": this.siteName,
                "url": this.baseUrl
            },
            "mainEntityOfPage": {
                "@type": "WebPage",
                "@id": window.location.href
            },
            "about": {
                "@type": "Thing",
                "name": "Scientific Software Documentation",
                "description": "Technical documentation for biomechanical data analysis tools"
            },
            "audience": {
                "@type": "Audience",
                "audienceType": "Researchers and Engineers"
            },
            "educationalLevel": "Advanced",
            "proficiencyRequired": "Expert"
        };
    }

    // Create tutorial-specific schema
    createTutorialSchema() {
        return {
            "@context": "https://schema.org",
            "@type": "HowTo",
            "name": document.title,
            "description": this.getPageDescription(),
            "url": window.location.href,
            "datePublished": this.getPublishedDate(),
            "dateModified": this.getModifiedDate(),
            "author": {
                "@type": "Organization",
                "name": "Locomotion Data Standardization Project"
            },
            "publisher": {
                "@type": "Organization",
                "name": this.siteName
            },
            "about": {
                "@type": "Thing",
                "name": "Biomechanical Data Analysis",
                "description": "Step-by-step guide for scientific data processing"
            },
            "audience": {
                "@type": "Audience",
                "audienceType": "Researchers"
            },
            "educationalLevel": "Intermediate",
            "step": this.extractTutorialSteps()
        };
    }

    // Create API documentation schema
    createAPISchema() {
        return {
            "@context": "https://schema.org",
            "@type": "APIReference",
            "name": document.title,
            "description": this.getPageDescription(),
            "url": window.location.href,
            "programmingLanguage": ["Python", "MATLAB"],
            "applicationCategory": "Scientific Software",
            "operatingSystem": "Cross-platform",
            "about": {
                "@type": "Thing",
                "name": "Biomechanical Data Processing API",
                "description": "Programming interface for scientific data analysis"
            }
        };
    }

    // Create dataset schema
    createDatasetSchema() {
        return {
            "@context": "https://schema.org",
            "@type": "Dataset",
            "name": document.title,
            "description": this.getPageDescription(),
            "url": window.location.href,
            "creator": {
                "@type": "Organization",
                "name": "Locomotion Data Standardization Project"
            },
            "publisher": {
                "@type": "Organization",
                "name": this.siteName
            },
            "keywords": [
                "biomechanics data",
                "gait analysis",
                "motion capture",
                "locomotion research",
                "scientific dataset"
            ],
            "license": "https://opensource.org/licenses/MIT",
            "distribution": {
                "@type": "DataDownload",
                "encodingFormat": "application/parquet",
                "contentUrl": window.location.href
            },
            "variableMeasured": [
                "joint angles",
                "joint moments",
                "ground reaction forces",
                "temporal parameters"
            ],
            "measurementTechnique": "Motion capture analysis",
            "spatialCoverage": "Human locomotion",
            "temporalCoverage": "Gait cycles"
        };
    }

    // Create website schema for homepage
    createWebsiteSchema() {
        return {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": this.siteName,
            "description": this.siteDescription,
            "url": this.baseUrl,
            "potentialAction": {
                "@type": "SearchAction",
                "target": {
                    "@type": "EntryPoint",
                    "urlTemplate": `${this.baseUrl}/search/?q={search_term_string}`
                },
                "query-input": "required name=search_term_string"
            },
            "about": {
                "@type": "Thing",
                "name": "Scientific Research Tools",
                "description": "Open source tools for biomechanical data standardization"
            }
        };
    }

    // Create general webpage schema
    createWebPageSchema() {
        return {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "name": document.title,
            "description": this.getPageDescription(),
            "url": window.location.href,
            "isPartOf": {
                "@type": "WebSite",
                "name": this.siteName,
                "url": this.baseUrl
            },
            "about": {
                "@type": "Thing",
                "name": "Scientific Documentation",
                "description": "Research tools and documentation"
            }
        };
    }

    // Create breadcrumb schema
    createBreadcrumbSchema() {
        const breadcrumbs = this.extractBreadcrumbs();
        if (!breadcrumbs.length) return null;

        return {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": breadcrumbs.map((crumb, index) => ({
                "@type": "ListItem",
                "position": index + 1,
                "name": crumb.name,
                "item": crumb.url
            }))
        };
    }

    // Add Open Graph tags
    addOpenGraphTags() {
        const pageTitle = document.title || this.siteName;
        const pageDescription = this.getPageDescription();
        const currentUrl = window.location.href;
        const imageUrl = this.getPageImage();

        this.setMetaProperty('og:type', this.getOGType());
        this.setMetaProperty('og:site_name', this.siteName);
        this.setMetaProperty('og:title', pageTitle);
        this.setMetaProperty('og:description', pageDescription);
        this.setMetaProperty('og:url', currentUrl);
        this.setMetaProperty('og:image', imageUrl);
        this.setMetaProperty('og:image:alt', `${pageTitle} - ${this.siteName}`);
        this.setMetaProperty('og:image:width', '1200');
        this.setMetaProperty('og:image:height', '630');
        this.setMetaProperty('og:locale', 'en_US');
        
        // Article-specific tags
        if (this.getPageType() === 'documentation' || this.getPageType() === 'tutorial') {
            this.setMetaProperty('article:published_time', this.getPublishedDate());
            this.setMetaProperty('article:modified_time', this.getModifiedDate());
            this.setMetaProperty('article:author', 'Locomotion Data Standardization Project');
            this.setMetaProperty('article:section', 'Scientific Documentation');
            this.setMetaProperty('article:tag', 'biomechanics,research,data-analysis');
        }
    }

    // Add Twitter Card tags
    addTwitterCardTags() {
        const pageTitle = document.title || this.siteName;
        const pageDescription = this.getPageDescription();
        const imageUrl = this.getPageImage();

        this.setMetaName('twitter:card', 'summary_large_image');
        this.setMetaName('twitter:site', '@locomotion_data'); // Update with actual Twitter handle
        this.setMetaName('twitter:creator', '@locomotion_data');
        this.setMetaName('twitter:title', pageTitle);
        this.setMetaName('twitter:description', pageDescription);
        this.setMetaName('twitter:image', imageUrl);
        this.setMetaName('twitter:image:alt', `${pageTitle} - Scientific Documentation`);
    }

    // Add research-specific meta tags
    addResearchSpecificTags() {
        // Dublin Core for academic indexing
        this.setMetaName('DC.title', document.title);
        this.setMetaName('DC.creator', 'Locomotion Data Standardization Project');
        this.setMetaName('DC.subject', 'biomechanics,gait analysis,motion capture,data standardization');
        this.setMetaName('DC.description', this.getPageDescription());
        this.setMetaName('DC.publisher', this.siteName);
        this.setMetaName('DC.date', this.getPublishedDate());
        this.setMetaName('DC.type', 'Text.Documentation');
        this.setMetaName('DC.format', 'text/html');
        this.setMetaName('DC.language', 'en');
        this.setMetaName('DC.rights', 'MIT License');

        // Citation metadata
        this.setMetaName('citation_title', document.title);
        this.setMetaName('citation_author', 'Locomotion Data Standardization Project');
        this.setMetaName('citation_publication_date', this.getPublishedDate());
        this.setMetaName('citation_technical_report_institution', 'Open Source Community');
        this.setMetaName('citation_pdf_url', this.getPDFUrl());

        // Research-specific keywords
        this.setMetaName('keywords', this.getResearchKeywords().join(', '));
    }

    // Utility methods
    getPageType() {
        const path = window.location.pathname;
        if (path === '/') return 'home';
        if (path.includes('/tutorials/')) return 'tutorial';
        if (path.includes('/api/') || path.includes('/reference/')) return 'api';
        if (path.includes('/datasets/')) return 'dataset';
        return 'documentation';
    }

    getPageDescription() {
        // Try to get description from existing meta tag
        const existingDesc = document.querySelector('meta[name="description"]');
        if (existingDesc) return existingDesc.content;

        // Extract from first paragraph
        const firstParagraph = document.querySelector('.md-content p');
        if (firstParagraph) {
            const text = firstParagraph.textContent.trim();
            return text.length > 160 ? text.substring(0, 157) + '...' : text;
        }

        return this.siteDescription;
    }

    getPageImage() {
        // Try to find a suitable image on the page
        const images = document.querySelectorAll('.md-content img');
        if (images.length > 0) {
            const img = images[0];
            return new URL(img.src, this.baseUrl).href;
        }

        // Fallback to default social image
        return `${this.baseUrl}/assets/images/social-preview.png`;
    }

    getOGType() {
        const pageType = this.getPageType();
        return pageType === 'home' ? 'website' : 'article';
    }

    getPublishedDate() {
        // Try to extract from page metadata or use current date
        const metaDate = document.querySelector('meta[name="date"]');
        if (metaDate) return metaDate.content;
        
        // Fallback to last modified time from document
        return new Date().toISOString();
    }

    getModifiedDate() {
        // Try to get last modified from server headers or use current time
        return new Date().toISOString();
    }

    getPDFUrl() {
        // Generate PDF URL for academic citation
        return `${this.baseUrl}/pdf${window.location.pathname}`;
    }

    getResearchKeywords() {
        return [
            'biomechanics',
            'gait analysis',
            'motion capture',
            'locomotion research',
            'data standardization',
            'scientific computing',
            'machine learning',
            'prosthetics',
            'rehabilitation engineering',
            'human movement',
            'kinematic analysis',
            'kinetic analysis',
            'clinical research',
            'sports science'
        ];
    }

    extractBreadcrumbs() {
        const breadcrumbContainer = document.querySelector('.breadcrumb, .md-nav__list');
        if (!breadcrumbContainer) return [];

        const breadcrumbs = [];
        const links = breadcrumbContainer.querySelectorAll('a');
        
        links.forEach(link => {
            breadcrumbs.push({
                name: link.textContent.trim(),
                url: new URL(link.href, this.baseUrl).href
            });
        });

        return breadcrumbs;
    }

    extractTutorialSteps() {
        const steps = [];
        const headings = document.querySelectorAll('.md-content h2, .md-content h3');
        
        headings.forEach((heading, index) => {
            const stepContent = this.getContentBetweenHeadings(heading);
            steps.push({
                "@type": "HowToStep",
                "position": index + 1,
                "name": heading.textContent.trim(),
                "text": stepContent
            });
        });

        return steps;
    }

    getContentBetweenHeadings(heading) {
        let content = '';
        let element = heading.nextElementSibling;
        
        while (element && !['H1', 'H2', 'H3'].includes(element.tagName)) {
            if (element.tagName === 'P') {
                content += element.textContent.trim() + ' ';
            }
            element = element.nextElementSibling;
        }
        
        return content.trim();
    }

    // Helper methods for meta tag manipulation
    setMetaTag(name, content) {
        this.setMetaAttribute('name', name, content);
    }

    setMetaProperty(property, content) {
        this.setMetaAttribute('property', property, content);
    }

    setMetaName(name, content) {
        this.setMetaAttribute('name', name, content);
    }

    setMetaAttribute(attribute, value, content) {
        let meta = document.querySelector(`meta[${attribute}="${value}"]`);
        if (!meta) {
            meta = document.createElement('meta');
            meta.setAttribute(attribute, value);
            document.head.appendChild(meta);
        }
        meta.content = content;
    }

    setLinkTag(rel, href) {
        let link = document.querySelector(`link[rel="${rel}"]`);
        if (!link) {
            link = document.createElement('link');
            link.rel = rel;
            document.head.appendChild(link);
        }
        link.href = href;
    }

    insertJSONLD(data) {
        // Remove existing structured data
        const existing = document.querySelectorAll('script[type="application/ld+json"]');
        existing.forEach(script => {
            if (script.dataset.generated === 'true') {
                script.remove();
            }
        });

        // Insert new structured data
        data.forEach(schema => {
            const script = document.createElement('script');
            script.type = 'application/ld+json';
            script.dataset.generated = 'true';
            script.textContent = JSON.stringify(schema, null, 2);
            document.head.appendChild(script);
        });
    }

    // Track page view for analytics
    trackPageView() {
        if (typeof gtag !== 'undefined') {
            gtag('config', 'GA_MEASUREMENT_ID', {
                page_title: document.title,
                page_location: window.location.href,
                content_group1: this.getPageType(),
                custom_map: {
                    'custom_parameter_1': 'research_category'
                }
            });
        }
    }
}

// Initialize SEO structured data when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        new SEOStructuredData();
    });
} else {
    new SEOStructuredData();
}

// Re-initialize when navigating between pages (for SPA behavior)
if ('navigation' in window) {
    navigation.addEventListener('navigate', () => {
        setTimeout(() => new SEOStructuredData(), 100);
    });
}

// Export for external use
window.SEOStructuredData = SEOStructuredData;