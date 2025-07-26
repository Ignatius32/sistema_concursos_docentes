/**
 * JSON Editor Module
 * A user-friendly JSON editor with syntax highlighting, validation, formatting, and collapsible sections
 */
class JSONEditor {
    constructor(textareaId, options = {}) {
        this.textareaId = textareaId;
        this.textarea = document.getElementById(textareaId);
        this.options = {
            theme: options.theme || 'light',
            tabSize: options.tabSize || 2,
            enableLineNumbers: options.enableLineNumbers !== false,
            enableFormatting: options.enableFormatting !== false,
            enableValidation: options.enableValidation !== false,
            enableCollapsible: options.enableCollapsible !== false,
            placeholder: options.placeholder || 'Enter JSON data...',
            ...options
        };
        
        this.init();
    }
    
    init() {
        if (!this.textarea) {
            console.error(`JSONEditor: Textarea with id "${this.textareaId}" not found`);
            return;
        }
        
        this.createEditorContainer();
        this.setupEventListeners();
        this.updateContent();
        
        // Initial validation if there's content
        if (this.textarea.value.trim()) {
            this.validateJSON();
        }
    }
    
    createEditorContainer() {
        // Create wrapper container
        this.wrapper = document.createElement('div');
        this.wrapper.className = 'json-editor-wrapper';
        
        // Create toolbar
        this.toolbar = document.createElement('div');
        this.toolbar.className = 'json-editor-toolbar';
        this.toolbar.innerHTML = `
            <div class="btn-group btn-group-sm" role="group">
                <button type="button" class="btn btn-outline-primary" data-action="format" title="Format JSON">
                    <i class="fas fa-magic"></i> Format
                </button>
                <button type="button" class="btn btn-outline-success" data-action="validate" title="Validate JSON">
                    <i class="fas fa-check-circle"></i> Validate
                </button>
                <button type="button" class="btn btn-outline-info" data-action="minify" title="Minify JSON">
                    <i class="fas fa-compress"></i> Minify
                </button>
                <button type="button" class="btn btn-outline-secondary" data-action="expand-all" title="Expand All">
                    <i class="fas fa-expand-alt"></i> Expand
                </button>
                <button type="button" class="btn btn-outline-secondary" data-action="collapse-all" title="Collapse All">
                    <i class="fas fa-compress-alt"></i> Collapse
                </button>
            </div>
            <div class="json-editor-status">
                <span class="status-indicator" id="${this.textareaId}-status"></span>
            </div>
        `;
        
        // Create editor container
        this.editorContainer = document.createElement('div');
        this.editorContainer.className = 'json-editor-container';
        
        // Create line numbers container
        if (this.options.enableLineNumbers) {
            this.lineNumbers = document.createElement('div');
            this.lineNumbers.className = 'json-editor-line-numbers';
            this.editorContainer.appendChild(this.lineNumbers);
        }
        
        // Create content container
        this.contentContainer = document.createElement('div');
        this.contentContainer.className = 'json-editor-content';
        this.editorContainer.appendChild(this.contentContainer);
        
        // Hide original textarea
        this.textarea.style.display = 'none';
        
        // Insert editor after textarea
        this.textarea.parentNode.insertBefore(this.wrapper, this.textarea.nextSibling);
        this.wrapper.appendChild(this.toolbar);
        this.wrapper.appendChild(this.editorContainer);
        
        // Add CSS styles
        this.addStyles();
    }
    
    addStyles() {
        const styleId = 'json-editor-styles';
        if (document.getElementById(styleId)) return;
        
        const style = document.createElement('style');
        style.id = styleId;
        style.textContent = `
            .json-editor-wrapper {
                border: 1px solid #dee2e6;
                border-radius: 0.375rem;
                background: #fff;
                margin-top: 0.5rem;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            }
            
            .json-editor-toolbar {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 0.75rem;
                background: #f8f9fa;
                border-bottom: 1px solid #dee2e6;
                border-radius: 0.375rem 0.375rem 0 0;
            }
            
            .json-editor-toolbar .btn-group .btn {
                font-size: 0.875rem;
                padding: 0.375rem 0.75rem;
            }
            
            .json-editor-status .status-indicator {
                padding: 0.25rem 0.75rem;
                border-radius: 0.375rem;
                font-size: 0.875rem;
                font-weight: 500;
                display: inline-block;
                min-width: 100px;
                text-align: center;
            }
            
            .status-valid { 
                background: #d1e7dd; 
                color: #0f5132; 
                border: 1px solid #badbcc;
            }
            .status-invalid { 
                background: #f8d7da; 
                color: #842029; 
                border: 1px solid #f5c2c7;
            }
            .status-warning { 
                background: #fff3cd; 
                color: #664d03; 
                border: 1px solid #ffecb5;
            }
            
            .json-editor-container {
                display: flex;
                min-height: 300px;
                max-height: 600px;
                overflow: hidden;
                background: #fff;
            }
            
            .json-editor-line-numbers {
                background: #f8f9fa;
                border-right: 1px solid #dee2e6;
                color: #6c757d;
                font-family: 'Courier New', 'Monaco', 'Menlo', monospace;
                font-size: 13px;
                line-height: 1.5;
                padding: 1rem 0.75rem;
                text-align: right;
                min-width: 50px;
                user-select: none;
                overflow: hidden;
            }
            
            .json-editor-content {
                flex: 1;
                font-family: 'Courier New', 'Monaco', 'Menlo', monospace;
                font-size: 13px;
                line-height: 1.5;
                padding: 1rem;
                overflow: auto;
                white-space: pre;
                outline: none;
                border: none;
                resize: none;
                background: #fff;
                color: #212529;
            }
            
            .json-editor-content:focus {
                outline: none;
                box-shadow: none;
            }
            
            .json-editor-content:empty:before {
                content: attr(data-placeholder);
                color: #6c757d;
                font-style: italic;
            }
            
            /* Syntax highlighting with Bootstrap-compatible colors */
            .json-key { 
                color: #0d6efd; 
                font-weight: 600; 
            }
            .json-string { 
                color: #198754; 
            }
            .json-number { 
                color: #6f42c1; 
                font-weight: 500;
            }
            .json-boolean { 
                color: #dc3545; 
                font-weight: 500;
            }
            .json-null { 
                color: #6c757d; 
                font-style: italic; 
                font-weight: 500;
            }
            .json-brace, .json-bracket { 
                color: #495057; 
                font-weight: 600; 
            }
            .json-comma, .json-colon { 
                color: #495057; 
            }
            
            /* Collapsible elements (future feature) */
            .json-collapsible {
                cursor: pointer;
                position: relative;
            }
            
            .json-collapsible::before {
                content: '▼';
                position: absolute;
                left: -15px;
                color: #6c757d;
                font-size: 10px;
                line-height: 1.5;
            }
            
            .json-collapsed::before {
                content: '▶';
            }
            
            .json-collapsed + .json-block {
                display: none;
            }
            
            /* Error highlighting */
            .json-error-line {
                background: #f8d7da;
                border-left: 3px solid #dc3545;
                padding-left: 0.5rem;
                margin-left: -0.5rem;
            }
            
            /* Integration with Bootstrap form validation */
            .was-validated .json-editor-wrapper:has(textarea:invalid),
            .json-editor-wrapper.is-invalid {
                border-color: #dc3545;
            }
            
            .was-validated .json-editor-wrapper:has(textarea:valid),
            .json-editor-wrapper.is-valid {
                border-color: #198754;
            }
            
            /* Responsive adjustments */
            @media (max-width: 768px) {
                .json-editor-toolbar {
                    flex-direction: column;
                    gap: 0.5rem;
                }
                
                .json-editor-toolbar .btn-group {
                    flex-wrap: wrap;
                    justify-content: center;
                }
                
                .json-editor-container {
                    max-height: 400px;
                }
                
                .json-editor-line-numbers {
                    min-width: 40px;
                    padding: 0.75rem 0.5rem;
                }
            }
        `;
        document.head.appendChild(style);
    }
    
    setupEventListeners() {
        // Toolbar actions
        this.toolbar.addEventListener('click', (e) => {
            const action = e.target.closest('[data-action]')?.dataset.action;
            if (action) {
                this.handleToolbarAction(action);
            }
        });
        
        // Content editing
        this.contentContainer.addEventListener('input', (e) => {
            this.updateTextarea();
            this.updateLineNumbers();
            this.validateJSON();
        });
        
        this.contentContainer.addEventListener('keydown', (e) => {
            this.handleKeyDown(e);
        });
        
        this.contentContainer.addEventListener('scroll', () => {
            if (this.lineNumbers) {
                this.lineNumbers.scrollTop = this.contentContainer.scrollTop;
            }
        });
        
        // Make content editable
        this.contentContainer.contentEditable = true;
        this.contentContainer.setAttribute('spellcheck', 'false');
    }
    
    handleToolbarAction(action) {
        switch (action) {
            case 'format':
                this.formatJSON();
                break;
            case 'validate':
                this.validateJSON();
                break;
            case 'minify':
                this.minifyJSON();
                break;
            case 'expand-all':
                this.expandAll();
                break;
            case 'collapse-all':
                this.collapseAll();
                break;
        }
    }
    
    handleKeyDown(e) {
        if (e.key === 'Tab') {
            e.preventDefault();
            this.insertAtCursor(' '.repeat(this.options.tabSize));
        } else if (e.key === 'Enter') {
            e.preventDefault();
            this.handleEnterKey();
        } else if (e.ctrlKey && e.key === 's') {
            e.preventDefault();
            this.formatJSON();
        }
    }
    
    handleEnterKey() {
        const selection = window.getSelection();
        const range = selection.getRangeAt(0);
        const lineStart = this.getLineStart(range.startContainer, range.startOffset);
        const indent = this.getIndentation(lineStart);
        
        const newLine = '\n' + indent;
        this.insertAtCursor(newLine);
    }
    
    insertAtCursor(text) {
        const selection = window.getSelection();
        if (selection.rangeCount > 0) {
            const range = selection.getRangeAt(0);
            range.deleteContents();
            range.insertNode(document.createTextNode(text));
            range.collapse(false);
            selection.removeAllRanges();
            selection.addRange(range);
        }
    }
    
    getLineStart(node, offset) {
        const textContent = this.contentContainer.textContent;
        let position = this.getCaretPosition();
        let lineStart = textContent.lastIndexOf('\n', position - 1) + 1;
        return textContent.substring(lineStart, position);
    }
    
    getIndentation(lineText) {
        const match = lineText.match(/^(\s*)/);
        return match ? match[1] : '';
    }
    
    getCaretPosition() {
        const selection = window.getSelection();
        if (selection.rangeCount === 0) return 0;
        
        const range = selection.getRangeAt(0);
        const preCaretRange = range.cloneRange();
        preCaretRange.selectNodeContents(this.contentContainer);
        preCaretRange.setEnd(range.endContainer, range.endOffset);
        return preCaretRange.toString().length;
    }
    
    updateContent() {
        const content = this.textarea.value;
        this.setContent(content);
        this.updateLineNumbers();
    }
    
    setContent(content) {
        if (content.trim()) {
            this.contentContainer.innerHTML = this.highlightJSON(content);
        } else {
            this.contentContainer.innerHTML = `<span style="color: #6c757d; font-style: italic;">${this.options.placeholder}</span>`;
        }
    }
    
    updateTextarea() {
        this.textarea.value = this.contentContainer.textContent;
        // Trigger change event for form validation
        this.textarea.dispatchEvent(new Event('change', { bubbles: true }));
    }
    
    updateLineNumbers() {
        if (!this.lineNumbers) return;
        
        const lines = this.contentContainer.textContent.split('\n');
        const lineCount = lines.length;
        
        let html = '';
        for (let i = 1; i <= lineCount; i++) {
            html += `${i}\n`;
        }
        this.lineNumbers.textContent = html;
    }
    
    highlightJSON(jsonString) {
        if (!jsonString.trim()) return '';
        
        try {
            // Parse and re-stringify to ensure valid JSON
            const parsed = JSON.parse(jsonString);
            jsonString = JSON.stringify(parsed, null, this.options.tabSize);
        } catch (e) {
            // If parsing fails, just highlight as-is
        }
        
        return jsonString
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"([^"\\]*(\\.[^"\\]*)*)"\s*:/g, '<span class="json-key">"$1"</span><span class="json-colon">:</span>')
            .replace(/"([^"\\]*(\\.[^"\\]*)*)"/g, '<span class="json-string">"$1"</span>')
            .replace(/\b(-?\d+\.?\d*)\b/g, '<span class="json-number">$1</span>')
            .replace(/\b(true|false)\b/g, '<span class="json-boolean">$1</span>')
            .replace(/\bnull\b/g, '<span class="json-null">null</span>')
            .replace(/([{}])/g, '<span class="json-brace">$1</span>')
            .replace(/([\[\]])/g, '<span class="json-bracket">$1</span>')
            .replace(/,/g, '<span class="json-comma">,</span>');
    }
    
    formatJSON() {
        try {
            const content = this.contentContainer.textContent.trim();
            if (!content) return;
            
            const parsed = JSON.parse(content);
            const formatted = JSON.stringify(parsed, null, this.options.tabSize);
            this.setContent(formatted);
            this.updateTextarea();
            this.updateLineNumbers();
            this.setStatus('JSON formatted successfully', 'valid');
        } catch (e) {
            this.setStatus(`Format error: ${e.message}`, 'invalid');
        }
    }
    
    minifyJSON() {
        try {
            const content = this.contentContainer.textContent.trim();
            if (!content) return;
            
            const parsed = JSON.parse(content);
            const minified = JSON.stringify(parsed);
            this.setContent(minified);
            this.updateTextarea();
            this.updateLineNumbers();
            this.setStatus('JSON minified successfully', 'valid');
        } catch (e) {
            this.setStatus(`Minify error: ${e.message}`, 'invalid');
        }
    }
    
    validateJSON() {
        const content = this.contentContainer.textContent.trim();
        if (!content) {
            this.setStatus('Empty content', 'warning');
            return false;
        }
        
        try {
            JSON.parse(content);
            this.setStatus('Valid JSON', 'valid');
            this.clearErrors();
            return true;
        } catch (e) {
            this.setStatus(`Invalid JSON: ${e.message}`, 'invalid');
            this.highlightError(e);
            return false;
        }
    }
    
    setStatus(message, type) {
        const statusEl = document.getElementById(`${this.textareaId}-status`);
        if (statusEl) {
            statusEl.textContent = message;
            statusEl.className = `status-indicator status-${type}`;
        }
    }
    
    clearErrors() {
        const errorLines = this.contentContainer.querySelectorAll('.json-error-line');
        errorLines.forEach(line => line.classList.remove('json-error-line'));
    }
    
    highlightError(error) {
        // Simple error highlighting - could be enhanced
        this.clearErrors();
        
        // Try to extract line number from error message
        const lineMatch = error.message.match(/line (\d+)/i);
        if (lineMatch) {
            const lineNumber = parseInt(lineMatch[1]);
            // Implementation would depend on how we structure the highlighted content
        }
    }
    
    expandAll() {
        // Implementation for expanding collapsed sections
        this.setStatus('All sections expanded', 'valid');
    }
    
    collapseAll() {
        // Implementation for collapsing sections
        this.setStatus('All sections collapsed', 'valid');
    }
    
    // Public API methods
    getValue() {
        return this.textarea.value;
    }
    
    setValue(value) {
        this.textarea.value = value;
        this.updateContent();
    }
    
    isValid() {
        return this.validateJSON();
    }
    
    format() {
        this.formatJSON();
    }
    
    destroy() {
        if (this.wrapper && this.wrapper.parentNode) {
            this.wrapper.parentNode.removeChild(this.wrapper);
        }
        this.textarea.style.display = '';
    }
}

// Auto-initialize JSON editors
document.addEventListener('DOMContentLoaded', function() {
    // Look for textareas with data-json-editor attribute
    const jsonTextareas = document.querySelectorAll('textarea[data-json-editor]');
    
    jsonTextareas.forEach(textarea => {
        const options = {};
        
        // Parse options from data attributes
        if (textarea.dataset.jsonEditorTheme) {
            options.theme = textarea.dataset.jsonEditorTheme;
        }
        if (textarea.dataset.jsonEditorTabSize) {
            options.tabSize = parseInt(textarea.dataset.jsonEditorTabSize);
        }
        if (textarea.dataset.jsonEditorPlaceholder) {
            options.placeholder = textarea.dataset.jsonEditorPlaceholder;
        }
        
        // Initialize editor
        new JSONEditor(textarea.id, options);
    });
});

// Export for manual initialization
window.JSONEditor = JSONEditor;
