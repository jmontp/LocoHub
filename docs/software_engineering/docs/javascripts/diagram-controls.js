// Enhanced Interactive Mermaid Diagram Controls
document.addEventListener('DOMContentLoaded', function() {
    
    // Add enhanced controls to each mermaid diagram
    function addDiagramControls() {
        const mermaidDiagrams = document.querySelectorAll('.mermaid');
        
        mermaidDiagrams.forEach(function(diagram) {
            // Skip if controls already added
            if (diagram.querySelector('.diagram-controls')) {
                return;
            }
            
            // Create controls container
            const controls = document.createElement('div');
            controls.className = 'diagram-controls';
            
            // Fullscreen button
            const fullscreenBtn = document.createElement('button');
            fullscreenBtn.className = 'diagram-control-btn';
            fullscreenBtn.innerHTML = '⛶';
            fullscreenBtn.title = 'Toggle Fullscreen';
            fullscreenBtn.addEventListener('click', function() {
                toggleFullscreen(diagram);
            });
            
            // Reset zoom button
            const resetBtn = document.createElement('button');
            resetBtn.className = 'diagram-control-btn';
            resetBtn.innerHTML = '↺';
            resetBtn.title = 'Reset Zoom';
            resetBtn.addEventListener('click', function() {
                resetDiagramZoom(diagram);
            });
            
            // Copy to clipboard button
            const copyBtn = document.createElement('button');
            copyBtn.className = 'diagram-control-btn';
            copyBtn.innerHTML = '📋';
            copyBtn.title = 'Copy SVG to Clipboard';
            copyBtn.addEventListener('click', function() {
                copySvgToClipboard(diagram);
            });
            
            controls.appendChild(fullscreenBtn);
            controls.appendChild(resetBtn);
            controls.appendChild(copyBtn);
            
            diagram.appendChild(controls);
        });
    }
    
    // Toggle fullscreen mode
    function toggleFullscreen(diagram) {
        if (diagram.classList.contains('fullscreen')) {
            diagram.classList.remove('fullscreen');
            document.body.style.overflow = '';
        } else {
            diagram.classList.add('fullscreen');
            document.body.style.overflow = 'hidden';
            
            // Add escape key listener
            const escapeHandler = function(e) {
                if (e.key === 'Escape') {
                    diagram.classList.remove('fullscreen');
                    document.body.style.overflow = '';
                    document.removeEventListener('keydown', escapeHandler);
                }
            };
            document.addEventListener('keydown', escapeHandler);
        }
    }
    
    // Reset diagram zoom
    function resetDiagramZoom(diagram) {
        const svg = diagram.querySelector('svg');
        if (svg) {
            // Try to reset panzoom if available
            if (window.panzoom) {
                const panzoomInstance = window.panzoom(svg);
                if (panzoomInstance) {
                    panzoomInstance.reset();
                }
            }
            
            // Fallback: reset transform
            svg.style.transform = '';
        }
    }
    
    // Copy SVG to clipboard
    function copySvgToClipboard(diagram) {
        const svg = diagram.querySelector('svg');
        if (svg) {
            const svgString = new XMLSerializer().serializeToString(svg);
            
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(svgString).then(function() {
                    showNotification('SVG copied to clipboard!');
                }).catch(function() {
                    fallbackCopyToClipboard(svgString);
                });
            } else {
                fallbackCopyToClipboard(svgString);
            }
        }
    }
    
    // Fallback copy method
    function fallbackCopyToClipboard(text) {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'absolute';
        textArea.style.left = '-9999px';
        document.body.appendChild(textArea);
        textArea.select();
        try {
            document.execCommand('copy');
            showNotification('SVG copied to clipboard!');
        } catch (err) {
            showNotification('Failed to copy SVG');
        }
        document.body.removeChild(textArea);
    }
    
    // Show notification
    function showNotification(message) {
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(0, 0, 0, 0.8);
            color: white;
            padding: 10px 15px;
            border-radius: 4px;
            z-index: 10000;
            font-size: 14px;
            font-family: var(--md-code-font-family);
        `;
        notification.textContent = message;
        document.body.appendChild(notification);
        
        setTimeout(function() {
            notification.remove();
        }, 3000);
    }
    
    // Add keyboard shortcuts
    function addKeyboardShortcuts() {
        document.addEventListener('keydown', function(e) {
            // Only when focused on a mermaid diagram or its parent
            const focusedElement = document.activeElement;
            const mermaidContainer = focusedElement.closest('.mermaid');
            
            if (mermaidContainer) {
                switch(e.key) {
                    case 'f':
                    case 'F':
                        if (e.altKey) {
                            e.preventDefault();
                            toggleFullscreen(mermaidContainer);
                        }
                        break;
                    case 'r':
                    case 'R':
                        if (e.altKey) {
                            e.preventDefault();
                            resetDiagramZoom(mermaidContainer);
                        }
                        break;
                }
            }
        });
    }
    
    // Make diagrams focusable for keyboard navigation
    function makeDiagramsFocusable() {
        const mermaidDiagrams = document.querySelectorAll('.mermaid');
        mermaidDiagrams.forEach(function(diagram) {
            diagram.setAttribute('tabindex', '0');
            diagram.style.outline = 'none';
            
            // Add focus indicator
            diagram.addEventListener('focus', function() {
                diagram.style.boxShadow = '0 0 0 2px var(--md-accent-fg-color)';
            });
            
            diagram.addEventListener('blur', function() {
                diagram.style.boxShadow = '';
            });
        });
    }
    
    // Initialize enhanced features
    function initializeEnhancedFeatures() {
        // Wait a bit for mermaid to render
        setTimeout(function() {
            addDiagramControls();
            makeDiagramsFocusable();
            addKeyboardShortcuts();
        }, 1000);
        
        // Also listen for navigation changes (SPA-like behavior)
        const observer = new MutationObserver(function() {
            setTimeout(function() {
                addDiagramControls();
                makeDiagramsFocusable();
            }, 500);
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }
    
    // Start initialization
    initializeEnhancedFeatures();
    
    // Add usage instructions
    function addUsageInstructions() {
        const style = document.createElement('style');
        style.textContent = `
            .mermaid::after {
                content: "💡 Hold Alt + scroll to zoom, Alt+F for fullscreen, Alt+R to reset";
                display: block;
                font-size: 11px;
                color: var(--md-default-fg-color--light);
                text-align: center;
                margin-top: 8px;
                opacity: 0;
                transition: opacity 0.3s;
            }
            
            .mermaid:hover::after {
                opacity: 0.7;
            }
            
            @media (max-width: 768px) {
                .mermaid::after {
                    content: "💡 Tap diagram controls above for zoom and fullscreen";
                }
            }
        `;
        document.head.appendChild(style);
    }
    
    addUsageInstructions();
});