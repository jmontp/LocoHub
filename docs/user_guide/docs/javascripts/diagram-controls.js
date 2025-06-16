// Enhanced Interactive Mermaid Diagram Controls
document.addEventListener('DOMContentLoaded', function() {
    
    // Add enhanced controls to each mermaid diagram
    function addDiagramControls() {
        const mermaidDiagrams = document.querySelectorAll('.mermaid');
        
        mermaidDiagrams.forEach(function(diagram) {
            // Skip if no SVG (not a real diagram) or controls already added
            const svg = diagram.querySelector('svg');
            if (!svg || diagram.querySelector('.diagram-controls')) {
                return;
            }
            
            // Add fallback class for browsers without :has() support
            diagram.classList.add('has-diagram');
            
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
        if (diagram._resetTransform) {
            diagram._resetTransform();
        } else {
            // Fallback: reset transform directly
            const svg = diagram.querySelector('svg');
            if (svg) {
                svg.style.transform = '';
            }
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
    
    // Add zoom and pan functionality
    function addZoomPanFunctionality() {
        const mermaidDiagrams = document.querySelectorAll('.mermaid');
        
        mermaidDiagrams.forEach(function(diagram) {
            const svg = diagram.querySelector('svg');
            if (!svg) return;
            
            let scale = 1;
            let translateX = 0;
            let translateY = 0;
            let isDragging = false;
            let startX, startY;
            
            // Apply transform
            function updateTransform() {
                svg.style.transform = `translate(${translateX}px, ${translateY}px) scale(${scale})`;
            }
            
            // Wheel zoom (with Alt key)
            diagram.addEventListener('wheel', function(e) {
                if (!e.altKey) return;
                e.preventDefault();
                
                const rect = svg.getBoundingClientRect();
                const mouseX = e.clientX - rect.left;
                const mouseY = e.clientY - rect.top;
                
                const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
                const newScale = Math.max(0.1, Math.min(5, scale * zoomFactor));
                
                // Zoom towards mouse position
                const scaleChange = newScale / scale;
                translateX = mouseX - (mouseX - translateX) * scaleChange;
                translateY = mouseY - (mouseY - translateY) * scaleChange;
                scale = newScale;
                
                updateTransform();
            });
            
            // Pan with Alt + drag
            diagram.addEventListener('mousedown', function(e) {
                if (!e.altKey) return;
                e.preventDefault();
                isDragging = true;
                startX = e.clientX - translateX;
                startY = e.clientY - translateY;
                diagram.style.cursor = 'grabbing';
            });
            
            document.addEventListener('mousemove', function(e) {
                if (!isDragging) return;
                e.preventDefault();
                translateX = e.clientX - startX;
                translateY = e.clientY - startY;
                updateTransform();
            });
            
            document.addEventListener('mouseup', function() {
                if (isDragging) {
                    isDragging = false;
                    diagram.style.cursor = '';
                }
            });
            
            // Store reset function for reset button
            diagram._resetTransform = function() {
                scale = 1;
                translateX = 0;
                translateY = 0;
                updateTransform();
            };
        });
    }

    // Make diagrams focusable for keyboard navigation
    function makeDiagramsFocusable() {
        const mermaidDiagrams = document.querySelectorAll('.mermaid');
        mermaidDiagrams.forEach(function(diagram) {
            const svg = diagram.querySelector('svg');
            if (!svg) return;
            
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
    
    // Initialize enhanced features only if needed
    function initializeEnhancedFeatures() {
        // Check if page has mermaid content before initializing
        const hasMermaidContent = document.querySelector('.mermaid');
        if (!hasMermaidContent) return;
        
        // Wait a bit for mermaid to render
        setTimeout(function() {
            addDiagramControls();
            addZoomPanFunctionality();
            makeDiagramsFocusable();
            addKeyboardShortcuts();
        }, 1000);
        
        // Also listen for navigation changes (SPA-like behavior)
        const observer = new MutationObserver(function() {
            setTimeout(function() {
                addDiagramControls();
                addZoomPanFunctionality();
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
    
    // Add usage instructions only for pages with actual mermaid diagrams
    function addUsageInstructions() {
        // Check if page actually has mermaid diagrams with SVG content
        const mermaidDiagrams = document.querySelectorAll('.mermaid svg');
        
        // Only add instructions if there are actual diagrams AND we're on a diagram-heavy page
        if (mermaidDiagrams.length > 0 && document.body.textContent.includes('mermaid')) {
            const style = document.createElement('style');
            style.textContent = `
                /* Primary selector for modern browsers */
                .mermaid:has(svg)::after {
                    content: "💡 Hold Alt + scroll to zoom, Alt+F for fullscreen, Alt+R to reset";
                    display: block;
                    font-size: 11px;
                    color: var(--md-default-fg-color--light);
                    text-align: center;
                    margin-top: 8px;
                    opacity: 0;
                    transition: opacity 0.3s;
                }
                
                .mermaid:has(svg):hover::after {
                    opacity: 0.7;
                }
                
                /* Fallback for browsers without :has() support */
                .mermaid.has-diagram::after {
                    content: "💡 Hold Alt + scroll to zoom, Alt+F for fullscreen, Alt+R to reset";
                    display: block;
                    font-size: 11px;
                    color: var(--md-default-fg-color--light);
                    text-align: center;
                    margin-top: 8px;
                    opacity: 0;
                    transition: opacity 0.3s;
                }
                
                .mermaid.has-diagram:hover::after {
                    opacity: 0.7;
                }
                
                @media (max-width: 768px) {
                    .mermaid:has(svg)::after,
                    .mermaid.has-diagram::after {
                        content: "💡 Tap diagram controls above for zoom and fullscreen";
                    }
                }
            `;
            document.head.appendChild(style);
            
            // Add fallback class for browsers without :has() support
            mermaidDiagrams.forEach(function(svg) {
                const mermaidContainer = svg.closest('.mermaid');
                if (mermaidContainer) {
                    mermaidContainer.classList.add('has-diagram');
                }
            });
        }
    }
    
    // Call this after mermaid diagrams are loaded
    setTimeout(addUsageInstructions, 1500);
});