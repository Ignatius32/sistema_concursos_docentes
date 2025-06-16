/**
 * Unified Tribunal Member Manager
 * Handles both new and existing tribunal members with consistent logic
 */
console.log('Loading Unified TribunalMemberManager v4.0');

class UnifiedTribunalMemberManager {
    constructor() {
        this.selectedMembers = new Map(); // For new members before saving
        this.existingMembers = new Map(); // For tracking existing member changes
        this.concursoId = this.getConcursoId();
        this.searchManager = null; // Search manager instance
        this.init();
    }    init() {
        try {
            console.log('Current URL:', window.location.pathname);
            console.log('Extracted concurso ID:', this.concursoId);
            
            // Initialize search manager
            this.initializeSearchManager();
            
            this.bindEvents();
            this.loadExistingMembers();
            this.updateUI();
            console.log('UnifiedTribunalMemberManager initialized');
        } catch (error) {
            console.error('UnifiedTribunalMemberManager initialization error:', error);
        }
    }getConcursoId() {
        // Match the pattern /tribunal/concurso/{id}/agregar
        const pathMatch = window.location.pathname.match(/\/tribunal\/concurso\/(\d+)/);
        return pathMatch ? pathMatch[1] : null;
    }

    bindEvents() {
        // Listen for member addition events from search
        document.addEventListener('memberAdd', (e) => {
            this.addNewMember(e.detail.persona);
        });

        // Use event delegation for all member actions
        document.addEventListener('click', (e) => {
            const action = this.getActionFromEvent(e);
            if (action) {
                this.handleAction(action, e);
            }
        });

        // Handle form changes
        document.addEventListener('change', (e) => {
            if (e.target.closest('.member-card')) {
                this.handleMemberFieldChange(e);
            }
        });

        // Clear all button
        const clearAllBtn = document.getElementById('clearAll');
        if (clearAllBtn) {
            clearAllBtn.addEventListener('click', () => this.clearAllNewMembers());
        }

        console.log('Unified event handlers bound');
    }

    getActionFromEvent(e) {
        const target = e.target.closest('[data-action]') || e.target.closest('.save-member, .edit-member, .cancel-member, .remove-member');
        
        if (!target) return null;

        if (target.classList.contains('save-member')) return 'save';
        if (target.classList.contains('edit-member')) return 'edit';
        if (target.classList.contains('cancel-member')) return 'cancel';
        if (target.classList.contains('remove-member')) {
            return target.dataset.action === 'remove-existing' ? 'remove-existing' : 'remove-new';
        }

        return target.dataset.action;
    }

    handleAction(action, e) {
        const card = e.target.closest('.member-card');
        if (!card) return;

        const memberId = card.dataset.memberId;
        const memberType = card.dataset.memberType;

        console.log(`Handling action: ${action} for member ${memberId} (type: ${memberType})`);

        switch (action) {
            case 'save':
                this.saveMember(card);
                break;
            case 'edit':
                this.editMember(card);
                break;
            case 'cancel':
                this.cancelMemberChanges(card);
                break;
            case 'remove-new':
                this.removeNewMember(memberId);
                break;
            case 'remove-existing':
                this.removeExistingMember(memberId, card);
                break;
        }
    }

    // NEW MEMBER METHODS
    addNewMember(persona) {
        console.log('Adding new member:', persona);
        
        // Check if already added
        if (this.selectedMembers.has(persona.id)) {
            this.showAlert(`${persona.nombre} ${persona.apellido} ya está en la lista`, 'warning');
            return;
        }

        // Add to selected members
        this.selectedMembers.set(persona.id, persona);
        
        // Create and add card
        this.createMemberCard(persona, 'new');
        
        // Update UI
        this.updateUI();
        this.clearSearch();
        
        this.showAlert(`${persona.nombre} ${persona.apellido} agregado al tribunal`, 'success');
    }

    removeNewMember(personaId) {
        const persona = this.selectedMembers.get(parseInt(personaId));
        if (!persona) return;

        this.selectedMembers.delete(parseInt(personaId));
        
        // Remove card from DOM
        const card = document.querySelector(`[data-member-id="${personaId}"][data-member-type="new"]`);
        if (card) {
            card.closest('.col-md-6').remove();
        }

        this.updateUI();
        this.showAlert(`${persona.nombre} ${persona.apellido} removido del tribunal`, 'info');
    }

    clearAllNewMembers() {
        this.selectedMembers.clear();
        
        // Remove all new member cards
        const newMemberCards = document.querySelectorAll('[data-member-type="new"]');
        newMemberCards.forEach(card => card.closest('.col-md-6').remove());
        
        this.updateUI();
        this.showAlert('Todos los miembros nuevos han sido removidos', 'info');
    }

    // EXISTING MEMBER METHODS
    loadExistingMembers() {
        const existingCards = document.querySelectorAll('[data-member-type="existing"]');
        existingCards.forEach(card => {
            const memberId = card.dataset.memberId;
            this.existingMembers.set(memberId, this.getOriginalMemberData(card));
        });
    }

    getOriginalMemberData(card) {
        return {
            rol: card.querySelector('.member-rol').value,
            claustro: card.querySelector('.member-claustro').value,
            can_add_tema: card.querySelector('.member-can-add-tema').checked,
            can_upload_file: card.querySelector('.member-can-upload-file').checked,
            can_sign_file: card.querySelector('.member-can-sign-file').checked,
            can_view_postulante_docs: card.querySelector('.member-can-view-postulante-docs').checked
        };
    }

    editMember(card) {
        const memberType = card.dataset.memberType;
        
        if (memberType === 'existing') {
            // Enable form fields
            this.enableMemberFields(card, true);
            
            // Show existing member actions, hide status
            card.querySelector('.existing-member-actions').classList.remove('d-none');
            card.querySelector('.new-member-actions').classList.add('d-none');
            
            // Update header
            this.updateMemberHeader(card, 'editing', 'Editando...');
            
            // Add visual indicator
            card.classList.add('border-primary');
            
            // Close dropdown
            this.closeDropdown(card);
        }
    }

    cancelMemberChanges(card) {
        const memberId = card.dataset.memberId;
        const memberType = card.dataset.memberType;
        
        if (memberType === 'existing') {
            // Restore original values
            const originalData = this.existingMembers.get(memberId);
            if (originalData) {
                this.restoreMemberData(card, originalData);
            }
            
            // Disable form fields
            this.enableMemberFields(card, false);
            
            // Hide existing member actions
            card.querySelector('.existing-member-actions').classList.add('d-none');
            
            // Update header
            this.updateMemberHeader(card, 'saved', 'Guardado');
            
            // Remove visual indicators
            card.classList.remove('border-primary', 'border-warning');
        }
    }

    removeExistingMember(memberId, card) {
        const memberName = card.querySelector('.member-name').textContent;
        
        if (!confirm(`¿Está seguro que desea eliminar a ${memberName} del tribunal?`)) {
            return;
        }

        this.deleteMemberFromServer(memberId, card);
    }

    // UNIFIED SAVE METHOD
    async saveMember(card) {
        const memberId = card.dataset.memberId;
        const memberType = card.dataset.memberType;
        
        console.log(`Saving member ${memberId} (type: ${memberType})`);
        
        // Get member data from form
        const memberData = this.getMemberDataFromCard(card);
        
        // Validate data
        if (!this.validateMemberData(memberData)) {
            this.showAlert('Por favor complete todos los campos requeridos', 'error');
            return;
        }

        try {
            // Update UI to show saving state
            this.updateMemberHeader(card, 'saving', 'Guardando...');
            this.disableMemberActions(card, true);
            
            let response;
            
            if (memberType === 'new') {
                response = await this.saveNewMember(memberId, memberData);
            } else if (memberType === 'existing') {
                response = await this.updateExistingMember(memberId, memberData);
            }
            
            if (response && response.success) {
                await this.handleSaveSuccess(card, memberType, response);
            } else {
                throw new Error(response?.message || 'Error al guardar');
            }
            
        } catch (error) {
            console.error('Save error:', error);
            this.handleSaveError(card, error);
        }
    }    async saveNewMember(personaId, memberData) {
        console.log('Saving new member to server:', personaId, memberData);
        
        const url = `/tribunal/concurso/${this.concursoId}/tribunal/add`;
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                persona_id: parseInt(personaId),
                ...memberData
            })
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error('Server response:', response.status, errorText);
            throw new Error(`Error ${response.status}: ${errorText}`);
        }

        const data = await response.json();
        return data;
    }    async updateExistingMember(miembroId, memberData) {
        console.log('Updating existing member on server:', miembroId, memberData);
        
        const url = `/tribunal/concurso/${this.concursoId}/tribunal/edit/${miembroId}`;
        const response = await fetch(url, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(memberData)
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error('Server response:', response.status, errorText);
            throw new Error(`Error ${response.status}: ${errorText}`);
        }

        const data = await response.json();
        return data;
    }    async deleteMemberFromServer(miembroId, card) {
        try {
            const url = `/tribunal/concurso/${this.concursoId}/tribunal/delete/${miembroId}`;
            const response = await fetch(url, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                const errorText = await response.text();
                console.error('Server response:', response.status, errorText);
                throw new Error(`Error ${response.status}: ${errorText}`);
            }

            const data = await response.json();
            
            if (data.success) {
                // Remove card from DOM
                card.closest('.col-md-6').remove();
                this.existingMembers.delete(miembroId);
                this.showAlert('Miembro eliminado del tribunal', 'success');
            } else {
                throw new Error(data.message || 'Error al eliminar');
            }
            
        } catch (error) {
            console.error('Delete error:', error);
            this.showAlert('Error al eliminar miembro: ' + error.message, 'error');
        }
    }    async handleSaveSuccess(card, memberType, response) {
        console.log('Save success for', memberType, 'member:', response);
        
        if (memberType === 'new') {
            // Convert new member card to existing member card
            await this.convertNewToExistingMember(card, response.miembro);
            // Don't re-enable member actions for converted cards since they're now existing members
        } else {
            // Update existing member data
            const memberId = card.dataset.memberId;
            this.existingMembers.set(memberId, this.getMemberDataFromCard(card));
            
            // Disable form fields
            this.enableMemberFields(card, false);
            
            // Hide existing member save/cancel actions
            card.querySelector('.existing-member-actions').classList.add('d-none');
            
            // Update header
            this.updateMemberHeader(card, 'saved', 'Guardado');
            
            // Remove visual indicators
            card.classList.remove('border-primary', 'border-warning');
            
            // Re-enable action buttons (but not form fields)
            this.disableMemberActions(card, false);
        }
        
        this.showAlert('Miembro guardado correctamente', 'success');
    }

    handleSaveError(card, error) {
        // Update header
        this.updateMemberHeader(card, 'error', 'Error al guardar');
        
        // Re-enable actions
        this.disableMemberActions(card, false);
        
        this.showAlert('Error al guardar: ' + error.message, 'error');
    }    async convertNewToExistingMember(card, miembroData) {
        console.log('Converting new member to existing member:', miembroData);
        console.log('Card before conversion:', card);
        
        // Remove from selected members
        const personaId = card.dataset.memberId;
        this.selectedMembers.delete(parseInt(personaId));
        
        // Update card data
        card.dataset.memberId = miembroData.id;
        card.dataset.memberType = 'existing';
        
        // Add to existing members
        this.existingMembers.set(miembroData.id.toString(), this.getMemberDataFromCard(card));
        
        // Hide new member elements
        const removeButton = card.querySelector('.remove-member[data-action="remove-new"]');
        const newActions = card.querySelector('.new-member-actions');
        
        if (removeButton) {
            removeButton.classList.add('d-none');
            console.log('Hidden remove button');
        }
        
        if (newActions) {
            newActions.classList.add('d-none');
            console.log('Hidden new member actions');
        }
        
        // Show existing member elements
        const existingActions = card.querySelector('.existing-actions');
        if (existingActions) {
            existingActions.classList.remove('d-none');
            console.log('Shown existing actions dropdown');
        }
        
        // Update header styling to existing member style
        const header = card.querySelector('.member-header');
        header.classList.remove('bg-warning', 'text-dark');
        header.classList.add('bg-secondary', 'text-white');
        
        // Update card border
        card.classList.remove('border-warning');
        card.classList.add('border-secondary');
        
        // Disable all form fields (existing members start disabled)
        this.enableMemberFields(card, false);
        
        // Update status to saved
        this.updateMemberHeader(card, 'saved', 'Guardado');
        
        // Update UI counts
        this.updateUI();
        
        console.log('Successfully converted card to existing member');
        console.log('Card after conversion:', card);
    }

    // CARD MANAGEMENT METHODS
    createMemberCard(persona, memberType, miembroData = null) {
        const template = document.getElementById('unifiedMemberCardTemplate');
        if (!template) {
            console.error('Unified member card template not found');
            return;
        }
        
        const clone = template.content.cloneNode(true);
        const card = clone.querySelector('.member-card');
        
        // Set basic data
        if (memberType === 'new') {
            card.dataset.memberId = persona.id;
            card.dataset.memberType = 'new';
            this.setupNewMemberCard(card, persona);
        } else {
            card.dataset.memberId = miembroData.id;
            card.dataset.memberType = 'existing';
            this.setupExistingMemberCard(card, persona, miembroData);
        }
          // Add to unified container
        const container = document.getElementById('tribunalMembersList');
            
        if (container) {
            container.appendChild(clone);
        }
    }    setupNewMemberCard(card, persona) {
        // Set persona data
        card.querySelector('.member-name').textContent = `${persona.apellido}, ${persona.nombre}`;
        card.querySelector('.member-details').textContent = `DNI: ${persona.dni}${persona.correo ? ' - ' + persona.correo : ''}`;
        
        // Show new member actions
        card.querySelector('.remove-member[data-action="remove-new"]').classList.remove('d-none');
        card.querySelector('.new-member-actions').classList.remove('d-none');
        
        // Set header styling
        card.querySelector('.member-header').classList.add('bg-warning', 'text-dark');
        card.classList.add('border-warning');
        
        // Enable all fields
        this.enableMemberFields(card, true);
        
        // Apply default permissions for the default role (Titular)
        this.applyDefaultPermissions(card);
        
        // Set up change handlers for role and claustro
        this.setupPermissionHandlers(card);
    }    setupExistingMemberCard(card, persona = null, miembroData = null) {
        if (persona && miembroData) {
            // Set persona data
            card.querySelector('.member-name').textContent = `${persona.apellido}, ${persona.nombre}`;
            card.querySelector('.member-details').textContent = `DNI: ${persona.dni}${persona.correo ? ' - ' + persona.correo : ''}`;
            
            // Set form values
            this.restoreMemberData(card, miembroData);
        }
        
        // Show existing member actions
        card.querySelector('.existing-actions').classList.remove('d-none');
        
        // Set header styling
        card.querySelector('.member-header').classList.add('bg-secondary', 'text-white');
        card.classList.add('border-secondary');
        
        // Disable all fields initially
        this.enableMemberFields(card, false);
        
        // Update status
        this.updateMemberHeader(card, 'saved', 'Guardado');
        
        // Set up change handlers for role and claustro when editing
        this.setupPermissionHandlers(card);    }

    // PERMISSION MANAGEMENT METHODS
    setupPermissionHandlers(card) {
        const rolSelect = card.querySelector('.member-rol');
        const claustroSelect = card.querySelector('.member-claustro');
        
        if (rolSelect) {
            rolSelect.addEventListener('change', (e) => {
                this.applyDefaultPermissions(card);
                // Also trigger the field change handler for existing members
                this.handleMemberFieldChange(e);
            });
        }
        
        if (claustroSelect) {
            claustroSelect.addEventListener('change', (e) => {
                this.applyDefaultPermissions(card);
                // Also trigger the field change handler for existing members
                this.handleMemberFieldChange(e);
            });
        }
    }
    
    applyDefaultPermissions(card) {
        const rol = card.querySelector('.member-rol').value;
        const claustro = card.querySelector('.member-claustro').value;
        
        const permissions = this.getDefaultPermissions(rol, claustro);
        
        // Apply permissions to checkboxes
        card.querySelector('.member-can-add-tema').checked = permissions.can_add_tema;
        card.querySelector('.member-can-upload-file').checked = permissions.can_upload_file;
        card.querySelector('.member-can-sign-file').checked = permissions.can_sign_file;
        card.querySelector('.member-can-view-postulante-docs').checked = permissions.can_view_postulante_docs;
        
        // Add visual feedback
        const permissionsSection = card.querySelector('.member-permissions');
        if (permissionsSection) {
            permissionsSection.classList.add('permissions-updated');
            setTimeout(() => {
                permissionsSection.classList.remove('permissions-updated');
            }, 1000);
        }
    }
    
    getDefaultPermissions(rol, claustro = 'Docente') {
        let basePermissions;
        
        switch (rol) {
            case 'Presidente':
                basePermissions = {
                    can_add_tema: true,
                    can_upload_file: true,
                    can_sign_file: true,
                    can_view_postulante_docs: true
                };
                break;
            case 'Titular':
                basePermissions = {
                    can_add_tema: false,
                    can_upload_file: false,
                    can_sign_file: true,
                    can_view_postulante_docs: true
                };
                break;
            case 'Suplente':
            case 'Veedor':
            default:
                basePermissions = {
                    can_add_tema: false,
                    can_upload_file: false,
                    can_sign_file: false,
                    can_view_postulante_docs: false
                };
                break;
        }
        
        // Estudiantes have more restricted permissions
        if (claustro === 'Estudiante') {
            basePermissions.can_sign_file = false;
            if (rol !== 'Presidente') {
                basePermissions.can_add_tema = false;
                basePermissions.can_upload_file = false;
            }
        }
        
        return basePermissions;
    }

    // UTILITY METHODS
    enableMemberFields(card, enable) {
        const fields = card.querySelectorAll('.member-rol, .member-claustro, .member-can-add-tema, .member-can-upload-file, .member-can-sign-file, .member-can-view-postulante-docs');
        fields.forEach(field => field.disabled = !enable);
    }

    disableMemberActions(card, disable) {
        const buttons = card.querySelectorAll('.save-member, .edit-member, .cancel-member, .remove-member');
        buttons.forEach(btn => btn.disabled = disable);
    }

    updateMemberHeader(card, status, text) {
        const statusElement = card.querySelector('.member-status');
        const iconMap = {
            'pending': 'fas fa-clock',
            'saving': 'fas fa-spinner fa-spin',
            'editing': 'fas fa-edit',
            'saved': 'fas fa-check',
            'error': 'fas fa-exclamation-triangle'
        };
        
        statusElement.innerHTML = `<i class="${iconMap[status] || 'fas fa-info'} me-1"></i>${text}`;
    }

    getMemberDataFromCard(card) {
        return {
            rol: card.querySelector('.member-rol').value,
            claustro: card.querySelector('.member-claustro').value,
            can_add_tema: card.querySelector('.member-can-add-tema').checked,
            can_upload_file: card.querySelector('.member-can-upload-file').checked,
            can_sign_file: card.querySelector('.member-can-sign-file').checked,
            can_view_postulante_docs: card.querySelector('.member-can-view-postulante-docs').checked
        };
    }    restoreMemberData(card, data) {
        card.querySelector('.member-rol').value = data.rol || 'Titular';
        card.querySelector('.member-claustro').value = data.claustro || 'Docente';
        card.querySelector('.member-can-add-tema').checked = data.can_add_tema || false;
        card.querySelector('.member-can-upload-file').checked = data.can_upload_file || false;
        card.querySelector('.member-can-sign-file').checked = data.can_sign_file || false;
        card.querySelector('.member-can-view-postulante-docs').checked = data.can_view_postulante_docs || false;
    }

    validateMemberData(data) {
        return data.rol && data.claustro;
    }    handleMemberFieldChange(e) {
        const card = e.target.closest('.member-card');
        const memberType = card.dataset.memberType;
        const fieldName = e.target.className;
        
        // Handle role and claustro changes for permission updates
        if (fieldName.includes('member-rol') || fieldName.includes('member-claustro')) {
            console.log('Role or claustro changed, applying default permissions');
            this.applyDefaultPermissions(card);
        }
        
        if (memberType === 'existing') {
            // Show save/cancel buttons for existing members
            card.querySelector('.existing-member-actions').classList.remove('d-none');
            card.classList.add('border-warning');
        }
    }

    closeDropdown(card) {
        const dropdown = card.querySelector('.dropdown');
        if (dropdown) {
            const dropdownToggle = dropdown.querySelector('[data-bs-toggle="dropdown"]');
            if (dropdownToggle && window.bootstrap?.Dropdown) {
                const dropdownInstance = window.bootstrap.Dropdown.getInstance(dropdownToggle);
                if (dropdownInstance) {
                    dropdownInstance.hide();
                }
            }
        }
    }    clearSearch() {
        if (this.searchManager) {
            this.searchManager.clearSearch();
        } else {
            // Fallback to direct DOM manipulation
            const personaSearch = document.getElementById('personaSearch');
            if (personaSearch) {
                personaSearch.value = '';
            }
            
            const searchResults = document.getElementById('searchResults');
            if (searchResults) {
                searchResults.style.display = 'none';
            }
        }
    }    updateUI() {
        // Update counters for unified section
        const totalCount = document.getElementById('totalMemberCount');
        const newCount = document.getElementById('newMemberCount');
        const existingCount = document.getElementById('existingMemberCount');
        
        const newMembersSize = this.selectedMembers.size;
        const existingMembersSize = this.existingMembers.size;
        const totalMembersSize = newMembersSize + existingMembersSize;
        
        if (totalCount) {
            totalCount.textContent = totalMembersSize;
        }
        
        if (newCount) {
            newCount.textContent = newMembersSize;
        }
        
        if (existingCount) {
            existingCount.textContent = existingMembersSize;
        }
        
        // Show/hide no members message
        const noMembersMsg = document.getElementById('noMembersMsg');
        if (noMembersMsg) {
            noMembersMsg.style.display = totalMembersSize === 0 ? 'block' : 'none';
        }
    }getCSRFToken() {
        // Try to get CSRF token from meta tag
        const token = document.querySelector('meta[name="csrf-token"]');
        if (token) {
            return token.getAttribute('content');
        }
        
        // Try to get from hidden input
        const hiddenInput = document.querySelector('input[name="csrf_token"]');
        if (hiddenInput) {
            return hiddenInput.value;
        }
        
        // Try to get from session cookie or form
        const forms = document.querySelectorAll('form');
        for (let form of forms) {
            const csrfInput = form.querySelector('input[name="csrf_token"]');
            if (csrfInput) {
                return csrfInput.value;
            }
        }
        
        console.warn('CSRF token not found');
        return '';
    }

    showAlert(message, type = 'info') {
        const alertArea = document.getElementById('alertArea');
        if (!alertArea) return;

        const alertClass = {
            'success': 'alert-success',
            'error': 'alert-danger',
            'warning': 'alert-warning',
            'info': 'alert-info'
        }[type] || 'alert-info';

        const alertHTML = `
            <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;

        alertArea.innerHTML = alertHTML;

        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            const alert = alertArea.querySelector('.alert');
            if (alert && window.bootstrap?.Alert) {
                const bsAlert = new window.bootstrap.Alert(alert);
                bsAlert.close();
            }
        }, 5000);
    }

    initializeSearchManager() {
        if (window.TribunalSearchManager && this.concursoId) {
            this.searchManager = new window.TribunalSearchManager(this.concursoId);
            console.log('Search manager initialized with concurso ID:', this.concursoId);
        } else {
            console.error('TribunalSearchManager not available or concurso ID missing');
            if (!window.TribunalSearchManager) {
                console.error('TribunalSearchManager class not found');
            }
            if (!this.concursoId) {
                console.error('Concurso ID not found in URL');
            }
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.tribunalManager = new UnifiedTribunalMemberManager();
});
