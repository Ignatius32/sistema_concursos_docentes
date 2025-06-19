/**
 * Tribunal Selected Members Module
 * Handles the management of selected tribunal members before saving
 */
console.log('Loading TribunalSelectedMembersManager v3.0 - Individual Save Version with Debug');

class TribunalSelectedMembersManager {
    constructor() {
        this.selectedMembers = new Map();
        this.init();
    }
      init() {
        try {
            this.bindEvents();
            this.updateUI();
            console.log('TribunalSelectedMembersManager initialized');
        } catch (error) {
            console.error('TribunalSelectedMembersManager initialization error:', error);
        }
    }
      bindEvents() {
        // Listen for member addition events from search
        document.addEventListener('memberAdd', (e) => {
            this.addMember(e.detail.persona);
        });
        
        // Clear all button (if it exists)
        const clearAllBtn = document.getElementById('clearAll');
        if (clearAllBtn) {
            clearAllBtn.addEventListener('click', () => this.clearAll());
            console.log('Clear all button event bound');
        }
    }
    
    addMember(persona) {
        console.log('Adding member:', persona);
        
        // Check if already added
        if (this.selectedMembers.has(persona.id)) {
            this.showAlert(`${persona.nombre} ${persona.apellido} ya está en la lista`, 'warning');
            return;
        }
        
        // Add to selected members
        this.selectedMembers.set(persona.id, persona);
        
        // Create and add card
        this.createMemberCard(persona);
        
        // Update UI
        this.updateUI();
        
        // Clear search
        this.clearSearch();
        
        this.showAlert(`${persona.nombre} ${persona.apellido} agregado al tribunal`, 'success');
    }
    
    clearSearch() {
        const personaSearch = document.getElementById('personaSearch');
        if (personaSearch) {
            personaSearch.value = '';
        }
        
        const searchResults = document.getElementById('searchResults');
        if (searchResults) {
            searchResults.style.display = 'none';
        }
    }
      createMemberCard(persona) {
        const template = document.getElementById('memberCardTemplate');
        if (!template) {
            console.error('Member card template not found');
            return;
        }
        
        const clone = template.content.cloneNode(true);
        const card = clone.querySelector('.member-card');
        
        // Set persona data
        card.dataset.personaId = persona.id;
        clone.querySelector('.persona-name').textContent = `${persona.apellido}, ${persona.nombre}`;
        clone.querySelector('.persona-details').textContent = `DNI: ${persona.dni}${persona.correo ? ' - ' + persona.correo : ''}`;
        
        // Bind remove button
        const removeBtn = clone.querySelector('.remove-member');
        removeBtn.addEventListener('click', () => {
            this.removeMember(persona.id);
        });        // Bind save button
        const saveBtn = clone.querySelector('.save-member-btn');
        saveBtn.addEventListener('click', () => {
            console.log('Save button clicked for persona:', persona.id);
            console.log('Save button element:', saveBtn);
            console.log('Save button parent card:', saveBtn.closest('.member-card'));
            console.log('Card data-persona-id:', saveBtn.closest('.member-card')?.dataset.personaId);
            this.saveMember(persona.id);
        });
        
        // Add to DOM first
        const container = document.getElementById('selectedMembersList');
        if (container) {
            container.appendChild(clone);
              // Now get the actual DOM element to bind events
            const addedCard = container.querySelector(`.member-card[data-persona-id="${persona.id}"]`);
            if (addedCard) {
                // Bind role change event
                const rolSelect = addedCard.querySelector('.rol-select');
                const claustroSelect = addedCard.querySelector('.claustro-select');
                  [rolSelect, claustroSelect].forEach(select => {
                    select.addEventListener('change', (event) => {
                        console.log('Select changed:', event.target.className, 'new value:', event.target.value);
                        this.validateMembers();
                        // Mark as modified when fields change
                        this.markMemberAsModified(persona.id);
                        // Auto-populate permissions when role changes
                        if (select === rolSelect) {
                            console.log('Role changed to:', rolSelect.value, 'updating permissions');
                            this.updatePermissions(addedCard, rolSelect.value);
                        }
                    });
                });// Bind permission checkboxes
                const permissionChecks = addedCard.querySelectorAll('.permissions-section input[type="checkbox"]');
                permissionChecks.forEach(checkbox => {
                    checkbox.addEventListener('change', () => {
                        this.markMemberAsModified(persona.id);
                    });
                });
                
                // Set initial permissions based on default role (Titular is default)
                if (rolSelect) {
                    console.log('Initial rol select value:', rolSelect.value);
                    // Ensure Titular is selected if no value is set
                    if (!rolSelect.value) {
                        rolSelect.value = 'Titular';
                        console.log('Set rol select to Titular');
                    }
                }
                const initialRole = rolSelect?.value || 'Titular';
                console.log('Setting initial permissions for role:', initialRole);
                this.updatePermissions(addedCard, initialRole);
            }
        } else {
            console.error('selectedMembersList container not found');
        }
    }
      updatePermissions(card, rol) {
        console.log('updatePermissions called with rol:', rol);
        const permissions = this.getDefaultPermissions(rol);
        console.log('Default permissions for rol', rol, ':', permissions);
        
        // Update checkboxes with specific class selectors
        const canAddTema = card.querySelector('.can-add-tema');
        const canUploadFile = card.querySelector('.can-upload-file');
        const canSignFile = card.querySelector('.can-sign-file');
        const canViewDocs = card.querySelector('.can-view-postulante-docs');
        
        console.log('Found checkboxes:', {
            canAddTema: !!canAddTema,
            canUploadFile: !!canUploadFile,
            canSignFile: !!canSignFile,
            canViewDocs: !!canViewDocs
        });
        
        if (canAddTema) {
            canAddTema.checked = permissions.can_add_tema;
            canAddTema.disabled = false; // Enable the checkbox
            console.log('Set canAddTema to:', permissions.can_add_tema);
        }
        if (canUploadFile) {
            canUploadFile.checked = permissions.can_upload_file;
            canUploadFile.disabled = false;
            console.log('Set canUploadFile to:', permissions.can_upload_file);
        }
        if (canSignFile) {
            canSignFile.checked = permissions.can_sign_file;
            canSignFile.disabled = false;
            console.log('Set canSignFile to:', permissions.can_sign_file);
        }
        if (canViewDocs) {
            canViewDocs.checked = permissions.can_view_postulante_docs;
            canViewDocs.disabled = false;
            console.log('Set canViewDocs to:', permissions.can_view_postulante_docs);
        }
        
        // Add visual feedback
        const permissionsSection = card.querySelector('.permissions-section');
        if (permissionsSection) {
            permissionsSection.classList.add('permissions-updated');
            setTimeout(() => {
                permissionsSection.classList.remove('permissions-updated');
            }, 1000);
        }
    }
    
    getDefaultPermissions(rol) {
        switch (rol) {
            case 'Presidente':
                return {
                    can_add_tema: true,
                    can_upload_file: true,
                    can_sign_file: true,
                    can_view_postulante_docs: true
                };
            case 'Titular':
                return {
                    can_add_tema: true,
                    can_upload_file: false,
                    can_sign_file: true,
                    can_view_postulante_docs: true
                };
            case 'Suplente':
            case 'Veedor':
            default:
                return {
                    can_add_tema: false,
                    can_upload_file: false,
                    can_sign_file: false,
                    can_view_postulante_docs: false
                };
        }
    }
    
    removeMember(personaId) {
        console.log('Removing member:', personaId);
        
        // Remove from selectedMembers
        const persona = this.selectedMembers.get(personaId);
        this.selectedMembers.delete(personaId);
          // Remove card from DOM
        const card = document.querySelector(`.member-card[data-persona-id="${personaId}"]`);
        if (card) {
            card.closest('.col-md-6').remove();
        }
        
        // Update UI
        this.updateUI();
        
        if (persona) {
            this.showAlert(`${persona.nombre} ${persona.apellido} removido del tribunal`, 'info');
        }
    }
    
    clearAll() {
        if (this.selectedMembers.size === 0) {
            this.showAlert('No hay miembros para limpiar', 'info');
            return;
        }
        
        if (confirm('¿Está seguro de que desea eliminar todos los miembros seleccionados?')) {
            // Clear the map
            this.selectedMembers.clear();
            
            // Remove all cards
            const container = document.getElementById('selectedMembersList');
            if (container) {
                container.innerHTML = '';
            }
            
            // Update UI
            this.updateUI();
            
            this.showAlert('Todos los miembros han sido removidos', 'info');
        }
    }
    
    async saveAllMembers() {
        if (this.selectedMembers.size === 0) {
            this.showAlert('No hay miembros para guardar', 'warning');
            return;
        }
        
        const saveBtn = document.getElementById('saveAllMembers');
        const originalText = saveBtn.innerHTML;
        
        // Disable button and show loading
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Guardando...';
        
        try {
            // Collect member data
            const membersData = [];            this.selectedMembers.forEach((persona, personaId) => {
                const card = document.querySelector(`.member-card[data-persona-id="${personaId}"]`);
                if (card) {
                    // Get form elements with null checks
                    const rolSelect = card.querySelector('.rol-select');
                    const claustroSelect = card.querySelector('.claustro-select');
                    const canAddTema = card.querySelector('.can-add-tema');
                    const canUploadFile = card.querySelector('.can-upload-file');
                    const canSignFile = card.querySelector('.can-sign-file');
                    const canViewDocs = card.querySelector('.can-view-postulante-docs');
                    
                    if (!rolSelect || !claustroSelect || !canAddTema || !canUploadFile || !canSignFile || !canViewDocs) {
                        console.error('Missing form elements in member card for persona:', persona.nombre, persona.apellido);
                        return;
                    }
                    
                    const memberData = {
                        persona_id: persona.id,
                        rol: rolSelect.value,
                        claustro: claustroSelect.value,
                        can_add_tema: canAddTema.checked ? '1' : '0',
                        can_upload_file: canUploadFile.checked ? '1' : '0',
                        can_sign_file: canSignFile.checked ? '1' : '0',
                        can_view_postulante_docs: canViewDocs.checked ? '1' : '0'
                    };
                    
                    // Validate required fields
                    if (!memberData.rol) {
                        throw new Error(`Debe seleccionar un rol para ${persona.nombre} ${persona.apellido}`);
                    }
                    
                    membersData.push(memberData);
                }
            });            
            // Get concurso ID from the URL or a data attribute
            const concursoId = window.location.pathname.match(/\/concurso\/(\d+)/)[1];
            
            console.log('Prepared members data:', membersData);
            
            // Send to server - wrap in members object as expected by Python
            const response = await fetch(`/tribunal/concurso/${concursoId}/agregar`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ members: membersData })
            });
            
            console.log('Response status:', response.status);
            console.log('Response headers:', Object.fromEntries(response.headers.entries()));
            
            // Get the response text first to debug
            const responseText = await response.text();
            console.log('Raw response text:', responseText);
            
            if (response.ok) {
                let result;
                try {
                    result = JSON.parse(responseText);
                } catch (parseError) {
                    console.error('JSON parse error:', parseError);
                    throw new Error(`Server returned non-JSON response: ${responseText.substring(0, 200)}...`);
                }
                
                if (result.success) {
                    this.showAlert(result.message + (result.added_members && result.added_members.length > 0 ? ':<br>' + result.added_members.join('<br>') : ''), 'success');
                    
                    if (result.errors && result.errors.length > 0) {
                        this.showAlert('Algunos errores:<br>' + result.errors.join('<br>'), 'warning');
                    }
                    
                    // Clear selected members
                    this.selectedMembers.clear();
                    const container = document.getElementById('selectedMembersList');
                    if (container) {
                        container.innerHTML = '';
                    }
                    this.updateUI();
                    
                    // Refresh existing members or redirect
                    setTimeout(() => {
                        window.location.reload();
                    }, 2000);
                } else {
                    throw new Error(result.errors ? result.errors.join('<br>') : 'Error desconocido');
                }
                
            } else {
                throw new Error(`HTTP ${response.status}: ${responseText.substring(0, 200)}...`);
            }
              } catch (error) {
            console.error('Error saving members:', error);
            console.error('Error details:', {
                message: error.message,
                stack: error.stack,
                name: error.name
            });
            this.showAlert('Error al guardar miembros: ' + error.message, 'danger');
        } finally {
            saveBtn.disabled = false;
            saveBtn.innerHTML = originalText;
        }
    }
      markMemberAsModified(personaId) {
        const card = document.querySelector(`.member-card[data-persona-id="${personaId}"]`);
        if (card && card.dataset.status !== 'pending') {
            this.updateMemberStatus(personaId, 'modified', 'Modificado - Guardar Cambios', 'warning');
        }
    }

    updateMemberStatus(personaId, status, message, variant) {
        const card = document.querySelector(`.member-card[data-persona-id="${personaId}"]`);
        if (!card) return;

        card.dataset.status = status;
        const header = card.querySelector('.card-header');
        const statusElement = card.querySelector('.member-status');
        const saveBtn = card.querySelector('.save-member-btn');

        // Update header color and content based on status
        const variants = {
            pending: { bg: 'bg-warning', text: 'text-dark', border: 'border-warning', icon: 'fa-clock' },
            modified: { bg: 'bg-info', text: 'text-white', border: 'border-info', icon: 'fa-edit' },
            saving: { bg: 'bg-primary', text: 'text-white', border: 'border-primary', icon: 'fa-spinner fa-spin' },
            saved: { bg: 'bg-success', text: 'text-white', border: 'border-success', icon: 'fa-check' },
            error: { bg: 'bg-danger', text: 'text-white', border: 'border-danger', icon: 'fa-exclamation-triangle' }
        };

        const config = variants[status] || variants.pending;
        
        // Update header
        header.className = `card-header ${config.bg} ${config.text} py-2`;
        card.className = card.className.replace(/border-\w+/, config.border);
        
        // Update status text and icon
        statusElement.innerHTML = `<i class="fas ${config.icon} me-1"></i>${message}`;
        
        // Update save button
        if (saveBtn) {
            if (status === 'saving') {
                saveBtn.disabled = true;
                saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Guardando...';
            } else if (status === 'saved') {
                saveBtn.disabled = true;
                saveBtn.innerHTML = '<i class="fas fa-check me-1"></i>Guardado';
                saveBtn.className = 'btn btn-success btn-sm save-member-btn';
                // Re-enable after a moment for potential edits
                setTimeout(() => {
                    saveBtn.disabled = false;
                    saveBtn.innerHTML = '<i class="fas fa-edit me-1"></i>Actualizar';
                    saveBtn.className = 'btn btn-outline-success btn-sm save-member-btn';
                }, 2000);
            } else if (status === 'error') {
                saveBtn.disabled = false;
                saveBtn.innerHTML = '<i class="fas fa-retry me-1"></i>Reintentar';
                saveBtn.className = 'btn btn-danger btn-sm save-member-btn';
            } else {
                saveBtn.disabled = false;
                saveBtn.innerHTML = '<i class="fas fa-save me-1"></i>Guardar Miembro';
                saveBtn.className = 'btn btn-success btn-sm save-member-btn';
            }
        }
    }    async saveMember(personaId) {
        console.log('Saving individual member:', personaId);
        
        const card = document.querySelector(`.member-card[data-persona-id="${personaId}"]`);
        if (!card) {
            console.error('Member card not found for persona:', personaId);
            return;
        }

        // Validate member data first
        const memberData = this.getMemberData(personaId);
        if (!memberData) {
            this.updateMemberStatus(personaId, 'error', 'Error: Datos incompletos', 'danger');
            return;
        }

        this.updateMemberStatus(personaId, 'saving', 'Guardando...', 'primary');

        const concursoId = window.tribunalConcursoId || this.getConcursoIdFromUrl();
        
        try {
            const response = await fetch(`/tribunal/concurso/${concursoId}/agregar`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    members: [memberData]
                })
            });

            console.log('Save response status:', response.status);
            
            if (response.ok) {
                const result = await response.json();
                console.log('Save response:', result);
                
                if (result.success) {
                    this.updateMemberStatus(personaId, 'saved', 'Guardado exitosamente', 'success');
                    
                    // Store the member ID if returned
                    if (result.members && result.members[0] && result.members[0].id) {
                        card.dataset.miembroId = result.members[0].id;
                    }
                    
                    // Show success message
                    this.showMessage('Miembro guardado exitosamente', 'success');
                } else {
                    this.updateMemberStatus(personaId, 'error', result.message || 'Error al guardar', 'danger');
                    this.showMessage(result.message || 'Error al guardar el miembro', 'danger');
                }
            } else {
                const errorText = await response.text();
                console.error('Save error response:', errorText);
                this.updateMemberStatus(personaId, 'error', 'Error del servidor', 'danger');
                this.showMessage('Error del servidor al guardar el miembro', 'danger');
            }
        } catch (error) {
            console.error('Error saving member:', error);
            this.updateMemberStatus(personaId, 'error', 'Error de conexión', 'danger');
            this.showMessage('Error de conexión al guardar el miembro', 'danger');
        }
    }    getMemberData(personaId) {
        console.log('getMemberData called for persona:', personaId);
        // Use more specific selector to find only the member card, not other elements
        const card = document.querySelector(`.member-card[data-persona-id="${personaId}"]`);
        if (!card) {
            console.error('Member card not found for persona:', personaId);
            // Try fallback selector
            const anyCard = document.querySelector(`[data-persona-id="${personaId}"]`);
            console.log('Found any element with persona ID:', anyCard);
            return null;
        }

        console.log('Member card found:', card);
        console.log('Card dataset:', card.dataset);
        console.log('Looking for selectors in card...');

        const rolSelect = card.querySelector('.rol-select');
        const claustroSelect = card.querySelector('.claustro-select');
        
        console.log('rolSelect found:', !!rolSelect);
        console.log('rolSelect element:', rolSelect);
        console.log('rolSelect value:', rolSelect?.value);
        console.log('claustroSelect found:', !!claustroSelect);
        console.log('claustroSelect element:', claustroSelect);
        console.log('claustroSelect value:', claustroSelect?.value);
        
        // Try alternative selectors if the primary ones fail
        if (!rolSelect) {
            const altRolSelect = card.querySelector('select[class*="rol"]');
            console.log('Alternative rol selector found:', !!altRolSelect);
            if (altRolSelect) {
                console.log('Alternative rol selector classes:', altRolSelect.className);
                console.log('Alternative rol selector value:', altRolSelect.value);
            }
        }
        
        if (!rolSelect?.value) {
            this.showMessage('Por favor seleccione un rol para el miembro', 'warning');
            return null;
        }

        // Get permissions
        const canAddTema = card.querySelector('.can-add-tema')?.checked || false;
        const canUploadFile = card.querySelector('.can-upload-file')?.checked || false;
        const canSignFile = card.querySelector('.can-sign-file')?.checked || false;
        const canViewDocs = card.querySelector('.can-view-postulante-docs')?.checked || false;

        const memberData = {
            persona_id: parseInt(personaId),
            rol: rolSelect.value,
            claustro: claustroSelect?.value || 'Docente',
            can_add_tema: canAddTema,
            can_upload_file: canUploadFile,
            can_sign_file: canSignFile,
            can_view_postulante_docs: canViewDocs
        };
        
        console.log('Prepared member data:', memberData);
        return memberData;
    }

    getConcursoIdFromUrl() {
        const pathParts = window.location.pathname.split('/');
        const concursoIndex = pathParts.indexOf('concurso');
        return concursoIndex !== -1 && pathParts[concursoIndex + 1] ? pathParts[concursoIndex + 1] : null;
    }

    showMessage(message, type = 'info') {
        // Create toast notification or use existing notification system
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; max-width: 400px;';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(alertDiv);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }
    
    validateMembers() {
        const cards = document.querySelectorAll('.member-card');
        let allValid = true;
        
        cards.forEach(card => {
            const rolSelect = card.querySelector('.rol-select');
            const claustroSelect = card.querySelector('.claustro-select');
            
            if (!rolSelect || !claustroSelect || !rolSelect.value || !claustroSelect.value) {
                allValid = false;
            }
        });
        
        // Update save button
        const saveBtn = document.getElementById('saveAllMembers');
        if (saveBtn) {
            saveBtn.disabled = cards.length === 0 || !allValid;
        }
        
        return allValid;
    }
    
    updateUI() {
        const count = this.selectedMembers.size;
        
        // Update member count badge
        const countBadge = document.getElementById('memberCount');
        if (countBadge) {
            countBadge.textContent = count;
        }
        
        // Show/hide no members message
        const noMembersMsg = document.getElementById('noMembersMsg');
        if (noMembersMsg) {
            noMembersMsg.style.display = count === 0 ? 'block' : 'none';
        }
        
        // Enable/disable save button
        const saveBtn = document.getElementById('saveAllMembers');
        if (saveBtn) {
            saveBtn.disabled = count === 0;
        }
        
        console.log('UI updated - member count:', count);
    }
    
    showAlert(message, type = 'info') {
        const alertArea = document.getElementById('alertArea');
        if (!alertArea) {
            console.error('Alert area not found');
            return;
        }
        
        const alertId = 'alert-' + Date.now();
        const alertHtml = `
            <div id="${alertId}" class="alert alert-${type} alert-dismissible fade show" role="alert">
                <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'warning' ? 'exclamation-triangle' : type === 'danger' ? 'exclamation-circle' : 'info-circle'} me-2"></i>
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
        
        alertArea.insertAdjacentHTML('beforeend', alertHtml);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            const alert = document.getElementById(alertId);
            if (alert) {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }
        }, 5000);
    }
}

// Export for use in other modules
window.TribunalSelectedMembersManager = TribunalSelectedMembersManager;
