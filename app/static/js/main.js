// Enable all Bootstrap tooltips
document.addEventListener('DOMContentLoaded', function() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});

// Form validation enhancement
document.addEventListener('DOMContentLoaded', function() {
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!form.checkValidity()) {
                e.preventDefault();
                e.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });
});

// Handle dynamic select fields based on parent selection
function setupDynamicSelect(parentId, childId, url, valueKey = 'id', labelKey = 'nombre') {
    const parentSelect = document.getElementById(parentId);
    const childSelect = document.getElementById(childId);
    
    if (parentSelect && childSelect) {
        parentSelect.addEventListener('change', function() {
            const value = this.value;
            childSelect.disabled = true;
            childSelect.innerHTML = '<option value="">Cargando...</option>';

            if (value) {
                fetch(url.replace('__value__', value))
                    .then(response => response.json())
                    .then(data => {
                        childSelect.innerHTML = '<option value="">Seleccione...</option>';
                        data.forEach(item => {
                            const option = document.createElement('option');
                            option.value = item[valueKey];
                            option.textContent = item[labelKey];
                            childSelect.appendChild(option);
                        });
                        childSelect.disabled = false;
                    })
                    .catch(error => {
                        console.error('Error cargando opciones:', error);
                        childSelect.innerHTML = '<option value="">Error al cargar opciones</option>';
                    });
            } else {
                childSelect.innerHTML = '<option value="">Seleccione primero la opción anterior</option>';
            }
        });
    }
}

// Format dates in user's timezone
function formatDates() {
    document.querySelectorAll('[data-date]').forEach(element => {
        const date = new Date(element.dataset.date);
        element.textContent = date.toLocaleDateString();
    });
}

// Helper function to show/hide elements based on condition
function toggleVisibility(elementId, condition) {
    const element = document.getElementById(elementId);
    if (element) {
        element.style.display = condition ? 'block' : 'none';
    }
}

// Helper function to format currency values
function formatCurrency(amount) {
    return new Intl.NumberFormat('es-AR', {
        style: 'currency',
        currency: 'ARS'
    }).format(amount);
}

// Helper function to confirm actions
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

// Add error class to invalid form fields
document.addEventListener('DOMContentLoaded', function() {
    const inputs = document.querySelectorAll('input, select, textarea');
    inputs.forEach(input => {
        input.addEventListener('invalid', function() {
            this.classList.add('is-invalid');
        });
        
        input.addEventListener('input', function() {
            if (this.validity.valid) {
                this.classList.remove('is-invalid');
            }
        });
    });
});

// Handle file input changes to show selected filename
document.addEventListener('DOMContentLoaded', function() {
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(input => {
        input.addEventListener('change', function() {
            const fileName = this.files[0]?.name;
            const label = this.nextElementSibling;
            if (label && label.classList.contains('custom-file-label')) {
                label.textContent = fileName || 'Elegir archivo';
            }
        });
    });
});

// Loading overlay functions
function showLoading() {
    document.getElementById('loadingOverlay').classList.add('active');
}

function hideLoading() {
    document.getElementById('loadingOverlay').classList.remove('active');
}

// Handle postulante document upload
document.addEventListener('DOMContentLoaded', function() {
    const uploadButtons = document.querySelectorAll('[data-action="upload-document"]');
    const documentForm = document.getElementById('document-upload-form');
    const tipoSelect = document.getElementById('tipo');
    const fileInput = document.getElementById('documento');

    uploadButtons?.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const docType = this.dataset.docType;
            if (tipoSelect && docType) {
                tipoSelect.value = docType;
            }
            fileInput?.click();
        });
    });

    // Auto submit form when file is selected
    fileInput?.addEventListener('change', function() {
        if (this.files.length > 0) {
            showLoading(); // Show loading overlay before submitting
            documentForm?.submit();
        }
    });

    // Add loading overlay for form submissions
    documentForm?.addEventListener('submit', function() {
        showLoading();
    });
});