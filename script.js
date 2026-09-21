const config = {
    phone: "+34 711 233 888",
    mail: "teresa@neurogarval.es",
    address: "C/ Diego de Almagro, 32,<br>28342, Valdemoro, Madrid",
    mapsUrl: "https://maps.app.goo.gl/pwGjVP2YtA6mQypG9",
    logo: "logo.svg"
};

// Iconos en SVG (Bootstrap Icons no incluye cerebro/rayo de este estilo), trazo y color como los bi-*
const brainIcon = `<svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 18V5"/><path d="M15 13a4.17 4.17 0 0 1-3-4 4.17 4.17 0 0 1-3 4"/><path d="M17.598 6.5A3 3 0 1 0 12 5a3 3 0 1 0-5.598 1.5"/><path d="M17.997 5.125a4 4 0 0 1 2.526 5.77"/><path d="M18 18a4 4 0 0 0 2-7.464"/><path d="M19.967 17.483A4 4 0 1 1 12 18a4 4 0 1 1-7.967-.517"/><path d="M6 18a4 4 0 0 1-2-7.464"/><path d="M6.003 5.125a4 4 0 0 0-2.526 5.77"/></svg>`;
const heartIcon = `<svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2 9.5a5.5 5.5 0 0 1 9.591-3.676.56.56 0 0 0 .818 0A5.49 5.49 0 0 1 22 9.5c0 2.29-1.5 4-3 5.5l-5.492 5.313a2 2 0 0 1-3 .019L5 15c-1.5-1.5-3-3.2-3-5.5"/><path d="M3.22 13H9.5l.5-1 2 4.5 2-7 1.5 3.5h5.27"/></svg>`;
const zapIcon = `<svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15.914 4a1.5 1.5 0 0 0-2.474-1.561l-9 9A1.5 1.5 0 0 0 5.5 14h4.002a.5.5 0 0 1 .471.666L8.086 20a1.5 1.5 0 0 0 2.475 1.56l9-9A1.5 1.5 0 0 0 18.5 10h-3.997a.5.5 0 0 1-.472-.667z"/></svg>`;

const serviceInfo = {
    neuro: {
        icon: brainIcon,
        title: "Neuropsicología",
        html: `<p>La neuropsicología estudia la relación entre el funcionamiento del cerebro y la conducta: atención, memoria, lenguaje, funciones ejecutivas, visopercepción y velocidad de procesamiento, entre otras.</p>
            <p>El objetivo es comprender cómo estas funciones influyen en el día a día y diseñar una intervención ajustada a cada persona.</p>
            <ul>
                <li>Entrevista inicial con la persona y/o la familia.</li>
                <li>Evaluación con pruebas estandarizadas.</li>
                <li>Devolución de resultados y orientaciones.</li>
                <li>Plan de intervención personalizado.</li>
            </ul>
            <p>Dirigido a niños, adolescentes y adultos con TDAH, TEA, dificultades de aprendizaje, daño cerebral adquirido o deterioro cognitivo, entre otros.</p>`
    },
    psico: {
        icon: heartIcon,
        title: "Psicología Sanitaria",
        html: `<p>Un espacio profesional y seguro para atender dificultades emocionales y conductuales, entendiendo el momento vital de cada persona.</p>
            <p>Se trabaja desde un enfoque cercano y basado en la evidencia, con objetivos claros y revisables.</p>
            <ul>
                <li>Ansiedad, estrés y estado de ánimo.</li>
                <li>Autoestima y gestión emocional.</li>
                <li>Habilidades sociales y pautas para la familia.</li>
                <li>Duelo y procesos de adaptación.</li>
            </ul>
            <p>Atención a niños, adolescentes y adultos, de forma individual o con la familia cuando es necesario.</p>`
    },
    rehab: {
        icon: zapIcon,
        title: "Rehabilitación",
        html: `<p>Programas personalizados orientados a rehabilitar, estimular y mantener las funciones cognitivas, partiendo de los objetivos y la rutina de cada persona.</p>
            <ul>
                <li>Estimulación cognitiva individual.</li>
                <li>Entrenamiento en estrategias y compensación.</li>
                <li>Asesoramiento a familiares y cuidadores.</li>
                <li>Seguimiento periódico de avances.</li>
            </ul>
            <p>Disponible en clínica, online o a domicilio, según las necesidades.</p>`
    }
};

function openServiceModal(key) {
    const info = serviceInfo[key];
    if (!info) return;
    document.getElementById('modalIcon').innerHTML = info.icon;
    document.getElementById('modalTitle').textContent = info.title;
    document.getElementById('modalBody').innerHTML = info.html;
    document.getElementById('serviceModal').showModal();
}

function closeServiceModal() {
    document.getElementById('serviceModal').close();
}

function initData() {
    const rawPhone = config.phone.replace(/\s/g, '');
    document.querySelectorAll('.neuro-phone').forEach(el => el.innerText = config.phone);
    document.querySelectorAll('.neuro-phone-link').forEach(el => el.href = `tel:${rawPhone}`);
    document.querySelectorAll('.neuro-whatsapp-link').forEach(el => el.href = `https://wa.me/${rawPhone.replace('+', '')}`);
    document.querySelectorAll('.neuro-mail').forEach(el => el.innerText = config.mail);
    document.querySelectorAll('.neuro-mail-link').forEach(el => el.href = `mailto:${config.mail}`);
    document.querySelectorAll('.neuro-address').forEach(el => el.innerHTML = config.address);
    document.querySelectorAll('.neuro-address-link').forEach(el => el.href = config.mapsUrl);
    document.querySelectorAll('.neuro-logo').forEach(el => el.src = config.logo);
}

function toggleMenu() {
    const menu = document.getElementById('mobileMenu');
    menu.classList.toggle('active');
    document.body.style.overflow = menu.classList.contains('active') ? 'hidden' : 'auto';
}

document.getElementById('serviceModal').addEventListener('click', function (event) {
    if (event.target === this) closeServiceModal();
});

window.addEventListener('DOMContentLoaded', initData);
