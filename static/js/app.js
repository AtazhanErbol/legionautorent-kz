(() => {
  'use strict';
  const event = (name, context = '') => {
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({event: name, context, language: document.documentElement.lang});
    if (window.ym && window.legionMetrikaId) window.ym(window.legionMetrikaId, 'reachGoal', name);
  };
  document.querySelectorAll('[data-event]').forEach(element => {
    element.addEventListener(element.tagName === 'FORM' ? 'submit' : 'click', () => event(element.dataset.event, element.dataset.context || ''));
  });
  if (document.body.dataset.pageEvent) event(document.body.dataset.pageEvent, document.body.dataset.object || '');
  document.querySelectorAll('select[name="city"]').forEach(select => select.addEventListener('change', () => event('select_city', select.value)));
  const toggle = document.querySelector('.menu-toggle');
  const menu = document.getElementById('mobile-menu');
  const closeMenu = () => { if (menu) menu.hidden = true; if (toggle) toggle.setAttribute('aria-expanded', 'false'); };
  toggle?.addEventListener('click', () => { menu.hidden = !menu.hidden; toggle.setAttribute('aria-expanded', String(!menu.hidden)); });
  menu?.querySelectorAll('a').forEach(link => link.addEventListener('click', closeMenu));
  document.addEventListener('keydown', e => { if (e.key === 'Escape') {closeMenu(); toggle?.focus();} });
  const header = document.getElementById('header');
  let ticking = false;
  window.addEventListener('scroll', () => { if (!ticking) {requestAnimationFrame(() => {header?.classList.toggle('compact', scrollY > 40); ticking = false;}); ticking = true;} }, {passive: true});
  const gallery = document.getElementById('gallery-main');
  document.querySelectorAll('.gallery-thumb').forEach(link => link.addEventListener('click', e => {
    if (!gallery) return;
    e.preventDefault(); gallery.src = link.dataset.image; gallery.alt = link.dataset.alt;
    document.querySelectorAll('.gallery-thumb').forEach(item => item.classList.toggle('selected', item === link));
  }));
  const start = document.getElementById('quick-start');
  const end = document.getElementById('quick-end');
  if (start && end) {
    const now = new Date(); now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
    start.min = now.toISOString().slice(0, 10); end.min = start.min;
    start.addEventListener('change', () => {end.min = start.value || start.min;});
  }
  const scene = document.getElementById('hero-scene');
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const lowPower = reduced || innerWidth < 900 || navigator.connection?.saveData || (navigator.deviceMemory && navigator.deviceMemory < 4);
  if (scene && !lowPower) {
    const image = document.getElementById('hero-car');
    const idle = window.requestIdleCallback || (cb => setTimeout(cb, 1200));
    idle(() => {
      const script = document.createElement('script'); script.src = '/static/vendor/gsap/gsap.min.js';
      script.onload = () => window.gsap?.fromTo(image, {y: 8, opacity: .8}, {y: 0, opacity: 1, duration: .8, ease: 'power2.out'});
      document.head.appendChild(script);
    });
    scene.addEventListener('pointermove', e => {
      if (!image || scene.querySelector('canvas')) return;
      const rect = scene.getBoundingClientRect();
      image.style.transform = `translate(${((e.clientX - rect.left) / rect.width - .5) * 8}px,${((e.clientY - rect.top) / rect.height - .5) * 4}px)`;
    }, {passive: true});
    scene.addEventListener('pointerleave', () => {if (image) image.style.transform = '';});
    scene.querySelector('.scene-toggle')?.addEventListener('click', async e => {
      const button = e.currentTarget;
      if (!scene.dataset.model || button.dataset.initialized) return;
      button.dataset.initialized = 'true';
      try {const module = await import('/static/js/hero3d.js'); await module.mount(scene); button.setAttribute('aria-pressed', 'true'); button.hidden = true;}
      catch (error) {button.dataset.initialized = ''; button.hidden = true; console.info('3D unavailable; image retained.');}
    });
  } else scene?.querySelector('.scene-toggle')?.setAttribute('hidden', '');
})();
