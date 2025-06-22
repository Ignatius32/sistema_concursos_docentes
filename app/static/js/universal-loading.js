/**
 * Universal Loading System
 * Automatically shows/hides loading overlay for all HTTP requests
 * Prevents double submissions and provides visual feedback
 */

class UniversalLoading {
    constructor() {
        this.requestCount = 0;
        this.loadingOverlay = null;
        this.originalFetch = null;
        this.init();
    }

    init() {
        this.createLoadingOverlay();
        this.interceptFetch();
        this.interceptXHR();
        this.interceptForms();
        this.interceptLinks();
    }

    createLoadingOverlay() {
        // Remove existing overlay if any
        const existing = document.getElementById('universalLoadingOverlay');
        if (existing) {
            existing.remove();
        }

        // Create new loading overlay
        this.loadingOverlay = document.createElement('div');
        this.loadingOverlay.id = 'universalLoadingOverlay';
        this.loadingOverlay.className = 'loading-overlay';
        this.loadingOverlay.innerHTML = `
            <div class="spinner-container">
                <div class="spinner"></div>
                <div class="loading-text">Cargando...</div>
            </div>
        `;
        document.body.appendChild(this.loadingOverlay);
    }

    showLoading(message = 'Cargando...') {
        this.requestCount++;
        if (this.loadingOverlay) {
            const textElement = this.loadingOverlay.querySelector('.loading-text');
            if (textElement) {
                textElement.textContent = message;
            }
            this.loadingOverlay.classList.add('active');
        }
    }

    hideLoading() {
        this.requestCount = Math.max(0, this.requestCount - 1);
        if (this.requestCount === 0 && this.loadingOverlay) {
            this.loadingOverlay.classList.remove('active');
        }
    }

    interceptFetch() {
        const self = this;
        self.originalFetch = window.fetch;
        
        window.fetch = function(...args) {
            // Don't show loading for very small requests or certain URLs
            const url = args[0];
            if (self.shouldSkipLoading(url)) {
                return self.originalFetch.apply(this, args);
            }

            self.showLoading('Procesando solicitud...');
            
            return self.originalFetch.apply(this, args)
                .then(response => {
                    self.hideLoading();
                    return response;
                })
                .catch(error => {
                    self.hideLoading();
                    throw error;
                });
        };
    }

    interceptXHR() {
        const self = this;
        const originalOpen = XMLHttpRequest.prototype.open;
        const originalSend = XMLHttpRequest.prototype.send;

        XMLHttpRequest.prototype.open = function(method, url, ...args) {
            this._url = url;
            this._method = method;
            return originalOpen.apply(this, [method, url, ...args]);
        };

        XMLHttpRequest.prototype.send = function(...args) {
            if (!self.shouldSkipLoading(this._url)) {
                self.showLoading('Enviando datos...');
                
                this.addEventListener('loadend', () => {
                    self.hideLoading();
                });
            }
            
            return originalSend.apply(this, args);
        };
    }

    interceptForms() {
        const self = this;
        
        // Handle all form submissions
        document.addEventListener('submit', function(event) {
            const form = event.target;
            
            // Skip if form has data-no-loading attribute
            if (form.dataset.noLoading === 'true') {
                return;
            }

            // Get custom loading message
            const message = form.dataset.loadingMessage || 'Enviando formulario...';
            
            // Show loading
            self.showLoading(message);
            
            // Add loading class to form
            form.classList.add('form-loading');
            
            // Disable submit buttons to prevent double submission
            const submitButtons = form.querySelectorAll('button[type="submit"], input[type="submit"]');
            submitButtons.forEach(button => {
                button.disabled = true;
                button.classList.add('btn-loading');
                
                // Store original text
                if (!button.dataset.originalText) {
                    button.dataset.originalText = button.textContent || button.value;
                }
                
                // Update button text
                const loadingText = button.dataset.loadingText || 'Procesando...';
                if (button.tagName === 'INPUT') {
                    button.value = loadingText;
                } else {
                    button.innerHTML = `<span class="btn-text">${loadingText}</span>`;
                }
            });

            // For regular form submissions (not AJAX), set a timeout to hide loading
            // in case the page reloads
            if (!form.dataset.ajax) {
                setTimeout(() => {
                    self.hideLoading();
                }, 500);
            }
        });

        // Handle form reset after AJAX
        document.addEventListener('ajaxComplete', function(event) {
            self.resetFormLoading(event.target);
        });
    }

    interceptLinks() {
        const self = this;
        
        document.addEventListener('click', function(event) {
            const link = event.target.closest('a');
            
            if (link && link.href && !link.dataset.noLoading) {
                // Skip external links, anchors, and javascript links
                if (link.hostname !== window.location.hostname || 
                    link.href.startsWith('#') || 
                    link.href.startsWith('javascript:') ||
                    link.target === '_blank') {
                    return;
                }

                const message = link.dataset.loadingMessage || 'Navegando...';
                self.showLoading(message);
                
                // Hide loading after a short delay in case navigation is fast
                setTimeout(() => {
                    self.hideLoading();
                }, 3000);
            }
        });
    }

    resetFormLoading(form) {
        if (!form || form.tagName !== 'FORM') return;
        
        // Remove loading class
        form.classList.remove('form-loading');
        
        // Reset submit buttons
        const submitButtons = form.querySelectorAll('button[type="submit"], input[type="submit"]');
        submitButtons.forEach(button => {
            button.disabled = false;
            button.classList.remove('btn-loading');
            
            // Restore original text
            if (button.dataset.originalText) {
                if (button.tagName === 'INPUT') {
                    button.value = button.dataset.originalText;
                } else {
                    button.textContent = button.dataset.originalText;
                }
            }
        });
        
        this.hideLoading();
    }

    shouldSkipLoading(url) {
        if (!url) return false;
        
        // Skip for certain file types or API endpoints that should be quick
        const skipPatterns = [
            /\.(css|js|png|jpg|jpeg|gif|svg|ico|woff|woff2|ttf)$/i,
            /\/api\/status/i,
            /\/health/i,
            /\/ping/i
        ];
        
        return skipPatterns.some(pattern => pattern.test(url));
    }

    // Public methods for manual control
    manual = {
        show: (message) => this.showLoading(message),
        hide: () => this.hideLoading(),
        resetForm: (form) => this.resetFormLoading(form)
    }
}

// Initialize universal loading system
let universalLoading;

document.addEventListener('DOMContentLoaded', function() {
    universalLoading = new UniversalLoading();
    
    // Make it globally accessible
    window.Loading = universalLoading.manual;
});

// Handle page visibility changes
document.addEventListener('visibilitychange', function() {
    if (document.visibilityState === 'visible' && universalLoading) {
        // Reset loading state when page becomes visible again
        universalLoading.requestCount = 0;
        if (universalLoading.loadingOverlay) {
            universalLoading.loadingOverlay.classList.remove('active');
        }
    }
});
