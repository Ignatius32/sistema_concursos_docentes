document.addEventListener('DOMContentLoaded', function() {
    const departamentoSelect = document.getElementById('departamento_id');
    const areaSelect = document.getElementById('area');
    const orientacionSelect = document.getElementById('orientacion');
    let deptosData = null;

    // Fetch the JSON data
    fetch('/static/DEPTOS_AREAS_ORIENTACIONES.json')
        .then(response => response.json())
        .then(data => {
            deptosData = data;
            setupDepartamentoChangeHandler();
        })
        .catch(error => console.error('Error loading departments data:', error));

    function setupDepartamentoChangeHandler() {
        if (!departamentoSelect || !areaSelect || !orientacionSelect) return;

        departamentoSelect.addEventListener('change', function() {
            const selectedDeptName = departamentoSelect.options[departamentoSelect.selectedIndex].text;
            updateAreasAndOrientaciones(selectedDeptName);
        });
    }

    function updateAreasAndOrientaciones(departamento) {
        // Clear current options
        areaSelect.innerHTML = '<option value="">Seleccione un área</option>';
        orientacionSelect.innerHTML = '<option value="">Seleccione una orientación</option>';

        if (!departamento || !deptosData) return;

        // Get unique areas for the selected department
        const areas = [...new Set(deptosData
            .filter(item => item.DEPARTAMENTO === departamento)
            .map(item => item.AREA))]
            .filter(area => area); // Remove undefined/null/empty

        // Add areas to select
        areas.forEach(area => {
            const option = document.createElement('option');
            option.value = area;
            option.textContent = area;
            areaSelect.appendChild(option);
        });

        // Setup area change handler
        areaSelect.addEventListener('change', function() {
            updateOrientaciones(departamento, this.value);
        });
    }

    function updateOrientaciones(departamento, area) {
        // Clear current orientaciones
        orientacionSelect.innerHTML = '<option value="">Seleccione una orientación</option>';

        if (!departamento || !area) return;

        // Get orientaciones for the selected department and area
        const orientaciones = [...new Set(deptosData
            .filter(item => item.DEPARTAMENTO === departamento && item.AREA === area)
            .map(item => item.ORIENTACION))]
            .filter(orientacion => orientacion); // Remove undefined/null/empty

        // Add orientaciones to select
        orientaciones.forEach(orientacion => {
            const option = document.createElement('option');
            option.value = orientacion;
            option.textContent = orientacion;
            orientacionSelect.appendChild(option);
        });
    }
});