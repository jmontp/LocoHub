// Global toggle for Library vs Raw Data code examples
document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on a tutorial page
    const isTutorialPage = window.location.pathname.includes('/tutorials/');
    if (!isTutorialPage) return;

    // Get saved preference or default to 'library'
    let currentMode = localStorage.getItem('codeMode') || 'library';

    // Create toggle button
    const toggleContainer = document.createElement('div');
    toggleContainer.className = 'code-toggle-container';
    toggleContainer.innerHTML = `
        <div class="code-toggle-wrapper">
            <span class="toggle-label">Code Style:</span>
            <button class="code-toggle-btn" id="codeToggle">
                <span class="toggle-icon">📚</span>
                <span class="toggle-text">${currentMode === 'library' ? 'Using Library' : 'Using Raw Data'}</span>
            </button>
        </div>
        <div class="toggle-hint">Click to switch all code examples</div>
    `;

    // Add CSS styles
    const style = document.createElement('style');
    style.textContent = `
        .code-toggle-container {
            position: sticky;
            top: 70px;
            z-index: 100;
            background: linear-gradient(to bottom, rgba(255,255,255,1) 0%, rgba(255,255,255,0.95) 100%);
            padding: 15px 20px;
            margin: 20px 0;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border: 1px solid #e0e0e0;
        }

        [data-md-color-scheme="slate"] .code-toggle-container {
            background: linear-gradient(to bottom, rgba(30,30,30,1) 0%, rgba(30,30,30,0.95) 100%);
            border-color: #404040;
        }

        .code-toggle-wrapper {
            display: flex;
            align-items: center;
            gap: 15px;
        }

        .toggle-label {
            font-weight: 600;
            color: #666;
            font-size: 14px;
        }

        [data-md-color-scheme="slate"] .toggle-label {
            color: #aaa;
        }

        .code-toggle-btn {
            background: #1565c0;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 8px;
            transition: all 0.3s ease;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .code-toggle-btn:hover {
            background: #0d47a1;
            transform: translateY(-1px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }

        .code-toggle-btn:active {
            transform: translateY(0);
        }

        .toggle-icon {
            font-size: 16px;
        }

        .toggle-hint {
            font-size: 12px;
            color: #999;
            margin-top: 5px;
        }

        [data-md-color-scheme="slate"] .toggle-hint {
            color: #666;
        }

        /* Highlight active tab */
        .tabbed-set input:checked + label {
            font-weight: 600;
        }
    `;
    document.head.appendChild(style);

    // Find the first h1 or h2 on the page and insert toggle after it
    const firstHeading = document.querySelector('article h1, article h2');
    if (firstHeading) {
        firstHeading.parentNode.insertBefore(toggleContainer, firstHeading.nextSibling);
    }

    // Function to switch all tabs
    function switchAllTabs(mode) {
        const targetLabel = mode === 'library' ? 'Using Library' : 'Using Raw Data';
        
        // Find all tab labels
        const allTabLabels = document.querySelectorAll('.tabbed-set label');
        
        allTabLabels.forEach(label => {
            if (label.textContent.trim() === targetLabel) {
                // Find the associated radio input and check it
                const radioId = label.getAttribute('for');
                const radio = document.getElementById(radioId);
                if (radio) {
                    radio.checked = true;
                }
            }
        });

        // Update button text and icon
        const btn = document.getElementById('codeToggle');
        const icon = mode === 'library' ? '📚' : '🔧';
        const text = mode === 'library' ? 'Using Library' : 'Using Raw Data';
        btn.querySelector('.toggle-icon').textContent = icon;
        btn.querySelector('.toggle-text').textContent = text;

        // Save preference
        localStorage.setItem('codeMode', mode);
    }

    // Apply saved preference on load
    switchAllTabs(currentMode);

    // Add click handler to toggle button
    document.getElementById('codeToggle').addEventListener('click', function() {
        currentMode = currentMode === 'library' ? 'raw' : 'library';
        switchAllTabs(currentMode);
    });

    // Also sync tabs when user clicks on any tab directly
    document.addEventListener('change', function(e) {
        if (e.target.type === 'radio' && e.target.name && e.target.name.startsWith('__tabbed_')) {
            const label = document.querySelector(`label[for="${e.target.id}"]`);
            if (label) {
                const text = label.textContent.trim();
                if (text === 'Using Library') {
                    currentMode = 'library';
                    switchAllTabs('library');
                } else if (text === 'Using Raw Data') {
                    currentMode = 'raw';
                    switchAllTabs('raw');
                }
            }
        }
    });
});