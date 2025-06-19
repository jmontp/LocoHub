/**
 * User Routing and Navigation Helpers
 * Provides intelligent routing based on user intent and behavior
 */

document.addEventListener('DOMContentLoaded', function() {
    
    // Track user interactions for better routing suggestions
    const userBehavior = {
        visitedPages: [],
        timeOnPage: Date.now(),
        interactions: []
    };

    // Initialize user routing
    initializeUserRouting();
    
    function initializeUserRouting() {
        // Add user journey tracking
        trackUserJourney();
        
        // Add smart navigation suggestions
        addNavigationSuggestions();
        
        // Add breadcrumb enhancements
        enhanceBreadcrumbs();
        
        // Add "What's Next" suggestions
        addWhatsNextSuggestions();
        
        // Add cross-references
        addCrossReferences();
    }

    /**
     * Track user journey for better recommendations
     */
    function trackUserJourney() {
        // Track page visits
        const currentPage = window.location.pathname;
        userBehavior.visitedPages.push(currentPage);
        
        // Track time spent on pages
        window.addEventListener('beforeunload', function() {
            const timeSpent = Date.now() - userBehavior.timeOnPage;
            console.log(`Time spent on ${currentPage}: ${timeSpent}ms`);
        });
        
        // Track interactions with route cards
        document.querySelectorAll('.route-card, .role-card, .ref-card').forEach(card => {
            card.addEventListener('click', function() {
                const cardType = this.className.split(' ').find(cls => 
                    ['analyze', 'learn', 'contribute', 'develop', 'researcher', 'clinician', 'data-scientist', 'lab-director'].includes(cls)
                );
                userBehavior.interactions.push({
                    type: 'card_click',
                    target: cardType,
                    timestamp: Date.now()
                });
            });
        });
    }

    /**
     * Add smart navigation suggestions based on current page
     */
    function addNavigationSuggestions() {
        const currentPath = window.location.pathname;
        let suggestions = [];
        
        // Determine suggestions based on current page
        if (currentPath.includes('/getting_started/')) {
            suggestions = [
                { text: 'Try a Tutorial', url: '/tutorials/basic/load_explore/', icon: 'school' },
                { text: 'Browse Examples', url: '/examples/', icon: 'eye' },
                { text: 'API Reference', url: '/reference/api/python/', icon: 'code-braces' }
            ];
        } else if (currentPath.includes('/tutorials/')) {
            suggestions = [
                { text: 'Real Examples', url: '/examples/', icon: 'play-circle' },
                { text: 'User Guides', url: '/user_guides/', icon: 'account-group' },
                { text: 'Get Help', url: '/user_guides/researchers/getting_data/#troubleshooting', icon: 'help-circle' }
            ];
        } else if (currentPath.includes('/examples/')) {
            suggestions = [
                { text: 'Learn More', url: '/tutorials/', icon: 'school' },
                { text: 'API Reference', url: '/reference/', icon: 'book-open' },
                { text: 'Contribute', url: '/contributing/', icon: 'heart' }
            ];
        } else if (currentPath.includes('/reference/')) {
            suggestions = [
                { text: 'See Examples', url: '/examples/', icon: 'play-circle' },
                { text: 'Tutorials', url: '/tutorials/', icon: 'school' },
                { text: 'Get Started', url: '/getting_started/', icon: 'rocket-launch' }
            ];
        }
        
        // Add suggestions to the page if any exist
        if (suggestions.length > 0) {
            addSuggestionsToPage(suggestions);
        }
    }

    /**
     * Add suggestion box to the page
     */
    function addSuggestionsToPage(suggestions) {
        // Check if suggestions already exist
        if (document.querySelector('.navigation-suggestions')) return;
        
        const suggestionsHTML = `
            <div class="navigation-suggestions">
                <h4><i class="material-icons">lightbulb</i> What's Next?</h4>
                <div class="suggestions-list">
                    ${suggestions.map(suggestion => `
                        <a href="${suggestion.url}" class="suggestion-item">
                            <i class="material-icons">${suggestion.icon}</i>
                            <span>${suggestion.text}</span>
                        </a>
                    `).join('')}
                </div>
            </div>
        `;
        
        // Add to the end of the main content
        const mainContent = document.querySelector('article') || document.querySelector('main');
        if (mainContent) {
            mainContent.insertAdjacentHTML('beforeend', suggestionsHTML);
        }
    }

    /**
     * Enhance breadcrumbs with context
     */
    function enhanceBreadcrumbs() {
        const breadcrumbs = document.querySelector('.md-nav__list');
        if (!breadcrumbs) return;
        
        // Add context to breadcrumbs
        const currentPath = window.location.pathname;
        let context = '';
        
        if (currentPath.includes('/getting_started/')) {
            context = 'Getting Started Path';
        } else if (currentPath.includes('/tutorials/basic/')) {
            context = 'Beginner Tutorial Path';
        } else if (currentPath.includes('/tutorials/advanced/')) {
            context = 'Advanced Tutorial Path';
        } else if (currentPath.includes('/user_guides/researchers/')) {
            context = 'Researcher Workflow';
        } else if (currentPath.includes('/user_guides/clinicians/')) {
            context = 'Clinical Applications';
        }
        
        if (context) {
            const contextElement = document.createElement('div');
            contextElement.className = 'breadcrumb-context';
            contextElement.innerHTML = `<small><i class="material-icons">map</i> ${context}</small>`;
            breadcrumbs.insertBefore(contextElement, breadcrumbs.firstChild);
        }
    }

    /**
     * Add "What's Next" suggestions at the end of pages
     */
    function addWhatsNextSuggestions() {
        const currentPath = window.location.pathname;
        let nextSteps = [];
        
        // Define next steps based on page type
        if (currentPath.includes('/getting_started/installation')) {
            nextSteps = [
                'Try the Quick Start guide',
                'Load your first dataset',
                'Create your first visualization'
            ];
        } else if (currentPath.includes('/getting_started/quick_start')) {
            nextSteps = [
                'Explore more tutorials',
                'Try a real-world example',
                'Check out user guides for your role'
            ];
        } else if (currentPath.includes('/tutorials/basic/')) {
            nextSteps = [
                'Try an advanced tutorial',
                'Explore real examples',
                'Apply to your own data'
            ];
        }
        
        if (nextSteps.length > 0) {
            addNextStepsToPage(nextSteps);
        }
    }

    /**
     * Add next steps box to page
     */
    function addNextStepsToPage(steps) {
        const nextStepsHTML = `
            <div class="next-steps">
                <h4><i class="material-icons">arrow-forward</i> What's Next?</h4>
                <ul>
                    ${steps.map(step => `<li>${step}</li>`).join('')}
                </ul>
            </div>
        `;
        
        const mainContent = document.querySelector('article') || document.querySelector('main');
        if (mainContent) {
            mainContent.insertAdjacentHTML('beforeend', nextStepsHTML);
        }
    }

    /**
     * Add cross-references to related content
     */
    function addCrossReferences() {
        const currentPath = window.location.pathname;
        let relatedContent = [];
        
        // Define related content based on current page
        if (currentPath.includes('/tutorials/')) {
            relatedContent = [
                { title: 'Real Examples', url: '/examples/', type: 'examples' },
                { title: 'API Reference', url: '/reference/api/python/', type: 'reference' },
                { title: 'User Guides', url: '/user_guides/', type: 'guides' }
            ];
        } else if (currentPath.includes('/examples/')) {
            relatedContent = [
                { title: 'Learn with Tutorials', url: '/tutorials/', type: 'tutorials' },
                { title: 'Technical Reference', url: '/reference/', type: 'reference' },
                { title: 'Get Started', url: '/getting_started/', type: 'getting-started' }
            ];
        }
        
        if (relatedContent.length > 0) {
            addRelatedContentToPage(relatedContent);
        }
    }

    /**
     * Add related content links
     */
    function addRelatedContentToPage(content) {
        const relatedHTML = `
            <div class="related-content">
                <h4><i class="material-icons">link</i> Related Content</h4>
                <div class="related-links">
                    ${content.map(item => `
                        <a href="${item.url}" class="related-link ${item.type}">
                            <span>${item.title}</span>
                        </a>
                    `).join('')}
                </div>
            </div>
        `;
        
        const mainContent = document.querySelector('article') || document.querySelector('main');
        if (mainContent) {
            mainContent.insertAdjacentHTML('beforeend', relatedHTML);
        }
    }

    /**
     * Add smart search suggestions
     */
    function addSmartSearch() {
        const searchInput = document.querySelector('.md-search__input');
        if (!searchInput) return;
        
        // Add search suggestions based on current context
        const currentPath = window.location.pathname;
        let searchSuggestions = [];
        
        if (currentPath.includes('/getting_started/')) {
            searchSuggestions = ['load data', 'first analysis', 'installation', 'quick start'];
        } else if (currentPath.includes('/tutorials/')) {
            searchSuggestions = ['basic tutorial', 'advanced workflow', 'examples', 'plotting'];
        } else if (currentPath.includes('/reference/')) {
            searchSuggestions = ['API documentation', 'function reference', 'data format', 'validation'];
        }
        
        // Add datalist for search suggestions
        if (searchSuggestions.length > 0) {
            const datalist = document.createElement('datalist');
            datalist.id = 'search-suggestions';
            searchSuggestions.forEach(suggestion => {
                const option = document.createElement('option');
                option.value = suggestion;
                datalist.appendChild(option);
            });
            searchInput.setAttribute('list', 'search-suggestions');
            searchInput.parentNode.appendChild(datalist);
        }
    }

    // Initialize smart search
    addSmartSearch();

    /**
     * Add progress indicators for tutorial paths
     */
    function addProgressIndicators() {
        const currentPath = window.location.pathname;
        
        // Define tutorial sequences
        const tutorialPaths = {
            basic: [
                '/tutorials/basic/load_explore/',
                '/tutorials/basic/filter_select/',
                '/tutorials/basic/visualizations/',
                '/tutorials/basic/metrics/'
            ],
            advanced: [
                '/tutorials/advanced/multi_dataset/',
                '/tutorials/advanced/custom_plots/',
                '/tutorials/advanced/statistics/',
                '/tutorials/advanced/automation/'
            ],
            getting_started: [
                '/getting_started/installation/',
                '/getting_started/quick_start/',
                '/getting_started/first_analysis/'
            ]
        };
        
        // Find current position in any tutorial path
        for (const [pathName, steps] of Object.entries(tutorialPaths)) {
            const currentIndex = steps.findIndex(step => currentPath.includes(step));
            if (currentIndex !== -1) {
                addProgressBar(pathName, steps, currentIndex);
                break;
            }
        }
    }

    /**
     * Add progress bar for tutorial sequence
     */
    function addProgressBar(pathName, steps, currentIndex) {
        const progressHTML = `
            <div class="tutorial-progress">
                <div class="progress-header">
                    <h4>${pathName.charAt(0).toUpperCase() + pathName.slice(1)} Tutorial Progress</h4>
                    <span class="progress-text">${currentIndex + 1} of ${steps.length}</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${((currentIndex + 1) / steps.length) * 100}%"></div>
                </div>
                <div class="progress-steps">
                    ${steps.map((step, index) => `
                        <div class="progress-step ${index <= currentIndex ? 'completed' : ''} ${index === currentIndex ? 'current' : ''}">
                            <div class="step-number">${index + 1}</div>
                            <div class="step-name">${getStepName(step)}</div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
        
        // Add to top of page
        const mainContent = document.querySelector('article') || document.querySelector('main');
        if (mainContent) {
            mainContent.insertAdjacentHTML('afterbegin', progressHTML);
        }
    }

    /**
     * Extract step name from URL
     */
    function getStepName(url) {
        const parts = url.split('/');
        const stepName = parts[parts.length - 2] || parts[parts.length - 1];
        return stepName.replace(/_/g, ' ').replace(/-/g, ' ').toLowerCase();
    }

    // Add progress indicators
    addProgressIndicators();

    // Add keyboard shortcuts for navigation
    document.addEventListener('keydown', function(e) {
        // Alt + N for "What's Next"
        if (e.altKey && e.key === 'n') {
            const nextButton = document.querySelector('.suggestion-item, .md-button--primary');
            if (nextButton) {
                nextButton.click();
            }
        }
        
        // Alt + H for help/troubleshooting
        if (e.altKey && e.key === 'h') {
            const helpLinks = document.querySelectorAll('a[href*="troubleshooting"], a[href*="help"]');
            if (helpLinks.length > 0) {
                helpLinks[0].click();
            }
        }
    });

    // Add keyboard shortcut indicators
    const shortcutHelp = document.createElement('div');
    shortcutHelp.className = 'keyboard-shortcuts';
    shortcutHelp.innerHTML = `
        <small>
            <strong>Keyboard shortcuts:</strong> 
            Alt+N (Next step) | Alt+H (Help)
        </small>
    `;
    shortcutHelp.style.cssText = `
        position: fixed;
        bottom: 10px;
        right: 10px;
        background: rgba(0,0,0,0.8);
        color: white;
        padding: 5px 10px;
        border-radius: 4px;
        font-size: 0.8rem;
        z-index: 1000;
        opacity: 0.7;
    `;
    document.body.appendChild(shortcutHelp);
    
    // Hide shortcut help after 5 seconds
    setTimeout(() => {
        if (shortcutHelp.parentNode) {
            shortcutHelp.style.opacity = '0';
            setTimeout(() => {
                if (shortcutHelp.parentNode) {
                    shortcutHelp.parentNode.removeChild(shortcutHelp);
                }
            }, 500);
        }
    }, 5000);
});

// Add CSS for new elements
const style = document.createElement('style');
style.textContent = `
    .navigation-suggestions, .next-steps, .related-content {
        background: #f8fafc;
        border: 1px solid #e5e7eb;
        border-radius: 0.5rem;
        padding: 1.5rem;
        margin: 2rem 0;
    }
    
    .navigation-suggestions h4, .next-steps h4, .related-content h4 {
        margin: 0 0 1rem 0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .suggestions-list, .related-links {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
    }
    
    .suggestion-item, .related-link {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 1rem;
        background: white;
        border: 1px solid #d1d5db;
        border-radius: 0.25rem;
        text-decoration: none;
        transition: all 0.2s ease;
    }
    
    .suggestion-item:hover, .related-link:hover {
        background: #3b82f6;
        color: white;
        transform: translateY(-1px);
    }
    
    .breadcrumb-context {
        padding: 0.5rem 0;
        color: #6b7280;
        border-bottom: 1px solid #e5e7eb;
        margin-bottom: 1rem;
    }
    
    .tutorial-progress {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 0.5rem;
        padding: 1.5rem;
        margin: 0 0 2rem 0;
    }
    
    .progress-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
    }
    
    .progress-bar {
        width: 100%;
        height: 8px;
        background: #e5e7eb;
        border-radius: 4px;
        overflow: hidden;
        margin-bottom: 1rem;
    }
    
    .progress-fill {
        height: 100%;
        background: #3b82f6;
        transition: width 0.3s ease;
    }
    
    .progress-steps {
        display: flex;
        gap: 1rem;
        overflow-x: auto;
    }
    
    .progress-step {
        display: flex;
        flex-direction: column;
        align-items: center;
        min-width: 80px;
        text-align: center;
    }
    
    .step-number {
        width: 24px;
        height: 24px;
        border-radius: 50%;
        background: #e5e7eb;
        color: #6b7280;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.8rem;
        font-weight: bold;
        margin-bottom: 0.5rem;
    }
    
    .progress-step.completed .step-number {
        background: #22c55e;
        color: white;
    }
    
    .progress-step.current .step-number {
        background: #3b82f6;
        color: white;
    }
    
    .step-name {
        font-size: 0.7rem;
        color: #6b7280;
        text-transform: capitalize;
    }
    
    @media (max-width: 768px) {
        .suggestions-list, .related-links {
            flex-direction: column;
        }
        
        .progress-steps {
            flex-direction: column;
            gap: 0.5rem;
        }
        
        .progress-step {
            flex-direction: row;
            min-width: auto;
            text-align: left;
        }
        
        .step-number {
            margin-bottom: 0;
            margin-right: 0.5rem;
        }
    }
`;
document.head.appendChild(style);