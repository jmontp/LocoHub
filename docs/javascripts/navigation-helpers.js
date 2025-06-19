/**
 * Navigation Helpers
 * Provides enhanced navigation functionality and user experience improvements
 */

document.addEventListener('DOMContentLoaded', function() {
    
    // Initialize all navigation helpers
    initializeNavigationHelpers();
    
    function initializeNavigationHelpers() {
        // Add sticky navigation enhancements
        enhanceStickyNavigation();
        
        // Add smooth scrolling
        addSmoothScrolling();
        
        // Add copy code functionality
        addCopyCodeButtons();
        
        // Add table of contents enhancements
        enhanceTableOfContents();
        
        // Add search enhancements
        enhanceSearch();
        
        // Add mobile navigation improvements
        improveMobileNavigation();
        
        // Add external link indicators
        addExternalLinkIndicators();
        
        // Add reading progress indicator
        addReadingProgress();
    }

    /**
     * Enhance sticky navigation behavior
     */
    function enhanceStickyNavigation() {
        let lastScrollTop = 0;
        const header = document.querySelector('.md-header');
        
        if (!header) return;
        
        window.addEventListener('scroll', function() {
            const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
            
            // Hide/show header based on scroll direction
            if (scrollTop > lastScrollTop && scrollTop > 100) {
                // Scrolling down
                header.style.transform = 'translateY(-100%)';
            } else {
                // Scrolling up
                header.style.transform = 'translateY(0)';
            }
            
            lastScrollTop = scrollTop;
        });
    }

    /**
     * Add smooth scrolling for anchor links
     */
    function addSmoothScrolling() {
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function(e) {
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });
    }

    /**
     * Add copy code functionality to code blocks
     */
    function addCopyCodeButtons() {
        document.querySelectorAll('pre code').forEach(function(codeBlock) {
            // Skip if button already exists
            if (codeBlock.parentNode.querySelector('.copy-button')) return;
            
            const button = document.createElement('button');
            button.className = 'copy-button';
            button.innerHTML = '<i class="material-icons">content_copy</i>';
            button.setAttribute('title', 'Copy code');
            
            button.addEventListener('click', function() {
                navigator.clipboard.writeText(codeBlock.textContent).then(function() {
                    button.innerHTML = '<i class="material-icons">check</i>';
                    button.style.color = '#22c55e';
                    
                    setTimeout(function() {
                        button.innerHTML = '<i class="material-icons">content_copy</i>';
                        button.style.color = '';
                    }, 2000);
                });
            });
            
            codeBlock.parentNode.style.position = 'relative';
            codeBlock.parentNode.appendChild(button);
        });
    }

    /**
     * Enhance table of contents functionality
     */
    function enhanceTableOfContents() {
        const toc = document.querySelector('.md-nav--secondary');
        if (!toc) return;
        
        // Add scroll spy functionality
        const headings = document.querySelectorAll('h1, h2, h3, h4, h5, h6');
        const tocLinks = toc.querySelectorAll('a');
        
        if (headings.length === 0 || tocLinks.length === 0) return;
        
        function updateActiveTocLink() {
            let activeHeading = null;
            
            headings.forEach(heading => {
                const rect = heading.getBoundingClientRect();
                if (rect.top <= 100 && rect.bottom >= 0) {
                    activeHeading = heading;
                }
            });
            
            // Remove active class from all links
            tocLinks.forEach(link => link.classList.remove('active'));
            
            // Add active class to current link
            if (activeHeading) {
                const activeLink = toc.querySelector(`a[href="#${activeHeading.id}"]`);
                if (activeLink) {
                    activeLink.classList.add('active');
                }
            }
        }
        
        // Add scroll listener for TOC updates
        window.addEventListener('scroll', updateActiveTocLink);
        updateActiveTocLink(); // Initial call
    }

    /**
     * Enhance search functionality
     */
    function enhanceSearch() {
        const searchInput = document.querySelector('.md-search__input');
        if (!searchInput) return;
        
        // Add search shortcuts
        document.addEventListener('keydown', function(e) {
            // Ctrl/Cmd + K to focus search
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                searchInput.focus();
            }
            
            // Escape to blur search
            if (e.key === 'Escape' && document.activeElement === searchInput) {
                searchInput.blur();
            }
        });
        
        // Add search placeholder enhancement
        searchInput.setAttribute('placeholder', 'Search documentation... (Ctrl+K)');
    }

    /**
     * Improve mobile navigation
     */
    function improveMobileNavigation() {
        const nav = document.querySelector('.md-nav--primary');
        if (!nav) return;
        
        // Add touch gestures for mobile nav
        let startX = 0;
        let startY = 0;
        
        document.addEventListener('touchstart', function(e) {
            startX = e.touches[0].clientX;
            startY = e.touches[0].clientY;
        });
        
        document.addEventListener('touchend', function(e) {
            const endX = e.changedTouches[0].clientX;
            const endY = e.changedTouches[0].clientY;
            
            const deltaX = endX - startX;
            const deltaY = endY - startY;
            
            // Swipe right to open navigation (when at left edge)
            if (deltaX > 50 && Math.abs(deltaY) < 50 && startX < 50) {
                const navToggle = document.querySelector('.md-nav__button');
                if (navToggle) navToggle.click();
            }
        });
    }

    /**
     * Add external link indicators
     */
    function addExternalLinkIndicators() {
        const domain = window.location.hostname;
        
        document.querySelectorAll('a[href^="http"]').forEach(link => {
            const linkDomain = new URL(link.href).hostname;
            
            if (linkDomain !== domain) {
                // Add external link icon
                const icon = document.createElement('i');
                icon.className = 'material-icons external-link-icon';
                icon.textContent = 'open_in_new';
                icon.setAttribute('title', 'External link');
                
                link.appendChild(icon);
                link.setAttribute('target', '_blank');
                link.setAttribute('rel', 'noopener noreferrer');
            }
        });
    }

    /**
     * Add reading progress indicator
     */
    function addReadingProgress() {
        // Only add on content pages, not landing pages
        const article = document.querySelector('article');
        if (!article || document.body.classList.contains('md-typeset--homepage')) return;
        
        const progressBar = document.createElement('div');
        progressBar.className = 'reading-progress';
        progressBar.innerHTML = '<div class="reading-progress-bar"></div>';
        
        document.body.appendChild(progressBar);
        
        const progressBarFill = progressBar.querySelector('.reading-progress-bar');
        
        function updateReadingProgress() {
            const winScroll = document.body.scrollTop || document.documentElement.scrollTop;
            const height = document.documentElement.scrollHeight - document.documentElement.clientHeight;
            const scrolled = (winScroll / height) * 100;
            
            progressBarFill.style.width = scrolled + '%';
        }
        
        window.addEventListener('scroll', updateReadingProgress);
    }

    /**
     * Add back-to-top button
     */
    function addBackToTop() {
        const backToTop = document.createElement('button');
        backToTop.className = 'back-to-top';
        backToTop.innerHTML = '<i class="material-icons">keyboard_arrow_up</i>';
        backToTop.setAttribute('title', 'Back to top');
        
        document.body.appendChild(backToTop);
        
        backToTop.addEventListener('click', function() {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });
        
        // Show/hide based on scroll position
        window.addEventListener('scroll', function() {
            if (window.pageYOffset > 300) {
                backToTop.classList.add('visible');
            } else {
                backToTop.classList.remove('visible');
            }
        });
    }

    // Add back to top button
    addBackToTop();

    /**
     * Add enhanced tab functionality
     */
    function enhanceTabbed() {
        document.querySelectorAll('.tabbed-set').forEach(tabbedSet => {
            const tabs = tabbedSet.querySelectorAll('.tabbed-labels label');
            const contents = tabbedSet.querySelectorAll('.tabbed-content');
            
            tabs.forEach((tab, index) => {
                tab.addEventListener('click', function() {
                    // Store active tab preference
                    const tabText = tab.textContent.trim();
                    localStorage.setItem('preferred-tab', tabText);
                    
                    // Sync across all tab sets with same labels
                    document.querySelectorAll('.tabbed-set').forEach(otherSet => {
                        const matchingTab = Array.from(otherSet.querySelectorAll('.tabbed-labels label'))
                            .find(otherTab => otherTab.textContent.trim() === tabText);
                        
                        if (matchingTab) {
                            matchingTab.click();
                        }
                    });
                });
            });
        });
        
        // Restore preferred tab on page load
        const preferredTab = localStorage.getItem('preferred-tab');
        if (preferredTab) {
            document.querySelectorAll('.tabbed-labels label').forEach(tab => {
                if (tab.textContent.trim() === preferredTab) {
                    tab.click();
                }
            });
        }
    }

    // Enhance tabbed functionality
    enhanceTabbed();

    /**
     * Add print styles optimization
     */
    function optimizePrintStyles() {
        const printStyle = document.createElement('style');
        printStyle.media = 'print';
        printStyle.textContent = `
            .md-header, .md-tabs, .md-sidebar, .copy-button, 
            .back-to-top, .reading-progress, .navigation-suggestions,
            .next-steps, .related-content, .tutorial-progress {
                display: none !important;
            }
            
            .md-content {
                margin: 0 !important;
            }
            
            .md-typeset {
                font-size: 12pt;
                line-height: 1.4;
            }
            
            .md-typeset h1, .md-typeset h2, .md-typeset h3 {
                page-break-after: avoid;
            }
            
            .md-typeset pre {
                page-break-inside: avoid;
            }
        `;
        document.head.appendChild(printStyle);
    }

    // Optimize print styles
    optimizePrintStyles();
});

// Add CSS for new navigation elements
const navStyle = document.createElement('style');
navStyle.textContent = `
    .copy-button {
        position: absolute;
        top: 8px;
        right: 8px;
        background: rgba(255, 255, 255, 0.9);
        border: 1px solid #d1d5db;
        border-radius: 4px;
        padding: 4px 8px;
        cursor: pointer;
        font-size: 0.8rem;
        transition: all 0.2s ease;
        z-index: 1;
    }
    
    .copy-button:hover {
        background: #f3f4f6;
        transform: scale(1.05);
    }
    
    .external-link-icon {
        font-size: 0.8rem !important;
        margin-left: 0.25rem;
        opacity: 0.6;
        vertical-align: super;
    }
    
    .reading-progress {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 3px;
        background: rgba(0, 0, 0, 0.1);
        z-index: 1000;
    }
    
    .reading-progress-bar {
        height: 100%;
        background: #3b82f6;
        width: 0%;
        transition: width 0.1s ease;
    }
    
    .back-to-top {
        position: fixed;
        bottom: 20px;
        right: 20px;
        width: 48px;
        height: 48px;
        background: #3b82f6;
        color: white;
        border: none;
        border-radius: 50%;
        cursor: pointer;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        transition: all 0.3s ease;
        opacity: 0;
        visibility: hidden;
        z-index: 1000;
    }
    
    .back-to-top.visible {
        opacity: 1;
        visibility: visible;
    }
    
    .back-to-top:hover {
        background: #2563eb;
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.4);
    }
    
    .md-nav--secondary a.active {
        color: #3b82f6;
        font-weight: 600;
        border-left: 3px solid #3b82f6;
        padding-left: 0.75rem;
        background: rgba(59, 130, 246, 0.1);
    }
    
    .md-header {
        transition: transform 0.3s ease;
    }
    
    /* Mobile improvements */
    @media (max-width: 768px) {
        .copy-button {
            top: 4px;
            right: 4px;
            padding: 2px 4px;
            font-size: 0.7rem;
        }
        
        .back-to-top {
            bottom: 15px;
            right: 15px;
            width: 40px;
            height: 40px;
        }
        
        .external-link-icon {
            font-size: 0.7rem !important;
        }
    }
    
    /* Print optimizations */
    @media print {
        .copy-button, .back-to-top, .reading-progress,
        .external-link-icon {
            display: none !important;
        }
    }
    
    /* Dark mode support */
    [data-md-color-scheme="slate"] .copy-button {
        background: rgba(30, 41, 59, 0.9);
        border-color: #475569;
        color: #e2e8f0;
    }
    
    [data-md-color-scheme="slate"] .copy-button:hover {
        background: #475569;
    }
    
    [data-md-color-scheme="slate"] .reading-progress {
        background: rgba(255, 255, 255, 0.1);
    }
    
    /* Keyboard navigation indicators */
    .md-nav__link:focus,
    .md-tabs__link:focus,
    button:focus {
        outline: 2px solid #3b82f6;
        outline-offset: 2px;
    }
    
    /* Loading states */
    .md-search__input:focus {
        box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
    }
    
    /* Accessibility improvements */
    .sr-only {
        position: absolute;
        width: 1px;
        height: 1px;
        padding: 0;
        margin: -1px;
        overflow: hidden;
        clip: rect(0, 0, 0, 0);
        white-space: nowrap;
        border: 0;
    }
`;
document.head.appendChild(navStyle);