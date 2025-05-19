// Function to batch fetch programa information for all asignaturas
function fetchAllProgramasInfo() {
    // Collect all materia IDs
    const materiaElements = document.querySelectorAll('.programa-button-container[data-id-materia]');
    const materiaIds = Array.from(materiaElements).map(el => el.dataset.idMateria);
    
    if (materiaIds.length === 0) return;
    
    console.log(`Batch fetching programa info for ${materiaIds.length} materias`);
    
    // Show individual loading indicators for each card and hide buttons
    materiaElements.forEach(container => {
        const button = container.querySelector('.download-programa-btn');
        const loadingIndicator = container.querySelector('.programa-loading-indicator');
        
        if (button && loadingIndicator) {
            button.classList.add('d-none');
            loadingIndicator.classList.remove('d-none');
        }
    });
    
    // Make bulk request
    fetch('/api/programas-bulk', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ materia_ids: materiaIds })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            console.log('Bulk programa fetch completed successfully');
            
            // Process each result
            for (const [materiaId, info] of Object.entries(data.results)) {
                const container = document.querySelector(`.programa-button-container[data-id-materia="${materiaId}"]`);
                if (!container) continue;
                
                const button = container.querySelector('.download-programa-btn');
                const loadingIndicator = container.querySelector('.programa-loading-indicator');
                
                // Hide loading indicator
                if (loadingIndicator) {
                    loadingIndicator.classList.add('d-none');
                }
                  // Update UI based on result
                if (info.status === 'success' && info.download_url) {
                    // Replace button with direct download link - full width green button
                    container.innerHTML = `
                        <a href="${info.download_url}" target="_blank" 
                            class="btn btn-success w-100 download-programa-btn">
                            <i class="bi bi-file-earmark-arrow-down"></i> Descargar programa
                        </a>
                    `;
                } else if (info.status === 'not_found' || info.status === 'error') {
                    // Program not found, show full width grey button with manual search link
                    const manualUrl = info.manual_url || "https://huayca.crub.uncoma.edu.ar/programas/";
                    container.innerHTML = `
                        <a href="${manualUrl}" target="_blank" 
                            class="btn btn-secondary w-100 text-wrap">
                            <i class="bi bi-search"></i> Programa no encontrado automáticamente, por favor haga una búsqueda manual en este enlace
                        </a>
                    `;
                } else {
                    // Error or unknown state, show the original button
                    if (button) {
                        button.classList.remove('d-none');
                    }
                }
            }        } else {
            console.error('Bulk programa fetch failed:', data.message);
            
            // Show all buttons again and hide loading indicators
            materiaElements.forEach(container => {
                const button = container.querySelector('.download-programa-btn');
                const loadingIndicator = container.querySelector('.programa-loading-indicator');
                
                if (loadingIndicator) {
                    loadingIndicator.classList.add('d-none');
                }
                
                // Replace with "Error" button for manual search
                const manualUrl = "https://huayca.crub.uncoma.edu.ar/programas/";
                container.innerHTML = `
                    <a href="${manualUrl}" target="_blank" 
                        class="btn btn-secondary w-100 text-wrap">
                        <i class="bi bi-search"></i> Error al buscar programa, por favor haga una búsqueda manual en este enlace
                    </a>
                `;
            });
        }
    })
    .catch(error => {
        console.error('Error in bulk programa fetch:', error);
        
        // Show all buttons again and hide loading indicators
        materiaElements.forEach(container => {
            const button = container.querySelector('.download-programa-btn');
            const loadingIndicator = container.querySelector('.programa-loading-indicator');
            
            if (loadingIndicator) {
                loadingIndicator.classList.add('d-none');
            }
            
            // Replace with "Error" button for manual search
            const manualUrl = "https://huayca.crub.uncoma.edu.ar/programas/";
            container.innerHTML = `
                <a href="${manualUrl}" target="_blank" 
                    class="btn btn-secondary w-100 text-wrap">
                    <i class="bi bi-search"></i> Error al buscar programa, por favor haga una búsqueda manual en este enlace
                </a>
            `;
        });
    });
}

// Start the batch fetch when the asignaturas tab is clicked
document.addEventListener('DOMContentLoaded', function() {
    // Find the asignaturas tab
    const asignaturasTab = document.getElementById('asignaturas-externas-tab');
    
    if (asignaturasTab) {
        // Add click event listener to the tab
        asignaturasTab.addEventListener('shown.bs.tab', function() {
            // Start the batch fetch when the tab is shown
            fetchAllProgramasInfo();
        });
    }
    
    // If the tab is already active on page load, fetch the data
    if (asignaturasTab && asignaturasTab.classList.contains('active')) {
        setTimeout(fetchAllProgramasInfo, 500);
    }
});
