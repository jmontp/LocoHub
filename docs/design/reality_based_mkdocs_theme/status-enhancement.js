/**
 * Reality-Based MkDocs Theme - Status Enhancement JavaScript
 * Created: 2025-06-19 with user permission
 * Purpose: Interactive enhancements for status-aware documentation
 * 
 * This script provides dynamic status tracking, interactive elements,
 * and user experience enhancements for the truth-oriented design system.
 */

(function() {
    'use strict';

    // Status tracking and enhancement functionality
    const StatusEnhancer = {
        
        // Initialize all status enhancements
        init: function() {
            this.enhanceStatusBadges();
            this.addStatusFiltering();
            this.trackStatusInteractions();
            this.enhanceCodeExamples();
            this.addAccessibilityFeatures();
            this.initStatusDashboard();
        },

        // Enhance status badges with interactive features
        enhanceStatusBadges: function() {
            const badges = document.querySelectorAll('.status-badge');
            
            badges.forEach(badge => {
                // Add tooltip with detailed status information
                this.addStatusTooltip(badge);
                
                // Add click tracking for analytics
                badge.addEventListener('click', (e) => {
                    const status = badge.classList.contains('status-available') ? 'available' :
                                 badge.classList.contains('status-verified') ? 'verified' :
                                 badge.classList.contains('status-partial') ? 'partial' :
                                 badge.classList.contains('status-planned') ? 'planned' :
                                 badge.classList.contains('status-broken') ? 'broken' : 'unknown';
                    
                    this.trackEvent('status_badge_clicked', {
                        status: status,
                        page: window.location.pathname
                    });
                });
                
                // Enhance keyboard accessibility
                badge.setAttribute('tabindex', '0');
                badge.setAttribute('role', 'button');
                
                badge.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        badge.click();
                    }
                });
            });
        },

        // Add detailed tooltips to status badges
        addStatusTooltip: function(badge) {
            const statusText = badge.querySelector('.badge-text')?.textContent || '';
            let tooltipText = '';
            
            if (badge.classList.contains('status-available')) {
                tooltipText = 'This feature is fully implemented and ready for production use.';
            } else if (badge.classList.contains('status-verified')) {
                tooltipText = 'This feature has comprehensive test coverage and is verified to work.';
            } else if (badge.classList.contains('status-partial')) {
                tooltipText = 'This feature works but has known limitations. Use with caution.';
            } else if (badge.classList.contains('status-planned')) {
                tooltipText = 'This feature is planned for future implementation. Do not rely on it yet.';
            } else if (badge.classList.contains('status-broken')) {
                tooltipText = 'This feature has known issues and should not be used.';
            }
            
            badge.setAttribute('title', tooltipText);
            badge.setAttribute('aria-label', `${statusText}: ${tooltipText}`);
        },

        // Add filtering functionality for status-based content
        addStatusFiltering: function() {
            // Create filter controls if they don't exist
            const filterContainer = document.querySelector('.status-filter-container');
            if (!filterContainer) {
                this.createStatusFilter();
            }
            
            // Add filter event listeners
            const filterButtons = document.querySelectorAll('.status-filter-btn');
            filterButtons.forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.preventDefault();
                    const filter = btn.dataset.filter;
                    this.applyStatusFilter(filter);
                    this.updateFilterButtonState(btn);
                });
            });
        },

        // Create status filter UI
        createStatusFilter: function() {
            const main = document.querySelector('main');
            if (!main) return;
            
            const filterHtml = `
                <div class="status-filter-container">
                    <div class="status-filter-label">Filter by status:</div>
                    <div class="status-filter-buttons">
                        <button class="status-filter-btn active" data-filter="all">All</button>
                        <button class="status-filter-btn" data-filter="available">Available</button>
                        <button class="status-filter-btn" data-filter="verified">Tested</button>
                        <button class="status-filter-btn" data-filter="partial">Partial</button>
                        <button class="status-filter-btn" data-filter="planned">Planned</button>
                    </div>
                </div>
            `;
            
            main.insertAdjacentHTML('afterbegin', filterHtml);
            
            // Add CSS for filter controls
            this.addFilterStyles();
        },

        // Apply status-based filtering
        applyStatusFilter: function(filter) {
            const featureCards = document.querySelectorAll('.feature-card');
            const codeExamples = document.querySelectorAll('.code-example');
            const statusElements = [...featureCards, ...codeExamples];
            
            statusElements.forEach(element => {
                if (filter === 'all') {
                    element.style.display = '';
                    element.setAttribute('aria-hidden', 'false');
                } else {
                    const hasStatus = element.classList.contains(filter) || 
                                    element.querySelector(`.status-${filter}`) !== null;
                    
                    if (hasStatus) {
                        element.style.display = '';
                        element.setAttribute('aria-hidden', 'false');
                    } else {
                        element.style.display = 'none';
                        element.setAttribute('aria-hidden', 'true');
                    }
                }
            });
            
            // Track filter usage
            this.trackEvent('status_filter_applied', {
                filter: filter,
                page: window.location.pathname
            });
        },

        // Update filter button active state
        updateFilterButtonState: function(activeBtn) {
            const filterButtons = document.querySelectorAll('.status-filter-btn');
            filterButtons.forEach(btn => {
                btn.classList.remove('active');
                btn.setAttribute('aria-pressed', 'false');
            });
            
            activeBtn.classList.add('active');
            activeBtn.setAttribute('aria-pressed', 'true');
        },

        // Track user interactions with status elements
        trackStatusInteractions: function() {
            // Track feature card interactions
            const featureCards = document.querySelectorAll('.feature-card');
            featureCards.forEach(card => {
                card.addEventListener('click', () => {
                    const title = card.querySelector('.feature-title')?.textContent || 'Unknown';
                    const status = this.getElementStatus(card);
                    
                    this.trackEvent('feature_card_clicked', {
                        feature: title,
                        status: status,
                        page: window.location.pathname
                    });
                });
            });
            
            // Track code example interactions
            const codeExamples = document.querySelectorAll('.code-example');
            codeExamples.forEach(example => {
                const copyBtn = example.querySelector('button[data-clipboard-text]');
                if (copyBtn) {
                    copyBtn.addEventListener('click', () => {
                        const title = example.querySelector('.code-title')?.textContent || 'Unknown';
                        const status = this.getElementStatus(example);
                        
                        this.trackEvent('code_example_copied', {
                            example: title,
                            status: status,
                            page: window.location.pathname
                        });
                    });
                }
            });
        },

        // Get status of an element
        getElementStatus: function(element) {
            if (element.classList.contains('available') || element.querySelector('.status-available')) return 'available';
            if (element.classList.contains('verified') || element.querySelector('.status-verified')) return 'verified';
            if (element.classList.contains('partial') || element.querySelector('.status-partial')) return 'partial';
            if (element.classList.contains('planned') || element.querySelector('.status-planned')) return 'planned';
            if (element.classList.contains('broken') || element.querySelector('.status-broken')) return 'broken';
            return 'unknown';
        },

        // Enhance code examples with status-aware features
        enhanceCodeExamples: function() {
            const codeExamples = document.querySelectorAll('.code-example');
            
            codeExamples.forEach(example => {
                // Add status-specific styling
                const status = this.getElementStatus(example);
                
                // Add warning for non-tested code
                if (status === 'partial' || status === 'broken') {
                    this.addCodeWarning(example, status);
                }
                
                // Add verification badge for tested code
                if (status === 'verified' || status === 'available') {
                    this.addVerificationBadge(example);
                }
                
                // Enhance copy functionality with status tracking
                this.enhanceCodeCopy(example);
            });
        },

        // Add warning to non-verified code examples
        addCodeWarning: function(example, status) {
            const warningText = status === 'partial' ? 
                'This code has limited testing. Use with caution.' :
                'This code has known issues and may not work as expected.';
            
            const warning = document.createElement('div');
            warning.className = 'code-warning';
            warning.innerHTML = `
                <span class="warning-icon">⚠️</span>
                <span class="warning-text">${warningText}</span>
            `;
            
            example.insertBefore(warning, example.firstChild);
        },

        // Add verification badge to tested code
        addVerificationBadge: function(example) {
            const badge = document.createElement('div');
            badge.className = 'verification-badge';
            badge.innerHTML = `
                <span class="verification-icon">✓</span>
                <span class="verification-text">Verified Code</span>
            `;
            
            const header = example.querySelector('.code-header');
            if (header) {
                header.appendChild(badge);
            }
        },

        // Enhance code copy functionality
        enhanceCodeCopy: function(example) {
            const codeBlock = example.querySelector('pre code');
            if (!codeBlock) return;
            
            // Add copy button if it doesn't exist
            let copyBtn = example.querySelector('.copy-code-btn');
            if (!copyBtn) {
                copyBtn = document.createElement('button');
                copyBtn.className = 'copy-code-btn';
                copyBtn.innerHTML = '📋 Copy';
                copyBtn.setAttribute('aria-label', 'Copy code to clipboard');
                
                const header = example.querySelector('.code-header');
                if (header) {
                    header.appendChild(copyBtn);
                }
            }
            
            // Add copy functionality
            copyBtn.addEventListener('click', async () => {
                try {
                    await navigator.clipboard.writeText(codeBlock.textContent);
                    copyBtn.innerHTML = '✓ Copied!';
                    copyBtn.classList.add('copied');
                    
                    setTimeout(() => {
                        copyBtn.innerHTML = '📋 Copy';
                        copyBtn.classList.remove('copied');
                    }, 2000);
                    
                } catch (err) {
                    console.warn('Failed to copy code:', err);
                    copyBtn.innerHTML = '❌ Failed';
                    setTimeout(() => {
                        copyBtn.innerHTML = '📋 Copy';
                    }, 2000);
                }
            });
        },

        // Add accessibility enhancements
        addAccessibilityFeatures: function() {
            // Add skip links for status sections
            this.addSkipLinks();
            
            // Enhance focus management
            this.enhanceFocusManagement();
            
            // Add ARIA live regions for dynamic content
            this.addLiveRegions();
            
            // Enhance keyboard navigation
            this.enhanceKeyboardNavigation();
        },

        // Add skip links for better navigation
        addSkipLinks: function() {
            const skipLinks = document.createElement('div');
            skipLinks.className = 'skip-links';
            skipLinks.innerHTML = `
                <a href="#available-features" class="skip-link">Skip to Available Features</a>
                <a href="#tested-features" class="skip-link">Skip to Tested Features</a>
                <a href="#main-content" class="skip-link">Skip to Main Content</a>
            `;
            
            document.body.insertBefore(skipLinks, document.body.firstChild);
        },

        // Enhance focus management for dynamic content
        enhanceFocusManagement: function() {
            const filterButtons = document.querySelectorAll('.status-filter-btn');
            
            filterButtons.forEach(btn => {
                btn.addEventListener('click', () => {
                    // Announce filter change to screen readers
                    this.announceToScreenReader(`Filtered content by ${btn.textContent} status`);
                });
            });
        },

        // Add ARIA live regions for dynamic announcements
        addLiveRegions: function() {
            const liveRegion = document.createElement('div');
            liveRegion.setAttribute('aria-live', 'polite');
            liveRegion.setAttribute('aria-atomic', 'true');
            liveRegion.className = 'sr-only';
            liveRegion.id = 'status-announcements';
            
            document.body.appendChild(liveRegion);
        },

        // Announce messages to screen readers
        announceToScreenReader: function(message) {
            const liveRegion = document.getElementById('status-announcements');
            if (liveRegion) {
                liveRegion.textContent = message;
                
                // Clear after announcement
                setTimeout(() => {
                    liveRegion.textContent = '';
                }, 1000);
            }
        },

        // Enhance keyboard navigation
        enhanceKeyboardNavigation: function() {
            // Add keyboard shortcuts
            document.addEventListener('keydown', (e) => {
                // Alt + 1-5 for status filters
                if (e.altKey && e.key >= '1' && e.key <= '5') {
                    e.preventDefault();
                    const filterIndex = parseInt(e.key) - 1;
                    const filterButtons = document.querySelectorAll('.status-filter-btn');
                    if (filterButtons[filterIndex]) {
                        filterButtons[filterIndex].click();
                        filterButtons[filterIndex].focus();
                    }
                }
                
                // Alt + S for status dashboard
                if (e.altKey && e.key === 's') {
                    e.preventDefault();
                    const dashboard = document.querySelector('.system-status');
                    if (dashboard) {
                        dashboard.scrollIntoView({ behavior: 'smooth' });
                        dashboard.focus();
                    }
                }
            });
        },

        // Initialize status dashboard with real-time updates
        initStatusDashboard: function() {
            const dashboard = document.querySelector('.system-status');
            if (!dashboard) return;
            
            // Update dashboard with current page status
            this.updateDashboardCounts();
            
            // Add hover effects for status items
            const statusItems = dashboard.querySelectorAll('.status-item');
            statusItems.forEach(item => {
                item.addEventListener('mouseenter', () => {
                    item.style.transform = 'scale(1.05)';
                    item.style.transition = 'transform 0.2s ease';
                });
                
                item.addEventListener('mouseleave', () => {
                    item.style.transform = 'scale(1)';
                });
            });
        },

        // Update dashboard with real counts from current page
        updateDashboardCounts: function() {
            const availableCount = document.querySelectorAll('.status-available').length;
            const verifiedCount = document.querySelectorAll('.status-verified').length;
            const partialCount = document.querySelectorAll('.status-partial').length;
            const plannedCount = document.querySelectorAll('.status-planned').length;
            
            const dashboard = document.querySelector('.system-status');
            if (dashboard) {
                const availableElement = dashboard.querySelector('.status-item.available .status-count');
                const verifiedElement = dashboard.querySelector('.status-item.verified .status-count');
                const partialElement = dashboard.querySelector('.status-item.partial .status-count');
                const plannedElement = dashboard.querySelector('.status-item.planned .status-count');
                
                if (availableElement) availableElement.textContent = availableCount;
                if (verifiedElement) verifiedElement.textContent = verifiedCount;
                if (partialElement) partialElement.textContent = partialCount;
                if (plannedElement) plannedElement.textContent = plannedCount;
            }
        },

        // Add CSS for filter controls and enhancements
        addFilterStyles: function() {
            const styles = `
                .status-filter-container {
                    display: flex;
                    align-items: center;
                    gap: 16px;
                    margin: 24px 0;
                    padding: 16px;
                    background-color: var(--trust-bg-secondary, #f8f9fa);
                    border-radius: 8px;
                    border: 1px solid var(--trust-border, #dee2e6);
                }
                
                .status-filter-label {
                    font-weight: 600;
                    color: var(--trust-text, #212529);
                }
                
                .status-filter-buttons {
                    display: flex;
                    gap: 8px;
                    flex-wrap: wrap;
                }
                
                .status-filter-btn {
                    padding: 6px 12px;
                    border: 1px solid var(--trust-border, #dee2e6);
                    background-color: var(--trust-bg, #ffffff);
                    color: var(--trust-text, #212529);
                    border-radius: 6px;
                    cursor: pointer;
                    font-size: 0.9em;
                    transition: all 0.2s ease;
                }
                
                .status-filter-btn:hover {
                    background-color: var(--trust-primary-light, #4a90e2);
                    color: white;
                    border-color: var(--trust-primary, #0056b3);
                }
                
                .status-filter-btn.active {
                    background-color: var(--trust-primary, #0056b3);
                    color: white;
                    border-color: var(--trust-primary, #0056b3);
                }
                
                .code-warning {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    padding: 8px 12px;
                    background-color: var(--status-warning-bg, #fff3cd);
                    border: 1px solid var(--status-warning-border, #ffeaa7);
                    border-radius: 4px;
                    margin-bottom: 8px;
                    font-size: 0.9em;
                    color: var(--status-warning, #856404);
                }
                
                .verification-badge {
                    display: flex;
                    align-items: center;
                    gap: 4px;
                    font-size: 0.8em;
                    color: var(--status-verified, #007bff);
                    margin-left: auto;
                }
                
                .copy-code-btn {
                    padding: 4px 8px;
                    border: 1px solid var(--trust-border, #dee2e6);
                    background-color: var(--trust-bg, #ffffff);
                    color: var(--trust-text, #212529);
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 0.8em;
                    transition: all 0.2s ease;
                    margin-left: 8px;
                }
                
                .copy-code-btn:hover {
                    background-color: var(--trust-bg-secondary, #f8f9fa);
                }
                
                .copy-code-btn.copied {
                    background-color: var(--status-available-bg, #d4edda);
                    color: var(--status-available, #28a745);
                    border-color: var(--status-available-border, #c3e6cb);
                }
                
                .skip-links {
                    position: absolute;
                    top: -40px;
                    left: 6px;
                    z-index: 1000;
                }
                
                .skip-link {
                    position: absolute;
                    top: -40px;
                    left: 6px;
                    background: var(--trust-primary, #0056b3);
                    color: white;
                    padding: 8px;
                    text-decoration: none;
                    border-radius: 4px;
                    transition: top 0.3s;
                }
                
                .skip-link:focus {
                    top: 6px;
                }
                
                @media (max-width: 768px) {
                    .status-filter-container {
                        flex-direction: column;
                        align-items: flex-start;
                        gap: 12px;
                    }
                    
                    .status-filter-buttons {
                        width: 100%;
                        justify-content: flex-start;
                    }
                }
            `;
            
            const styleSheet = document.createElement('style');
            styleSheet.textContent = styles;
            document.head.appendChild(styleSheet);
        },

        // Track events (placeholder for analytics)
        trackEvent: function(eventName, properties) {
            // This would integrate with your analytics platform
            console.log('Status Event:', eventName, properties);
            
            // Example integration with Google Analytics
            if (typeof gtag !== 'undefined') {
                gtag('event', eventName, properties);
            }
        }
    };

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => StatusEnhancer.init());
    } else {
        StatusEnhancer.init();
    }

    // Re-initialize on page navigation (for SPA-like behavior)
    window.addEventListener('popstate', () => {
        setTimeout(() => StatusEnhancer.init(), 100);
    });

    // Export for external access
    window.StatusEnhancer = StatusEnhancer;

})();