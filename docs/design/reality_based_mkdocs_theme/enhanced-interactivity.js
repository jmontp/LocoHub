/*
Locomotion Data Standardization - Enhanced Documentation Interactivity
Created: 2025-06-19 with user permission
Purpose: Interactive features for professional scientific documentation

Features:
- Code copy functionality with accessibility
- Collapsible content sections
- Enhanced search and highlighting
- Keyboard navigation improvements
- Screen reader optimizations
- Performance monitoring
- Citation management
*/

(function() {
    'use strict';

    // Performance monitoring
    const performanceMetrics = {
        startTime: performance.now(),
        interactions: 0,
        searchQueries: 0
    };

    // Accessibility utilities
    const a11y = {
        announce: function(message) {
            const liveRegion = document.querySelector('.aria-live-polite') || this.createLiveRegion();
            liveRegion.textContent = message;
            setTimeout(() => liveRegion.textContent = '', 1000);
        },

        createLiveRegion: function() {
            const region = document.createElement('div');
            region.className = 'aria-live-polite';
            region.setAttribute('aria-live', 'polite');
            region.setAttribute('aria-atomic', 'true');
            document.body.appendChild(region);
            return region;
        },

        trapFocus: function(element) {
            const focusableElements = element.querySelectorAll(
                'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
            );
            const firstElement = focusableElements[0];
            const lastElement = focusableElements[focusableElements.length - 1];

            element.addEventListener('keydown', function(e) {
                if (e.key === 'Tab') {
                    if (e.shiftKey) {
                        if (document.activeElement === firstElement) {
                            lastElement.focus();
                            e.preventDefault();
                        }
                    } else {
                        if (document.activeElement === lastElement) {
                            firstElement.focus();
                            e.preventDefault();
                        }
                    }
                }
            });
        }
    };

    // Code copy functionality
    const codeCopy = {
        init: function() {
            this.addCopyButtons();
            this.setupKeyboardShortcuts();
        },

        addCopyButtons: function() {
            const codeBlocks = document.querySelectorAll('pre code, .highlight pre');
            
            codeBlocks.forEach(block => {
                const container = block.closest('.code-example') || block.closest('.highlight') || block.parentElement;
                if (container && !container.querySelector('.code-copy-btn')) {
                    this.createCopyButton(container, block);
                }
            });
        },

        createCopyButton: function(container, codeBlock) {
            const button = document.createElement('button');
            button.className = 'code-copy-btn';
            button.textContent = 'Copy';
            button.setAttribute('aria-label', 'Copy code to clipboard');
            button.setAttribute('data-tooltip', 'Copy to clipboard');

            // Position button appropriately
            if (container.classList.contains('code-example')) {
                const header = container.querySelector('.code-header .code-actions');
                if (header) {
                    header.appendChild(button);
                }
            } else {
                container.style.position = 'relative';
                button.style.position = 'absolute';
                button.style.top = '8px';
                button.style.right = '8px';
                container.appendChild(button);
            }

            button.addEventListener('click', () => this.copyCode(button, codeBlock));
        },

        copyCode: function(button, codeBlock) {
            const code = codeBlock.textContent || codeBlock.innerText;
            
            navigator.clipboard.writeText(code).then(() => {
                this.showCopySuccess(button);
                a11y.announce('Code copied to clipboard');
                performanceMetrics.interactions++;
            }).catch(() => {
                // Fallback for older browsers
                this.fallbackCopy(code, button);
            });
        },

        fallbackCopy: function(text, button) {
            const textArea = document.createElement('textarea');
            textArea.value = text;
            textArea.style.position = 'fixed';
            textArea.style.opacity = '0';
            document.body.appendChild(textArea);
            textArea.select();
            
            try {
                document.execCommand('copy');
                this.showCopySuccess(button);
                a11y.announce('Code copied to clipboard');
            } catch (err) {
                a11y.announce('Copy failed. Please select and copy manually.');
            }
            
            document.body.removeChild(textArea);
        },

        showCopySuccess: function(button) {
            const originalText = button.textContent;
            button.textContent = 'Copied!';
            button.classList.add('copy-success');
            
            setTimeout(() => {
                button.textContent = originalText;
                button.classList.remove('copy-success');
            }, 2000);
        },

        setupKeyboardShortcuts: function() {
            document.addEventListener('keydown', (e) => {
                // Ctrl/Cmd + Shift + C to copy focused code block
                if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'C') {
                    const activeElement = document.activeElement;
                    const codeBlock = activeElement.closest('pre, .highlight');
                    
                    if (codeBlock) {
                        const copyBtn = codeBlock.querySelector('.code-copy-btn');
                        if (copyBtn) {
                            copyBtn.click();
                            e.preventDefault();
                        }
                    }
                }
            });
        }
    };

    // Collapsible content functionality
    const collapsible = {
        init: function() {
            this.createCollapsibleSections();
            this.setupKeyboardControls();
        },

        createCollapsibleSections: function() {
            // Look for sections marked as collapsible
            const collapsibleSections = document.querySelectorAll('.collapsible, [data-collapsible]');
            
            collapsibleSections.forEach(section => {
                this.setupCollapsible(section);
            });

            // Auto-create collapsible sections for long content
            this.autoCreateCollapsibles();
        },

        setupCollapsible: function(section) {
            const header = section.querySelector('.collapsible-header') || this.createHeader(section);
            const content = section.querySelector('.collapsible-content') || this.createContent(section);
            
            if (!header || !content) return;

            header.setAttribute('role', 'button');
            header.setAttribute('aria-expanded', 'false');
            header.setAttribute('aria-controls', content.id || this.generateId());
            header.setAttribute('tabindex', '0');

            if (!content.id) {
                content.id = this.generateId();
            }

            header.addEventListener('click', () => this.toggle(section));
            header.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    this.toggle(section);
                }
            });
        },

        createHeader: function(section) {
            const firstChild = section.firstElementChild;
            if (firstChild && ['H1', 'H2', 'H3', 'H4', 'H5', 'H6'].includes(firstChild.tagName)) {
                const header = document.createElement('button');
                header.className = 'collapsible-header';
                header.innerHTML = firstChild.innerHTML + '<span class="collapsible-toggle">▼</span>';
                section.replaceChild(header, firstChild);
                return header;
            }
            return null;
        },

        createContent: function(section) {
            const header = section.querySelector('.collapsible-header');
            if (!header) return null;

            const content = document.createElement('div');
            content.className = 'collapsible-content';
            
            const inner = document.createElement('div');
            inner.className = 'collapsible-inner';
            
            // Move all content after header into collapsible content
            let nextElement = header.nextElementSibling;
            while (nextElement) {
                const current = nextElement;
                nextElement = nextElement.nextElementSibling;
                inner.appendChild(current);
            }
            
            content.appendChild(inner);
            section.appendChild(content);
            return content;
        },

        toggle: function(section) {
            const isOpen = section.classList.contains('open');
            const header = section.querySelector('.collapsible-header');
            const content = section.querySelector('.collapsible-content');
            
            if (isOpen) {
                section.classList.remove('open');
                header.setAttribute('aria-expanded', 'false');
                a11y.announce('Section collapsed');
            } else {
                section.classList.add('open');
                header.setAttribute('aria-expanded', 'true');
                a11y.announce('Section expanded');
            }
            
            performanceMetrics.interactions++;
        },

        autoCreateCollapsibles: function() {
            // Auto-collapse very long sections that aren't already collapsible
            const longSections = document.querySelectorAll('section, article, .admonition');
            
            longSections.forEach(section => {
                if (section.classList.contains('collapsible') || section.querySelector('.collapsible-header')) {
                    return; // Already handled
                }
                
                const height = section.offsetHeight;
                const wordCount = section.textContent.split(/\s+/).length;
                
                // Make collapsible if over 500 words or 600px tall
                if (wordCount > 500 || height > 600) {
                    section.classList.add('collapsible');
                    this.setupCollapsible(section);
                }
            });
        },

        setupKeyboardControls: function() {
            document.addEventListener('keydown', (e) => {
                // Alt + C to collapse/expand all sections
                if (e.altKey && e.key === 'c') {
                    const allSections = document.querySelectorAll('.collapsible');
                    const anyOpen = Array.from(allSections).some(s => s.classList.contains('open'));
                    
                    allSections.forEach(section => {
                        if (anyOpen) {
                            section.classList.remove('open');
                            section.querySelector('.collapsible-header')?.setAttribute('aria-expanded', 'false');
                        } else {
                            section.classList.add('open');
                            section.querySelector('.collapsible-header')?.setAttribute('aria-expanded', 'true');
                        }
                    });
                    
                    a11y.announce(anyOpen ? 'All sections collapsed' : 'All sections expanded');
                    e.preventDefault();
                }
            });
        },

        generateId: function() {
            return 'collapsible-' + Math.random().toString(36).substr(2, 9);
        }
    };

    // Enhanced search functionality
    const enhancedSearch = {
        init: function() {
            this.setupSearchHighlighting();
            this.setupKeyboardShortcuts();
            this.trackSearchMetrics();
        },

        setupSearchHighlighting: function() {
            const searchInput = document.querySelector('input[data-md-component="search-query"]');
            if (!searchInput) return;

            let highlightTimeout;
            
            searchInput.addEventListener('input', (e) => {
                clearTimeout(highlightTimeout);
                highlightTimeout = setTimeout(() => {
                    this.highlightSearchTerms(e.target.value);
                    performanceMetrics.searchQueries++;
                }, 300);
            });

            // Clear highlights when search is closed
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape') {
                    this.clearHighlights();
                }
            });
        },

        highlightSearchTerms: function(query) {
            this.clearHighlights();
            
            if (!query || query.length < 2) return;

            const terms = query.toLowerCase().split(/\s+/).filter(term => term.length > 1);
            const contentElements = document.querySelectorAll('.md-content p, .md-content li, .md-content h1, .md-content h2, .md-content h3');

            contentElements.forEach(element => {
                this.highlightInElement(element, terms);
            });
        },

        highlightInElement: function(element, terms) {
            const walker = document.createTreeWalker(
                element,
                NodeFilter.SHOW_TEXT,
                null,
                false
            );

            const textNodes = [];
            let node;
            while (node = walker.nextNode()) {
                textNodes.push(node);
            }

            textNodes.forEach(textNode => {
                let text = textNode.textContent;
                let highlightedText = text;
                
                terms.forEach(term => {
                    const regex = new RegExp(`(${this.escapeRegex(term)})`, 'gi');
                    highlightedText = highlightedText.replace(regex, '<mark class="search-highlight">$1</mark>');
                });

                if (highlightedText !== text) {
                    const span = document.createElement('span');
                    span.innerHTML = highlightedText;
                    textNode.parentNode.replaceChild(span, textNode);
                }
            });
        },

        clearHighlights: function() {
            const highlights = document.querySelectorAll('.search-highlight');
            highlights.forEach(highlight => {
                const parent = highlight.parentNode;
                parent.replaceChild(document.createTextNode(highlight.textContent), highlight);
                parent.normalize();
            });
        },

        escapeRegex: function(string) {
            return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        },

        setupKeyboardShortcuts: function() {
            document.addEventListener('keydown', (e) => {
                // Ctrl/Cmd + K to focus search
                if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                    e.preventDefault();
                    const searchInput = document.querySelector('input[data-md-component="search-query"]');
                    if (searchInput) {
                        searchInput.focus();
                        searchInput.select();
                    }
                }
            });
        },

        trackSearchMetrics: function() {
            const searchButton = document.querySelector('[data-md-component="search-button"]');
            if (searchButton) {
                searchButton.addEventListener('click', () => {
                    performanceMetrics.interactions++;
                });
            }
        }
    };

    // Citation management
    const citations = {
        init: function() {
            this.setupCitationCopy();
            this.createCitationTooltips();
        },

        setupCitationCopy: function() {
            const citations = document.querySelectorAll('.citation');
            
            citations.forEach(citation => {
                const copyButton = document.createElement('button');
                copyButton.className = 'citation-copy-btn';
                copyButton.textContent = 'Copy Citation';
                copyButton.setAttribute('aria-label', 'Copy citation to clipboard');
                
                copyButton.addEventListener('click', () => {
                    const citationText = this.formatCitation(citation);
                    navigator.clipboard.writeText(citationText).then(() => {
                        a11y.announce('Citation copied to clipboard');
                        this.showCopySuccess(copyButton);
                    });
                });
                
                citation.appendChild(copyButton);
            });
        },

        formatCitation: function(citationElement) {
            const content = citationElement.querySelector('.citation-content')?.textContent || '';
            const author = citationElement.querySelector('.citation-author')?.textContent || '';
            const url = window.location.href;
            const date = new Date().toLocaleDateString();
            
            return `${content}\n\n${author}\nRetrieved from: ${url}\nAccessed: ${date}`;
        },

        createCitationTooltips: function() {
            const links = document.querySelectorAll('a[href^="http"]');
            
            links.forEach(link => {
                if (!link.querySelector('.tooltip-content')) {
                    const tooltip = document.createElement('span');
                    tooltip.className = 'tooltip-content';
                    tooltip.textContent = `External link: ${link.href}`;
                    
                    link.classList.add('tooltip');
                    link.appendChild(tooltip);
                }
            });
        },

        showCopySuccess: function(button) {
            const originalText = button.textContent;
            button.textContent = 'Copied!';
            
            setTimeout(() => {
                button.textContent = originalText;
            }, 2000);
        }
    };

    // Tab functionality
    const tabs = {
        init: function() {
            this.setupTabs();
        },

        setupTabs: function() {
            const tabContainers = document.querySelectorAll('.tab-container');
            
            tabContainers.forEach(container => {
                this.initializeTabContainer(container);
            });
        },

        initializeTabContainer: function(container) {
            const tabs = container.querySelectorAll('.tab-button');
            const contents = container.querySelectorAll('.tab-content');
            
            tabs.forEach((tab, index) => {
                tab.setAttribute('role', 'tab');
                tab.setAttribute('aria-controls', contents[index]?.id || `tab-content-${index}`);
                tab.setAttribute('aria-selected', index === 0 ? 'true' : 'false');
                tab.setAttribute('tabindex', index === 0 ? '0' : '-1');
                
                if (!contents[index]?.id) {
                    contents[index].id = `tab-content-${index}`;
                }
                
                contents[index].setAttribute('role', 'tabpanel');
                contents[index].setAttribute('aria-labelledby', tab.id || `tab-${index}`);
                
                if (!tab.id) {
                    tab.id = `tab-${index}`;
                }
                
                tab.addEventListener('click', () => this.switchTab(container, index));
                tab.addEventListener('keydown', (e) => this.handleTabKeydown(e, container, index));
            });
            
            // Show first tab by default
            if (contents[0]) {
                contents[0].classList.add('active');
                tabs[0]?.classList.add('active');
            }
        },

        switchTab: function(container, activeIndex) {
            const tabs = container.querySelectorAll('.tab-button');
            const contents = container.querySelectorAll('.tab-content');
            
            tabs.forEach((tab, index) => {
                tab.classList.toggle('active', index === activeIndex);
                tab.setAttribute('aria-selected', index === activeIndex ? 'true' : 'false');
                tab.setAttribute('tabindex', index === activeIndex ? '0' : '-1');
            });
            
            contents.forEach((content, index) => {
                content.classList.toggle('active', index === activeIndex);
            });
            
            tabs[activeIndex]?.focus();
            performanceMetrics.interactions++;
        },

        handleTabKeydown: function(e, container, currentIndex) {
            const tabs = container.querySelectorAll('.tab-button');
            let newIndex = currentIndex;
            
            switch (e.key) {
                case 'ArrowLeft':
                    newIndex = currentIndex > 0 ? currentIndex - 1 : tabs.length - 1;
                    break;
                case 'ArrowRight':
                    newIndex = currentIndex < tabs.length - 1 ? currentIndex + 1 : 0;
                    break;
                case 'Home':
                    newIndex = 0;
                    break;
                case 'End':
                    newIndex = tabs.length - 1;
                    break;
                default:
                    return;
            }
            
            e.preventDefault();
            this.switchTab(container, newIndex);
        }
    };

    // Performance monitoring
    const performance = {
        init: function() {
            this.setupPerformanceMonitoring();
            this.reportMetrics();
        },

        setupPerformanceMonitoring: function() {
            // Monitor interaction responsiveness
            document.addEventListener('click', this.measureInteraction);
            document.addEventListener('keydown', this.measureInteraction);
            
            // Monitor page load performance
            window.addEventListener('load', () => {
                const loadTime = performance.now() - performanceMetrics.startTime;
                console.log(`Documentation site loaded in ${loadTime.toFixed(2)}ms`);
            });
        },

        measureInteraction: function() {
            const now = performance.now();
            performanceMetrics.interactions++;
            
            // Log slow interactions
            requestAnimationFrame(() => {
                const responseTime = performance.now() - now;
                if (responseTime > 16) { // >16ms indicates potential lag
                    console.warn(`Slow interaction detected: ${responseTime.toFixed(2)}ms`);
                }
            });
        },

        reportMetrics: function() {
            // Report metrics every 30 seconds
            setInterval(() => {
                console.log('Documentation Performance Metrics:', {
                    uptime: ((performance.now() - performanceMetrics.startTime) / 1000).toFixed(1) + 's',
                    interactions: performanceMetrics.interactions,
                    searchQueries: performanceMetrics.searchQueries
                });
            }, 30000);
        }
    };

    // Accessibility enhancements
    const accessibility = {
        init: function() {
            this.addSkipLinks();
            this.enhanceKeyboardNavigation();
            this.improveScreenReaderExperience();
            this.setupFocusManagement();
        },

        addSkipLinks: function() {
            if (document.querySelector('.skip-link')) return;
            
            const skipLink = document.createElement('a');
            skipLink.href = '#main-content';
            skipLink.className = 'skip-link';
            skipLink.textContent = 'Skip to main content';
            
            document.body.insertBefore(skipLink, document.body.firstChild);
            
            // Ensure main content has an ID
            const mainContent = document.querySelector('main, .md-content, #content');
            if (mainContent && !mainContent.id) {
                mainContent.id = 'main-content';
            }
        },

        enhanceKeyboardNavigation: function() {
            // Make cards focusable
            const cards = document.querySelectorAll('.feature-card, .status-item, .metric-card');
            cards.forEach((card, index) => {
                if (!card.hasAttribute('tabindex')) {
                    card.setAttribute('tabindex', '0');
                    card.setAttribute('role', 'article');
                    
                    card.addEventListener('keydown', (e) => {
                        if (e.key === 'Enter') {
                            const link = card.querySelector('a');
                            if (link) {
                                link.click();
                            }
                        }
                    });
                }
            });
        },

        improveScreenReaderExperience: function() {
            // Add appropriate ARIA labels
            const statusBadges = document.querySelectorAll('.status-badge');
            statusBadges.forEach(badge => {
                if (!badge.hasAttribute('aria-label')) {
                    const status = badge.textContent.trim();
                    badge.setAttribute('aria-label', `Status: ${status}`);
                }
            });

            // Improve table accessibility
            const tables = document.querySelectorAll('table');
            tables.forEach(table => {
                if (!table.querySelector('caption') && !table.hasAttribute('aria-label')) {
                    const title = table.previousElementSibling;
                    if (title && ['H1', 'H2', 'H3', 'H4', 'H5', 'H6'].includes(title.tagName)) {
                        table.setAttribute('aria-labelledby', title.id || this.generateId(title));
                    }
                }
            });
        },

        setupFocusManagement: function() {
            // Trap focus in modals/dialogs
            const modals = document.querySelectorAll('[role="dialog"], .modal');
            modals.forEach(modal => {
                a11y.trapFocus(modal);
            });

            // Improve focus visibility
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Tab') {
                    document.body.classList.add('keyboard-nav');
                }
            });

            document.addEventListener('mousedown', () => {
                document.body.classList.remove('keyboard-nav');
            });
        },

        generateId: function(element) {
            const id = 'auto-id-' + Math.random().toString(36).substr(2, 9);
            element.id = id;
            return id;
        }
    };

    // Lazy loading for performance
    const lazyLoading = {
        init: function() {
            this.setupImageLazyLoading();
            this.setupContentLazyLoading();
        },

        setupImageLazyLoading: function() {
            const images = document.querySelectorAll('img[data-src]');
            
            if ('IntersectionObserver' in window) {
                const imageObserver = new IntersectionObserver((entries) => {
                    entries.forEach(entry => {
                        if (entry.isIntersecting) {
                            const img = entry.target;
                            img.src = img.dataset.src;
                            img.removeAttribute('data-src');
                            imageObserver.unobserve(img);
                        }
                    });
                });

                images.forEach(img => imageObserver.observe(img));
            } else {
                // Fallback for older browsers
                images.forEach(img => {
                    img.src = img.dataset.src;
                    img.removeAttribute('data-src');
                });
            }
        },

        setupContentLazyLoading: function() {
            const lazyContent = document.querySelectorAll('[data-lazy-load]');
            
            if ('IntersectionObserver' in window) {
                const contentObserver = new IntersectionObserver((entries) => {
                    entries.forEach(entry => {
                        if (entry.isIntersecting) {
                            this.loadContent(entry.target);
                            contentObserver.unobserve(entry.target);
                        }
                    });
                });

                lazyContent.forEach(content => contentObserver.observe(content));
            }
        },

        loadContent: function(element) {
            const url = element.dataset.lazyLoad;
            if (!url) return;

            fetch(url)
                .then(response => response.text())
                .then(html => {
                    element.innerHTML = html;
                    element.removeAttribute('data-lazy-load');
                    
                    // Reinitialize features for new content
                    codeCopy.addCopyButtons();
                    collapsible.createCollapsibleSections();
                })
                .catch(error => {
                    console.error('Failed to load lazy content:', error);
                    element.innerHTML = '<p>Failed to load content. Please refresh the page.</p>';
                });
        }
    };

    // Progressive Web App features
    const pwa = {
        init: function() {
            this.registerServiceWorker();
            this.setupInstallPrompt();
            this.setupOfflineDetection();
            this.enableNotifications();
        },

        registerServiceWorker: function() {
            if ('serviceWorker' in navigator) {
                window.addEventListener('load', async () => {
                    try {
                        const registration = await navigator.serviceWorker.register('/sw.js');
                        console.log('Service Worker registered:', registration);
                        
                        // Listen for updates
                        registration.addEventListener('updatefound', () => {
                            const newWorker = registration.installing;
                            newWorker.addEventListener('statechange', () => {
                                if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                                    this.showUpdateNotification();
                                }
                            });
                        });
                        
                        // Get performance metrics from service worker
                        this.setupServiceWorkerMessaging();
                        
                    } catch (error) {
                        console.log('Service Worker registration failed:', error);
                    }
                });
            }
        },

        setupServiceWorkerMessaging: function() {
            if (!navigator.serviceWorker.controller) return;
            
            // Get performance metrics
            const getMetrics = () => {
                const channel = new MessageChannel();
                channel.port1.onmessage = (event) => {
                    if (event.data.type === 'PERFORMANCE_METRICS') {
                        console.log('SW Performance:', event.data.data);
                        this.displayCacheMetrics(event.data.data);
                    }
                };
                
                navigator.serviceWorker.controller.postMessage(
                    { type: 'GET_PERFORMANCE_METRICS' },
                    [channel.port2]
                );
            };
            
            // Get metrics every 30 seconds
            setInterval(getMetrics, 30000);
            getMetrics(); // Initial call
        },

        displayCacheMetrics: function(metrics) {
            // Create or update cache metrics display
            let metricsDiv = document.getElementById('cache-metrics');
            if (!metricsDiv) {
                metricsDiv = document.createElement('div');
                metricsDiv.id = 'cache-metrics';
                metricsDiv.style.cssText = `
                    position: fixed;
                    bottom: 10px;
                    left: 10px;
                    background: rgba(0,0,0,0.8);
                    color: white;
                    padding: 8px 12px;
                    border-radius: 4px;
                    font-size: 12px;
                    font-family: monospace;
                    z-index: 9999;
                    opacity: 0.7;
                `;
                document.body.appendChild(metricsDiv);
            }
            
            metricsDiv.innerHTML = `
                Cache Hit Rate: ${metrics.cacheHitRate}%<br>
                Total Requests: ${metrics.totalRequests}
            `;
            
            // Hide after 5 seconds
            setTimeout(() => {
                if (metricsDiv.parentNode) {
                    metricsDiv.style.opacity = '0.3';
                }
            }, 5000);
        },

        setupInstallPrompt: function() {
            let deferredPrompt;
            
            window.addEventListener('beforeinstallprompt', (e) => {
                e.preventDefault();
                deferredPrompt = e;
                this.showInstallButton();
            });
            
            window.addEventListener('appinstalled', () => {
                console.log('PWA installed');
                this.hideInstallButton();
                a11y.announce('App installed successfully');
            });
        },

        showInstallButton: function() {
            const installBtn = document.createElement('button');
            installBtn.id = 'pwa-install-btn';
            installBtn.textContent = '📱 Install App';
            installBtn.className = 'install-button';
            installBtn.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 1000;
                background: var(--primary-blue, #1e40af);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 20px;
                font-size: 14px;
                font-weight: 600;
                cursor: pointer;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                transition: all 0.2s ease;
            `;
            
            installBtn.addEventListener('click', this.installApp.bind(this));
            document.body.appendChild(installBtn);
        },

        hideInstallButton: function() {
            const installBtn = document.getElementById('pwa-install-btn');
            if (installBtn) {
                installBtn.remove();
            }
        },

        installApp: async function() {
            const deferredPrompt = window.deferredPrompt;
            if (!deferredPrompt) return;
            
            deferredPrompt.prompt();
            const result = await deferredPrompt.userChoice;
            
            if (result.outcome === 'accepted') {
                console.log('User accepted the install prompt');
            }
            
            window.deferredPrompt = null;
            this.hideInstallButton();
        },

        setupOfflineDetection: function() {
            const updateOnlineStatus = () => {
                const isOnline = navigator.onLine;
                document.body.classList.toggle('offline', !isOnline);
                
                if (!isOnline) {
                    this.showOfflineNotification();
                } else {
                    this.hideOfflineNotification();
                    this.syncOfflineData();
                }
            };
            
            window.addEventListener('online', updateOnlineStatus);
            window.addEventListener('offline', updateOnlineStatus);
            updateOnlineStatus(); // Initial check
        },

        showOfflineNotification: function() {
            let notification = document.getElementById('offline-notification');
            if (notification) return;
            
            notification = document.createElement('div');
            notification.id = 'offline-notification';
            notification.innerHTML = `
                <span>📡 You're offline</span>
                <span>Some features may be limited</span>
            `;
            notification.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                background: #f59e0b;
                color: white;
                padding: 12px;
                text-align: center;
                font-weight: 600;
                z-index: 10000;
                display: flex;
                justify-content: center;
                align-items: center;
                gap: 16px;
                animation: slideDown 0.3s ease;
            `;
            
            document.body.appendChild(notification);
            a11y.announce('You are now offline. Some features may be limited.');
        },

        hideOfflineNotification: function() {
            const notification = document.getElementById('offline-notification');
            if (notification) {
                notification.style.animation = 'slideUp 0.3s ease';
                setTimeout(() => notification.remove(), 300);
                a11y.announce('You are back online');
            }
        },

        syncOfflineData: function() {
            // Sync any offline data when back online
            const offlineMetrics = localStorage.getItem('offline_metrics');
            if (offlineMetrics) {
                try {
                    const metrics = JSON.parse(offlineMetrics);
                    if (window.performanceMonitor) {
                        window.performanceMonitor.sendOfflineMetrics(metrics);
                    }
                    localStorage.removeItem('offline_metrics');
                } catch (error) {
                    console.warn('Failed to sync offline metrics:', error);
                }
            }
        },

        enableNotifications: function() {
            if ('Notification' in window && Notification.permission === 'default') {
                // Request permission after user interaction
                document.addEventListener('click', () => {
                    Notification.requestPermission().then(permission => {
                        if (permission === 'granted') {
                            console.log('Notifications enabled');
                        }
                    });
                }, { once: true });
            }
        },

        showUpdateNotification: function() {
            if ('Notification' in window && Notification.permission === 'granted') {
                new Notification('Documentation Updated', {
                    body: 'New content is available. Refresh to see the latest updates.',
                    icon: '/assets/images/favicon.png',
                    badge: '/assets/images/badge.png',
                    tag: 'documentation-update'
                });
            } else {
                // Fallback in-page notification
                const updateNotice = document.createElement('div');
                updateNotice.style.cssText = `
                    position: fixed;
                    top: 20px;
                    left: 50%;
                    transform: translateX(-50%);
                    background: #10b981;
                    color: white;
                    padding: 12px 24px;
                    border-radius: 8px;
                    font-weight: 600;
                    z-index: 10000;
                    cursor: pointer;
                `;
                updateNotice.innerHTML = '🔄 New content available - Click to refresh';
                updateNotice.addEventListener('click', () => window.location.reload());
                document.body.appendChild(updateNotice);
                
                setTimeout(() => updateNotice.remove(), 10000);
            }
        }
    };

    // Advanced search with faceted filtering
    const advancedSearch = {
        init: function() {
            this.setupSearchFilters();
            this.enableSearchHistory();
            this.setupKeyboardShortcuts();
        },

        setupSearchFilters: function() {
            const searchContainer = document.querySelector('.md-search');
            if (!searchContainer) return;
            
            // Add filter controls
            const filterContainer = document.createElement('div');
            filterContainer.className = 'search-filters';
            filterContainer.innerHTML = `
                <div class="filter-group">
                    <label>Content Type:</label>
                    <select id="content-type-filter">
                        <option value="">All</option>
                        <option value="tutorial">Tutorials</option>
                        <option value="reference">API Reference</option>
                        <option value="example">Examples</option>
                        <option value="documentation">Documentation</option>
                    </select>
                </div>
                <div class="filter-group">
                    <label>Language:</label>
                    <select id="language-filter">
                        <option value="">All</option>
                        <option value="python">Python</option>
                        <option value="matlab">MATLAB</option>
                        <option value="javascript">JavaScript</option>
                    </select>
                </div>
            `;
            
            searchContainer.appendChild(filterContainer);
            this.attachFilterListeners();
        },

        attachFilterListeners: function() {
            const filters = document.querySelectorAll('.search-filters select');
            filters.forEach(filter => {
                filter.addEventListener('change', () => {
                    this.applySearchFilters();
                });
            });
        },

        applySearchFilters: function() {
            const contentType = document.getElementById('content-type-filter')?.value;
            const language = document.getElementById('language-filter')?.value;
            
            // Apply filters to search results
            const results = document.querySelectorAll('.md-search-result');
            results.forEach(result => {
                let show = true;
                
                if (contentType && !result.dataset.contentType?.includes(contentType)) {
                    show = false;
                }
                
                if (language && !result.dataset.language?.includes(language)) {
                    show = false;
                }
                
                result.style.display = show ? 'block' : 'none';
            });
        },

        enableSearchHistory: function() {
            const searchInput = document.querySelector('input[data-md-component="search-query"]');
            if (!searchInput) return;
            
            let searchHistory = JSON.parse(localStorage.getItem('search_history') || '[]');
            
            searchInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    const query = e.target.value.trim();
                    if (query && !searchHistory.includes(query)) {
                        searchHistory.unshift(query);
                        searchHistory = searchHistory.slice(0, 10); // Keep last 10
                        localStorage.setItem('search_history', JSON.stringify(searchHistory));
                    }
                }
            });
        },

        setupKeyboardShortcuts: function() {
            document.addEventListener('keydown', (e) => {
                // Ctrl/Cmd + Shift + F for advanced search
                if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'F') {
                    e.preventDefault();
                    this.showAdvancedSearchModal();
                }
            });
        },

        showAdvancedSearchModal: function() {
            // Create advanced search modal
            const modal = document.createElement('div');
            modal.className = 'advanced-search-modal';
            modal.innerHTML = `
                <div class="modal-content">
                    <h3>Advanced Search</h3>
                    <div class="search-options">
                        <input type="text" placeholder="Search query..." id="advanced-search-input">
                        <div class="search-filters">
                            <!-- Filter controls here -->
                        </div>
                    </div>
                    <div class="modal-actions">
                        <button id="search-submit">Search</button>
                        <button id="search-cancel">Cancel</button>
                    </div>
                </div>
            `;
            
            document.body.appendChild(modal);
            
            // Focus trap and keyboard handling
            a11y.trapFocus(modal);
            
            // Event listeners
            document.getElementById('search-cancel').addEventListener('click', () => {
                modal.remove();
            });
            
            document.getElementById('search-submit').addEventListener('click', () => {
                const query = document.getElementById('advanced-search-input').value;
                this.performAdvancedSearch(query);
                modal.remove();
            });
        },

        performAdvancedSearch: function(query) {
            // Implement advanced search logic
            console.log('Performing advanced search:', query);
            
            // Track advanced search usage
            if (window.performanceMonitor) {
                window.performanceMonitor.trackEvent('advanced_search', {
                    query_length: query.length,
                    has_filters: true
                });
            }
        }
    };

    // Initialize all features when DOM is ready
    function init() {
        // Core features
        codeCopy.init();
        collapsible.init();
        enhancedSearch.init();
        citations.init();
        tabs.init();
        accessibility.init();
        lazyLoading.init();
        performance.init();
        
        // New Wave 4 features
        pwa.init();
        advancedSearch.init();

        // Create ARIA live region for announcements
        a11y.createLiveRegion();

        console.log('Enhanced Documentation Interactivity initialized with PWA features');
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Expose utilities for external use
    window.DocsInteractivity = {
        codeCopy,
        collapsible,
        enhancedSearch,
        citations,
        accessibility,
        performanceMetrics
    };

})();