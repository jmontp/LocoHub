// Global language toggle; per-section tabs control Raw/Library independently
document.addEventListener('DOMContentLoaded', function() {
    const isRelevantPage = window.location.pathname.includes('/tutorials/') || document.querySelector('.code-mode-buttons');
    if (!isRelevantPage) return;

    // Global language preference
    let currentLang = (localStorage.getItem('codeLang') || 'python').toLowerCase();
    function applyLang() {
        document.documentElement.setAttribute('data-code-lang', currentLang);
        updateButtons();
        localStorage.setItem('codeLang', currentLang);
    }
    function updateButtons() {
        document.querySelectorAll('.code-mode-button').forEach(btn => {
            const lang = (btn.getAttribute('data-lang') || '').toLowerCase();
            if (lang === currentLang) btn.classList.add('active');
            else btn.classList.remove('active');
        });
    }

    // Global mode preference (Raw/Library) across all tabbed sections
    let currentMode = (localStorage.getItem('codeMode') || 'raw').toLowerCase(); // 'raw' | 'library'
    function syncModeTabs(mode) {
        const targetLabel = mode === 'library' ? 'Library' : 'Raw';
        document.querySelectorAll('.tabbed-set').forEach(set => {
            const labels = set.querySelectorAll('label');
            labels.forEach(label => {
                if (label.textContent.trim() === targetLabel) {
                    const radioId = label.getAttribute('for');
                    const radio = document.getElementById(radioId);
                    if (radio && !radio.checked) {
                        radio.checked = true;
                        radio.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                }
            });
        });
        localStorage.setItem('codeMode', mode);
    }

    // Initial apply
    applyLang();
    setTimeout(() => syncModeTabs(currentMode), 100);

    // Handle top language buttons
    document.addEventListener('click', function(e) {
        const btn = e.target.closest('.code-mode-button');
        if (!btn) return;
        const lang = (btn.getAttribute('data-lang') || '').toLowerCase();
        if (lang === 'python' || lang === 'matlab') {
            currentLang = lang;
            applyLang();
            e.preventDefault();
        }
    });

    // Listen for Raw/Library tab clicks and sync site-wide
    document.addEventListener('click', function(e) {
        if (e.target.tagName !== 'LABEL') return;
        if (!e.target.closest('.tabbed-set')) return;
        const text = e.target.textContent.trim();
        if (text === 'Raw' || text === 'Library') {
            currentMode = (text === 'Library') ? 'library' : 'raw';
            // small delay to let the clicked tab update first
            setTimeout(() => syncModeTabs(currentMode), 10);
        }
    }, true);
});
