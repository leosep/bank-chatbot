document.addEventListener('DOMContentLoaded', () => {
    console.log('Scripts para el panel de agentes cargados.');

    // No hay scripts avanzados necesarios por ahora, pero este archivo está listo para el futuro.
    // Ejemplo de funcionalidad que podrías añadir:
    // - Abrir y cerrar modales para editar resoluciones.
    // - Validar formularios antes de enviarlos.
    
    // Función para mostrar/ocultar el formulario de resolución en la página de llamadas
    // Esta es una mejora opcional para la usabilidad.
    const resolutionForms = document.querySelectorAll('.resolution-form');

    resolutionForms.forEach(form => {
        const resolutionTextarea = form.querySelector('textarea[name="resolution"]');
        if (resolutionTextarea.value.trim() !== '') {
            form.style.display = 'flex'; // Muestra el formulario si ya hay una resolución
        } else {
            form.style.display = 'none'; // Oculta el formulario si está vacío
        }
    });

    const callCards = document.querySelectorAll('.call-card');
    callCards.forEach(card => {
        card.addEventListener('click', (event) => {
            // Previene que el clic en los elementos internos active el evento del padre
            if (!event.target.closest('form')) {
                // Alternar la visibilidad del formulario de resolución
                const form = card.querySelector('.resolution-form');
                if (form) {
                    form.style.display = form.style.display === 'flex' ? 'none' : 'flex';
                }
            }
        });
    });
});