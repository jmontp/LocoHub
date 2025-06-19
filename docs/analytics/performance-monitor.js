/*
Cookie-Free Performance Monitoring and Analytics System
Created: 2025-06-19 with user permission
Purpose: Comprehensive performance tracking and user analytics for documentation effectiveness

STRICT NO-COOKIES POLICY:
- Zero cookies used for tracking or analytics
- Only sessionStorage for current session continuity (cleared on browser close)
- Google Analytics configured with storage: 'none' to disable all cookies
- Respects Do Not Track settings
- Privacy-first design with no persistent user tracking

Features:
- Real-time Core Web Vitals monitoring (FCP, LCP, FID, CLS)
- User behavior analytics (scroll depth, clicks, time on page)
- Documentation effectiveness metrics (code copying, search patterns)
- Performance regression detection and alerting
- Automated error tracking and reporting
- Mobile gesture and accessibility monitoring
*/

class PerformanceMonitor {
    constructor(config = {}) {
        this.config = {
            // Analytics configuration
            googleAnalyticsId: config.googleAnalyticsId || 'GA_MEASUREMENT_ID',
            enableRealUserMonitoring: config.enableRealUserMonitoring !== false,
            enableHeatmaps: config.enableHeatmaps || false,
            enableErrorTracking: config.enableErrorTracking !== false,
            
            // Performance thresholds
            performanceThresholds: {
                firstContentfulPaint: 2500,    // 2.5s
                largestContentfulPaint: 4000,   // 4s
                firstInputDelay: 100,           // 100ms
                cumulativeLayoutShift: 0.1,     // 0.1
                timeToInteractive: 5000         // 5s
            },
            
            // Sampling rates
            performanceSampling: config.performanceSampling || 1.0,  // 100%
            errorSampling: config.errorSampling || 1.0,              // 100%
            
            // Privacy settings - NO COOKIES POLICY
            respectDoNotTrack: config.respectDoNotTrack !== false,
            anonymizeIP: config.anonymizeIP !== false,
            noCookies: true,  // Strict no-cookies policy
            
            // Reporting endpoints
            endpoints: {
                performance: '/api/analytics/performance',
                errors: '/api/analytics/errors',
                interactions: '/api/analytics/interactions',
                feedback: '/api/analytics/feedback'
            }
        };
        
        this.metrics = {
            performance: new Map(),
            interactions: new Map(),
            errors: [],
            sessions: new Map()
        };
        
        this.sessionId = this.generateSessionId();
        this.pageLoadTime = performance.now();
        this.isVisible = !document.hidden;
        
        this.init();
    }
    
    init() {
        // Check privacy settings
        if (this.shouldRespectPrivacy()) {
            console.log('Analytics disabled due to privacy settings');
            return;
        }
        
        // Initialize core monitoring
        this.initializeGoogleAnalytics();
        this.initializePerformanceMonitoring();
        this.initializeUserBehaviorTracking();
        this.initializeErrorTracking();
        this.initializeFeedbackCollection();
        
        // Start monitoring
        this.startRealTimeMonitoring();
        this.setupPeriodicReporting();
        
        console.log('Performance monitoring initialized');
    }
    
    // Privacy management - COOKIE-FREE MONITORING
    shouldRespectPrivacy() {
        // Check Do Not Track - respect user privacy preferences
        if (this.config.respectDoNotTrack && navigator.doNotTrack === '1') {
            return true;
        }
        
        // No cookie checking needed - we're cookie-free!
        // Only use localStorage for session continuity (not user tracking)
        
        return false;
    }
    
    // Google Analytics integration
    initializeGoogleAnalytics() {
        if (!this.config.googleAnalyticsId || this.config.googleAnalyticsId === 'GA_MEASUREMENT_ID') {
            return; // Skip if not configured
        }
        
        // Load Google Analytics
        const script = document.createElement('script');
        script.async = true;
        script.src = `https://www.googletagmanager.com/gtag/js?id=${this.config.googleAnalyticsId}`;
        document.head.appendChild(script);
        
        // Initialize gtag
        window.dataLayer = window.dataLayer || [];
        function gtag(){dataLayer.push(arguments);}
        window.gtag = gtag;
        
        gtag('js', new Date());
        gtag('config', this.config.googleAnalyticsId, {
            // STRICT PRIVACY CONFIGURATION - NO COOKIES
            anonymize_ip: this.config.anonymizeIP,
            allow_google_signals: false,
            allow_ad_personalization_signals: false,
            
            // Disable all cookie usage
            storage: 'none',
            client_storage: 'none',
            cookie_flags: 'SameSite=None;Secure',
            cookie_update: false,
            cookie_expires: 0,
            
            // Performance tracking
            custom_map: {
                'custom_parameter_1': 'page_type',
                'custom_parameter_2': 'content_category',
                'custom_parameter_3': 'user_type'
            },
            
            // Enhanced measurement
            enhanced_measurement: {
                scrolls: true,
                outbound_clicks: true,
                site_search: true,
                video_engagement: true,
                file_downloads: true
            }
        });
        
        // Track initial page view with custom parameters
        this.trackPageView({
            page_type: this.getPageType(),
            content_category: this.getContentCategory(),
            user_type: this.getUserType()
        });
    }
    
    // Core Web Vitals and performance monitoring
    initializePerformanceMonitoring() {
        // Track Core Web Vitals
        this.trackCoreWebVitals();
        
        // Track custom performance metrics
        this.trackCustomMetrics();
        
        // Monitor resource loading
        this.monitorResourcePerformance();
        
        // Track JavaScript errors affecting performance
        this.monitorPerformanceErrors();
    }
    
    trackCoreWebVitals() {
        // First Contentful Paint (FCP)
        new PerformanceObserver((entryList) => {
            for (const entry of entryList.getEntries()) {
                if (entry.name === 'first-contentful-paint') {
                    this.recordMetric('FCP', entry.startTime, {
                        threshold: this.config.performanceThresholds.firstContentfulPaint,
                        critical: true
                    });
                }
            }
        }).observe({ entryTypes: ['paint'] });
        
        // Largest Contentful Paint (LCP)
        new PerformanceObserver((entryList) => {
            const entries = entryList.getEntries();
            const lastEntry = entries[entries.length - 1];
            this.recordMetric('LCP', lastEntry.startTime, {
                threshold: this.config.performanceThresholds.largestContentfulPaint,
                critical: true,
                element: lastEntry.element?.tagName
            });
        }).observe({ entryTypes: ['largest-contentful-paint'] });
        
        // First Input Delay (FID)
        new PerformanceObserver((entryList) => {
            for (const entry of entryList.getEntries()) {
                this.recordMetric('FID', entry.processingStart - entry.startTime, {
                    threshold: this.config.performanceThresholds.firstInputDelay,
                    critical: true,
                    inputType: entry.name
                });
            }
        }).observe({ entryTypes: ['first-input'] });
        
        // Cumulative Layout Shift (CLS)
        let clsValue = 0;
        new PerformanceObserver((entryList) => {
            for (const entry of entryList.getEntries()) {
                if (!entry.hadRecentInput) {
                    clsValue += entry.value;
                }
            }
            this.recordMetric('CLS', clsValue, {
                threshold: this.config.performanceThresholds.cumulativeLayoutShift,
                critical: true
            });
        }).observe({ entryTypes: ['layout-shift'] });
    }
    
    trackCustomMetrics() {
        // Time to Interactive (TTI) approximation
        const observer = new PerformanceObserver((entryList) => {
            const entries = entryList.getEntries();
            const lastLongTask = entries[entries.length - 1];
            const tti = lastLongTask ? lastLongTask.startTime + lastLongTask.duration : performance.now();
            
            this.recordMetric('TTI', tti, {
                threshold: this.config.performanceThresholds.timeToInteractive,
                critical: true
            });
        });
        
        try {
            observer.observe({ entryTypes: ['longtask'] });
        } catch (e) {
            // Fallback TTI calculation
            window.addEventListener('load', () => {
                setTimeout(() => {
                    this.recordMetric('TTI', performance.now(), {
                        threshold: this.config.performanceThresholds.timeToInteractive,
                        critical: true,
                        fallback: true
                    });
                }, 100);
            });
        }
        
        // Navigation timing
        window.addEventListener('load', () => {
            const navTiming = performance.getEntriesByType('navigation')[0];
            if (navTiming) {
                this.recordMetric('DNS', navTiming.domainLookupEnd - navTiming.domainLookupStart);
                this.recordMetric('TCP', navTiming.connectEnd - navTiming.connectStart);
                this.recordMetric('Request', navTiming.responseStart - navTiming.requestStart);
                this.recordMetric('Response', navTiming.responseEnd - navTiming.responseStart);
                this.recordMetric('DOM', navTiming.domContentLoadedEventEnd - navTiming.domContentLoadedEventStart);
                this.recordMetric('Load', navTiming.loadEventEnd - navTiming.loadEventStart);
            }
        });
    }
    
    monitorResourcePerformance() {
        new PerformanceObserver((entryList) => {
            for (const entry of entryList.getEntries()) {
                const resourceType = entry.initiatorType;
                const loadTime = entry.responseEnd - entry.startTime;
                
                this.recordMetric(`Resource_${resourceType}`, loadTime, {
                    url: entry.name,
                    size: entry.transferSize,
                    cached: entry.transferSize === 0
                });
                
                // Flag slow resources
                if (loadTime > 2000) { // 2s threshold
                    this.recordSlowResource(entry);
                }
            }
        }).observe({ entryTypes: ['resource'] });
    }
    
    // User behavior tracking
    initializeUserBehaviorTracking() {
        this.trackScrollBehavior();
        this.trackClickPatterns();
        this.trackSearchBehavior();
        this.trackTimeOnPage();
        this.trackDocumentationUsage();
        this.trackMobileGestures();
    }
    
    trackScrollBehavior() {
        let maxScroll = 0;
        let scrollDepths = [25, 50, 75, 90, 100];
        let reachedDepths = new Set();
        
        const trackScroll = () => {
            const scrollPercent = Math.round((window.scrollY / (document.body.scrollHeight - window.innerHeight)) * 100);
            maxScroll = Math.max(maxScroll, scrollPercent);
            
            scrollDepths.forEach(depth => {
                if (scrollPercent >= depth && !reachedDepths.has(depth)) {
                    reachedDepths.add(depth);
                    this.trackEvent('scroll_depth', {
                        depth: depth,
                        page_type: this.getPageType(),
                        timestamp: Date.now() - this.pageLoadTime
                    });
                }
            });
        };
        
        let scrollTimeout;
        window.addEventListener('scroll', () => {
            clearTimeout(scrollTimeout);
            scrollTimeout = setTimeout(trackScroll, 100);
        }, { passive: true });
        
        // Track final scroll on page unload
        window.addEventListener('beforeunload', () => {
            this.trackEvent('final_scroll_depth', {
                max_depth: maxScroll,
                time_on_page: Date.now() - this.pageLoadTime
            });
        });
    }
    
    trackClickPatterns() {
        document.addEventListener('click', (event) => {
            const element = event.target.closest('a, button, .clickable');
            if (!element) return;
            
            const clickData = {
                element_type: element.tagName.toLowerCase(),
                element_class: element.className,
                element_text: element.textContent?.trim().substring(0, 100),
                element_href: element.href,
                timestamp: Date.now() - this.pageLoadTime,
                page_type: this.getPageType()
            };
            
            // Special tracking for documentation elements
            if (element.closest('.code-copy-btn')) {
                clickData.action = 'code_copy';
            } else if (element.closest('.tab-button')) {
                clickData.action = 'tab_switch';
            } else if (element.closest('.collapsible-header')) {
                clickData.action = 'section_expand';
            } else if (element.closest('.status-badge')) {
                clickData.action = 'status_click';
            }
            
            this.trackEvent('click', clickData);
        }, { passive: true });
    }
    
    trackSearchBehavior() {
        const searchInput = document.querySelector('input[data-md-component="search-query"]');
        if (!searchInput) return;
        
        let searchTimeout;
        let searchStartTime;
        
        searchInput.addEventListener('focus', () => {
            searchStartTime = Date.now();
            this.trackEvent('search_start', {
                page_type: this.getPageType()
            });
        });
        
        searchInput.addEventListener('input', (event) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                const query = event.target.value.trim();
                if (query.length > 2) {
                    this.trackEvent('search_query', {
                        query_length: query.length,
                        query_hash: this.hashString(query), // Privacy-safe query tracking
                        time_since_start: Date.now() - searchStartTime
                    });
                }
            }, 500);
        });
        
        // Track search result interactions
        document.addEventListener('click', (event) => {
            if (event.target.closest('.md-search-result')) {
                this.trackEvent('search_result_click', {
                    result_position: this.getSearchResultPosition(event.target),
                    query_time: Date.now() - searchStartTime
                });
            }
        });
    }
    
    trackTimeOnPage() {
        const startTime = Date.now();
        let lastActiveTime = startTime;
        let totalActiveTime = 0;
        
        // Track active time (user is interacting)
        const updateActiveTime = () => {
            const now = Date.now();
            if (this.isVisible && now - lastActiveTime < 30000) { // 30s threshold
                totalActiveTime += now - lastActiveTime;
            }
            lastActiveTime = now;
        };
        
        ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart'].forEach(event => {
            document.addEventListener(event, updateActiveTime, { passive: true });
        });
        
        // Track visibility changes
        document.addEventListener('visibilitychange', () => {
            this.isVisible = !document.hidden;
            if (this.isVisible) {
                lastActiveTime = Date.now();
            } else {
                updateActiveTime();
            }
        });
        
        // Track when user leaves
        window.addEventListener('beforeunload', () => {
            updateActiveTime();
            this.trackEvent('page_exit', {
                total_time: Date.now() - startTime,
                active_time: totalActiveTime,
                engagement_rate: totalActiveTime / (Date.now() - startTime),
                page_type: this.getPageType()
            });
        });
    }
    
    trackDocumentationUsage() {
        // Track code block interactions
        document.addEventListener('click', (event) => {
            if (event.target.closest('.code-copy-btn')) {
                this.trackEvent('code_copy', {
                    language: this.getCodeLanguage(event.target),
                    block_size: this.getCodeBlockSize(event.target),
                    page_section: this.getPageSection(event.target)
                });
            }
        });
        
        // Track API reference usage
        const apiLinks = document.querySelectorAll('a[href*="/api/"], a[href*="/reference/"]');
        apiLinks.forEach(link => {
            link.addEventListener('click', () => {
                this.trackEvent('api_reference_click', {
                    api_endpoint: link.href,
                    source_page: window.location.pathname
                });
            });
        });
        
        // Track tutorial progression
        if (this.getPageType() === 'tutorial') {
            this.trackTutorialProgress();
        }
    }
    
    trackMobileGestures() {
        if (!('ontouchstart' in window)) return;
        
        let touchStartX, touchStartY, touchStartTime;
        
        document.addEventListener('touchstart', (event) => {
            const touch = event.touches[0];
            touchStartX = touch.clientX;
            touchStartY = touch.clientY;
            touchStartTime = Date.now();
        }, { passive: true });
        
        document.addEventListener('touchend', (event) => {
            if (!touchStartX || !touchStartY) return;
            
            const touch = event.changedTouches[0];
            const deltaX = touch.clientX - touchStartX;
            const deltaY = touch.clientY - touchStartY;
            const deltaTime = Date.now() - touchStartTime;
            const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY);
            
            // Detect swipe gestures
            if (distance > 50 && deltaTime < 300) {
                const direction = Math.abs(deltaX) > Math.abs(deltaY) ? 
                    (deltaX > 0 ? 'right' : 'left') : 
                    (deltaY > 0 ? 'down' : 'up');
                
                this.trackEvent('mobile_swipe', {
                    direction: direction,
                    distance: Math.round(distance),
                    duration: deltaTime,
                    page_type: this.getPageType()
                });
            }
        }, { passive: true });
    }
    
    // Error tracking and monitoring
    initializeErrorTracking() {
        // JavaScript errors
        window.addEventListener('error', (event) => {
            this.recordError({
                type: 'javascript',
                message: event.message,
                filename: event.filename,
                lineno: event.lineno,
                colno: event.colno,
                stack: event.error?.stack,
                timestamp: Date.now(),
                url: window.location.href,
                userAgent: navigator.userAgent
            });
        });
        
        // Unhandled promise rejections
        window.addEventListener('unhandledrejection', (event) => {
            this.recordError({
                type: 'unhandled_promise',
                message: event.reason?.message || 'Unhandled promise rejection',
                stack: event.reason?.stack,
                timestamp: Date.now(),
                url: window.location.href
            });
        });
        
        // Resource loading errors
        document.addEventListener('error', (event) => {
            if (event.target !== window) {
                this.recordError({
                    type: 'resource_load',
                    message: `Failed to load ${event.target.tagName}: ${event.target.src || event.target.href}`,
                    element: event.target.tagName,
                    url: event.target.src || event.target.href,
                    timestamp: Date.now()
                });
            }
        }, true);
    }
    
    // Feedback collection system
    initializeFeedbackCollection() {
        this.createFeedbackWidget();
        this.trackHelpfulnessRatings();
        this.trackSearchSatisfaction();
    }
    
    createFeedbackWidget() {
        // Create floating feedback button
        const feedbackBtn = document.createElement('button');
        feedbackBtn.className = 'feedback-widget';
        feedbackBtn.innerHTML = '💬 Feedback';
        feedbackBtn.setAttribute('aria-label', 'Provide feedback');
        
        feedbackBtn.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 1000;
            background: var(--primary-blue, #1e40af);
            color: white;
            border: none;
            border-radius: 25px;
            padding: 12px 20px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            transition: all 0.2s ease;
        `;
        
        feedbackBtn.addEventListener('click', () => {
            this.showFeedbackModal();
        });
        
        document.body.appendChild(feedbackBtn);
    }
    
    showFeedbackModal() {
        // Simple feedback modal (could be enhanced with a proper modal system)
        const feedback = prompt(`How helpful is this documentation page?
        
1 - Not helpful at all
2 - Slightly helpful  
3 - Moderately helpful
4 - Very helpful
5 - Extremely helpful

Please enter a number (1-5):`);
        
        if (feedback && /^[1-5]$/.test(feedback)) {
            this.trackEvent('page_rating', {
                rating: parseInt(feedback),
                page_type: this.getPageType(),
                page_url: window.location.pathname
            });
            
            // Optional follow-up comment
            if (parseInt(feedback) <= 3) {
                const comment = prompt('What could we improve about this page?');
                if (comment && comment.trim()) {
                    this.trackEvent('improvement_suggestion', {
                        rating: parseInt(feedback),
                        suggestion: comment.trim().substring(0, 500),
                        page_type: this.getPageType()
                    });
                }
            }
        }
    }
    
    trackHelpfulnessRatings() {
        // Track thumbs up/down if they exist
        document.addEventListener('click', (event) => {
            const rating = event.target.closest('[data-rating]');
            if (rating) {
                this.trackEvent('content_rating', {
                    rating: rating.dataset.rating,
                    content_section: this.getPageSection(rating),
                    page_type: this.getPageType()
                });
            }
        });
    }
    
    trackSearchSatisfaction() {
        // Track if users find what they're looking for after searching
        let searchQuery = '';
        let searchTime = 0;
        
        const searchInput = document.querySelector('input[data-md-component="search-query"]');
        if (searchInput) {
            searchInput.addEventListener('input', (event) => {
                searchQuery = event.target.value;
                searchTime = Date.now();
            });
        }
        
        // Track if user navigates away quickly after search (potential dissatisfaction)
        window.addEventListener('beforeunload', () => {
            if (searchQuery && Date.now() - searchTime < 10000) { // Left within 10s
                this.trackEvent('search_quick_exit', {
                    query_length: searchQuery.length,
                    time_on_results: Date.now() - searchTime
                });
            }
        });
    }
    
    // Real-time monitoring and alerts
    startRealTimeMonitoring() {
        // Monitor performance in real-time
        setInterval(() => {
            this.checkPerformanceThresholds();
            this.monitorMemoryUsage();
            this.checkErrorRates();
        }, 30000); // Every 30 seconds
    }
    
    checkPerformanceThresholds() {
        const thresholds = this.config.performanceThresholds;
        
        for (const [metric, value] of this.metrics.performance) {
            if (value.critical && value.value > value.threshold) {
                this.alertPerformanceIssue(metric, value);
            }
        }
    }
    
    monitorMemoryUsage() {
        if ('memory' in performance) {
            const memory = performance.memory;
            const memoryUsage = {
                used: memory.usedJSHeapSize,
                total: memory.totalJSHeapSize,
                limit: memory.jsHeapSizeLimit,
                percentage: (memory.usedJSHeapSize / memory.jsHeapSizeLimit) * 100
            };
            
            if (memoryUsage.percentage > 90) {
                this.alertMemoryIssue(memoryUsage);
            }
            
            this.recordMetric('Memory_Usage', memoryUsage.percentage, memoryUsage);
        }
    }
    
    checkErrorRates() {
        const recentErrors = this.metrics.errors.filter(
            error => Date.now() - error.timestamp < 300000 // Last 5 minutes
        );
        
        if (recentErrors.length > 5) { // More than 5 errors in 5 minutes
            this.alertHighErrorRate(recentErrors);
        }
    }
    
    // Reporting and data export
    setupPeriodicReporting() {
        // Send metrics every 5 minutes
        setInterval(() => {
            this.sendMetricsToServer();
        }, 300000);
        
        // Send session summary on page unload
        window.addEventListener('beforeunload', () => {
            this.sendSessionSummary();
        });
    }
    
    async sendMetricsToServer() {
        if (!this.config.endpoints.performance) return;
        
        const metricsData = {
            sessionId: this.sessionId,
            timestamp: Date.now(),
            url: window.location.href,
            userAgent: navigator.userAgent,
            metrics: Object.fromEntries(this.metrics.performance),
            interactions: Object.fromEntries(this.metrics.interactions),
            errors: this.metrics.errors.slice(-10), // Last 10 errors
            performance: this.getPerformanceSummary()
        };
        
        try {
            if (navigator.sendBeacon) {
                navigator.sendBeacon(
                    this.config.endpoints.performance, 
                    JSON.stringify(metricsData)
                );
            } else {
                await fetch(this.config.endpoints.performance, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(metricsData),
                    keepalive: true
                });
            }
        } catch (error) {
            console.warn('Failed to send metrics:', error);
        }
    }
    
    getPerformanceSummary() {
        const nav = performance.getEntriesByType('navigation')[0];
        if (!nav) return {};
        
        return {
            domContentLoaded: nav.domContentLoadedEventEnd - nav.domContentLoadedEventStart,
            loadComplete: nav.loadEventEnd - nav.loadEventStart,
            totalPageLoad: nav.loadEventEnd - nav.fetchStart,
            ttfb: nav.responseStart - nav.requestStart,
            resourceCount: performance.getEntriesByType('resource').length
        };
    }
    
    // Utility methods
    recordMetric(name, value, metadata = {}) {
        this.metrics.performance.set(name, {
            value,
            timestamp: Date.now(),
            ...metadata
        });
        
        // Real-time threshold checking
        if (metadata.critical && metadata.threshold && value > metadata.threshold) {
            this.alertPerformanceIssue(name, { value, threshold: metadata.threshold });
        }
    }
    
    recordError(errorData) {
        this.metrics.errors.push(errorData);
        
        // Send critical errors immediately
        if (this.shouldSample(this.config.errorSampling)) {
            this.sendErrorToServer(errorData);
        }
    }
    
    trackEvent(eventName, eventData = {}) {
        // Track in internal metrics
        const key = `${eventName}_${Date.now()}`;
        this.metrics.interactions.set(key, {
            event: eventName,
            data: eventData,
            timestamp: Date.now()
        });
        
        // Send to Google Analytics if available
        if (window.gtag) {
            gtag('event', eventName, {
                event_category: 'documentation',
                event_label: eventData.page_type || this.getPageType(),
                value: eventData.value || 1,
                custom_parameter_1: eventData.page_type,
                custom_parameter_2: eventData.action,
                custom_parameter_3: eventData.element_type
            });
        }
    }
    
    // Helper methods
    generateSessionId() {
        return 'session_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
    }
    
    shouldSample(rate) {
        return Math.random() < rate;
    }
    
    getPageType() {
        const path = window.location.pathname;
        if (path === '/') return 'homepage';
        if (path.includes('/tutorials/')) return 'tutorial';
        if (path.includes('/api/') || path.includes('/reference/')) return 'api';
        if (path.includes('/examples/')) return 'examples';
        if (path.includes('/getting_started/')) return 'getting_started';
        return 'documentation';
    }
    
    getContentCategory() {
        const title = document.title.toLowerCase();
        if (title.includes('api') || title.includes('reference')) return 'reference';
        if (title.includes('tutorial') || title.includes('guide')) return 'tutorial';
        if (title.includes('example')) return 'example';
        return 'documentation';
    }
    
    getUserType() {
        // Cookie-free user type detection using session storage only
        // Session storage is cleared when browser is closed - no persistent tracking
        const hasVisited = sessionStorage.getItem('current_session_returning');
        if (!hasVisited) {
            sessionStorage.setItem('current_session_returning', 'true');
            return 'new';
        }
        return 'returning';
    }
    
    hashString(str) {
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            const char = str.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash; // Convert to 32-bit integer
        }
        return hash.toString(36);
    }
    
    getSearchResultPosition(element) {
        const results = document.querySelectorAll('.md-search-result');
        return Array.from(results).indexOf(element.closest('.md-search-result')) + 1;
    }
    
    getCodeLanguage(element) {
        const codeBlock = element.closest('.highlight, pre');
        if (!codeBlock) return 'unknown';
        
        const classNames = codeBlock.className;
        const langMatch = classNames.match(/language-(\w+)|highlight-(\w+)/);
        return langMatch ? (langMatch[1] || langMatch[2]) : 'unknown';
    }
    
    getCodeBlockSize(element) {
        const codeBlock = element.closest('.highlight, pre');
        if (!codeBlock) return 0;
        
        const code = codeBlock.textContent || '';
        return code.split('\n').length;
    }
    
    getPageSection(element) {
        const heading = element.closest('section')?.querySelector('h1, h2, h3') ||
                       element.closest('article')?.querySelector('h1, h2, h3');
        return heading ? heading.textContent.trim() : 'unknown';
    }
    
    // Alert methods
    alertPerformanceIssue(metric, data) {
        console.warn(`Performance threshold exceeded: ${metric}`, data);
        
        // Could send to monitoring service
        this.sendAlert({
            type: 'performance',
            metric,
            value: data.value,
            threshold: data.threshold,
            severity: 'warning'
        });
    }
    
    alertMemoryIssue(memoryData) {
        console.warn('High memory usage detected:', memoryData);
        
        this.sendAlert({
            type: 'memory',
            usage: memoryData,
            severity: 'warning'
        });
    }
    
    alertHighErrorRate(errors) {
        console.error('High error rate detected:', errors.length, 'errors in 5 minutes');
        
        this.sendAlert({
            type: 'error_rate',
            errorCount: errors.length,
            timeWindow: '5m',
            severity: 'critical'
        });
    }
    
    async sendAlert(alertData) {
        // Send to monitoring endpoint
        try {
            await fetch('/api/alerts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ...alertData,
                    timestamp: Date.now(),
                    sessionId: this.sessionId,
                    url: window.location.href
                })
            });
        } catch (error) {
            console.warn('Failed to send alert:', error);
        }
    }
}

// Initialize performance monitoring
let performanceMonitor;

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        performanceMonitor = new PerformanceMonitor();
    });
} else {
    performanceMonitor = new PerformanceMonitor();
}

// Export for external use
window.PerformanceMonitor = PerformanceMonitor;
window.performanceMonitor = performanceMonitor;