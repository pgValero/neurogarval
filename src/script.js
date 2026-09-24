// Modales de servicios, modalidades y artículos del blog: el contenido lo
// genera build.py desde content/servicios.yml, content/modalidades.yml y
// content/blog.yml (edición en Pages CMS) y se publica como _site/data.js, que
// se carga antes que este archivo. Sin data.js (preview sin build) la página
// carga, pero los modales no tienen contenido.
// El contacto NO se gestiona aquí: build.py lo escribe directamente en
// index.html (huecos .neuro-*) desde content/common.yml.
const siteData = window.SITE_DATA || {};

function openServiceModal(key) {
    const info = siteData.services && siteData.services[key];
    if (!info) return;
    const icons = siteData.icons || {};
    document.getElementById('modalIcon').innerHTML = icons[info.icon] || '';
    document.getElementById('modalTitle').textContent = info.title;
    document.getElementById('modalBody').innerHTML = info.html;
    const modal = document.getElementById('serviceModal');
    if (!modal.open) modal.showModal();
}

function closeServiceModal() {
    const modal = document.getElementById('serviceModal');
    if (modal.open) modal.close();
}

function openModalityModal(key) {
    const info = siteData.modalities && siteData.modalities[key];
    if (!info) return;
    const icons = siteData.icons || {};
    document.getElementById('modalityModalIcon').innerHTML = icons[info.icon] || '';
    document.getElementById('modalityModalTitle').textContent = info.title;
    document.getElementById('modalityModalBody').innerHTML = info.html;
    const modal = document.getElementById('modalityModal');
    if (!modal.open) modal.showModal();
}

function closeModalityModal() {
    const modal = document.getElementById('modalityModal');
    if (modal.open) modal.close();
}

function openBlogModal(key) {
    const info = siteData.posts && siteData.posts[key];
    if (!info) return;
    const cover = document.getElementById('blogModalCover');
    cover.innerHTML = info.cover
        ? '<img src="' + info.cover + '" alt="' + info.title + '">'
        : '';
    cover.hidden = !info.cover;
    document.getElementById('blogModalTitle').textContent = info.title;
    document.getElementById('blogModalBody').innerHTML = info.html;
    const modal = document.getElementById('blogModal');
    if (!modal.open) modal.showModal();
}

function closeBlogModal() {
    const modal = document.getElementById('blogModal');
    if (modal.open) modal.close();
}

function toggleMenu() {
    const menu = document.getElementById('mobileMenu');
    menu.classList.toggle('active');
    document.body.style.overflow = menu.classList.contains('active') ? 'hidden' : 'auto';
}

document.getElementById('serviceModal').addEventListener('click', function (event) {
    if (event.target === this) closeServiceModal();
});

document.getElementById('modalityModal').addEventListener('click', function (event) {
    if (event.target === this) closeModalityModal();
});

document.getElementById('blogModal').addEventListener('click', function (event) {
    if (event.target === this) closeBlogModal();
});
