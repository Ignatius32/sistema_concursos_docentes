// This script handles the automatic opening of the notification modal when the URL has #notificacionesModal
document.addEventListener('DOMContentLoaded', function() {
    // Check if URL hash is #notificacionesModal
    if (window.location.hash === '#notificacionesModal') {
        // Open the modal
        var notificacionesModal = new bootstrap.Modal(document.getElementById('notificacionesModal'));
        notificacionesModal.show();
    }
});
