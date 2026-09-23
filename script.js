// Modales de servicio: el contenido lo genera build.py desde
// content/home.yml (edición en Pages CMS) y se publica como _site/data.js,
// que se carga antes que este archivo. Sin data.js (preview sin build) la
// página carga, pero los modales no tienen contenido.
// El contacto NO se gestiona aquí: build.py lo escribe directamente en
// index.html (huecos .neuro-*) desde content/settings.yml.
const siteData = window.SITE_DATA || {};

function openServiceModal(key) {
    const info = siteData.services && siteData.services[key];
    if (!info) return;
    const icons = siteData.icons || {};
    document.getElementById('modalIcon').innerHTML = icons[info.icon] || '';
    document.getElementById('modalTitle').textContent = info.title;
    document.getElementById('modalBody').innerHTML = info.html;
    document.getElementById('serviceModal').showModal();
}

function closeServiceModal() {
    document.getElementById('serviceModal').close();
}

function toggleMenu() {
    const menu = document.getElementById('mobileMenu');
    menu.classList.toggle('active');
    document.body.style.overflow = menu.classList.contains('active') ? 'hidden' : 'auto';
}

document.getElementById('serviceModal').addEventListener('click', function (event) {
    if (event.target === this) closeServiceModal();
});
