// Modales de servicios, modalidades y artículos del blog. El texto completo
// de cada tarjeta ya está en el HTML (bloque .card-full oculto, generado por
// build.py desde content/*.yml), así que buscadores y asistentes de IA lo
// leen sin ejecutar JS. Aquí solo se copia ese contenido al modal.
// El contacto NO se gestiona aquí: build.py lo escribe directamente en
// index.html (huecos .neuro-*) desde content/common.yml.

function fillModal(prefix, card, iconSelector, titleSelector) {
    const icon = card.querySelector(iconSelector);
    document.getElementById(prefix + 'Icon').innerHTML = icon ? icon.innerHTML : '';
    document.getElementById(prefix + 'Title').textContent =
        card.querySelector(titleSelector).textContent;
    document.getElementById(prefix + 'Body').innerHTML =
        card.querySelector('.card-full').innerHTML;
}

function openServiceModal(key) {
    const card = document.querySelector('.service-card[data-service="' + key + '"]');
    if (!card) return;
    fillModal('modal', card, '.service-icon', 'h3');
    const modal = document.getElementById('serviceModal');
    if (!modal.open) modal.showModal();
}

function closeServiceModal() {
    const modal = document.getElementById('serviceModal');
    if (modal.open) modal.close();
}

function openModalityModal(key) {
    const card = document.querySelector('.modality-item[data-modality="' + key + '"]');
    if (!card) return;
    fillModal('modalityModal', card, '.modality-icon', 'h4');
    const modal = document.getElementById('modalityModal');
    if (!modal.open) modal.showModal();
}

function closeModalityModal() {
    const modal = document.getElementById('modalityModal');
    if (modal.open) modal.close();
}

function openBlogModal(key) {
    const card = document.querySelector('.blog-card[data-blog="' + key + '"]');
    if (!card) return;
    const img = card.querySelector('.blog-thumb img');
    const cover = document.getElementById('blogModalCover');
    cover.innerHTML = '';
    if (img) {
        const copy = img.cloneNode();
        copy.removeAttribute('loading');
        cover.appendChild(copy);
    }
    cover.hidden = !img;
    document.getElementById('blogModalTitle').textContent =
        card.querySelector('h4').textContent;
    document.getElementById('blogModalBody').innerHTML =
        card.querySelector('.card-full').innerHTML;
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
