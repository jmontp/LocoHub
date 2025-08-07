// Synchronized tab switching for Library vs Raw Data code examples
document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on a tutorial page
    const isTutorialPage = window.location.pathname.includes('/tutorials/');
    if (!isTutorialPage) return;

    // Get saved preference or default to 'library'
    let currentMode = localStorage.getItem('codeMode') || 'library';

    // Add CSS for better tab styling
    const style = document.createElement('style');
    style.textContent = `
        /* Enhanced tab styling */
        .tabbed-set {
            margin: 20px 0;
        }

        .tabbed-labels {
            border-bottom: 2px solid #e0e0e0;
            margin-bottom: 0;
        }

        [data-md-color-scheme="slate"] .tabbed-labels {
            border-bottom-color: #404040;
        }

        .tabbed-set label {
            padding: 10px 20px !important;
            font-weight: 500;
            color: #666;
            cursor: pointer;
            transition: all 0.2s ease;
            border-radius: 8px 8px 0 0;
            margin-right: 4px;
        }

        [data-md-color-scheme="slate"] .tabbed-set label {
            color: #aaa;
        }

        .tabbed-set label:hover {
            background: rgba(21, 101, 192, 0.1);
            color: #1565c0;
        }

        [data-md-color-scheme="slate"] .tabbed-set label:hover {
            background: rgba(21, 101, 192, 0.2);
            color: #42a5f5;
        }

        .tabbed-set input:checked + label {
            background: #1565c0 !important;
            color: white !important;
            font-weight: 600;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        [data-md-color-scheme="slate"] .tabbed-set input:checked + label {
            background: #42a5f5 !important;
            color: #000 !important;
        }

    `;
    document.head.appendChild(style);

    // Function to sync all tabs
    function syncAllTabs(targetLabel) {
        // Find all tab sets
        document.querySelectorAll('.tabbed-set').forEach(tabbedSet => {
            // Find the matching label in this set
            const labels = tabbedSet.querySelectorAll('label');
            labels.forEach(label => {
                if (label.textContent.trim() === targetLabel) {
                    // Click the label to trigger native behavior and visual update
                    const radioId = label.getAttribute('for');
                    const radio = document.getElementById(radioId);
                    if (radio && !radio.checked) {
                        radio.checked = true;
                        // Trigger change event for proper update
                        radio.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                }
            });
        });

        // Save preference
        const mode = targetLabel === 'Using Library' ? 'library' : 'raw';
        localStorage.setItem('codeMode', mode);
    }

    // Apply saved preference on load
    const initialLabel = currentMode === 'library' ? 'Using Library' : 'Using Raw Data';
    setTimeout(() => syncAllTabs(initialLabel), 100);

    // Listen for tab clicks and sync all tabs
    document.addEventListener('click', function(e) {
        // Check if a tab label was clicked
        if (e.target.tagName === 'LABEL' && e.target.closest('.tabbed-set')) {
            const clickedText = e.target.textContent.trim();
            if (clickedText === 'Using Library' || clickedText === 'Using Raw Data') {
                // Small delay to let the clicked tab update first
                setTimeout(() => syncAllTabs(clickedText), 10);
            }
        }
    }, true); // Use capture phase to get the event before default handling
});