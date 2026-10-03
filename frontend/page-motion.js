import './page-motion.css';

let currentInstance;

// Everything is visible in the HTML/CSS. Enhancement starts only when an item
// reaches the viewport, so a failed script never leaves content hidden.
export function initPageMotion() {
  if (currentInstance) return currentInstance;
  if (!('IntersectionObserver' in window) || !Element.prototype.animate) return () => {};

  const reduced = matchMedia('(prefers-reduced-motion: reduce), (hover: none), (pointer: coarse)');
  const selector = '.car-card, .steps-grid > article, .benefits-grid > article, .contact-layout > div';
  const observed = new Set();
  const seen = new WeakSet();
  const reveals = new Map();
  const accordions = new Map();
  const entering = new Set();
  const dirtyGrids = new Set();
  let revealFrame = 0;
  let scanFrame = 0;
  let disposed = false;

  const stopReveal = element => {
    reveals.get(element)?.cancel();
    reveals.delete(element);
  };
  const visible = element => !element.hidden && !element.closest('[hidden]');

  const reveal = () => {
    revealFrame = 0;
    const entries = [...entering].filter(element => element.isConnected && visible(element));
    entering.clear();
    if (reduced.matches) return;
    const positions = entries.map(element => ({element, rect: element.getBoundingClientRect()}))
      .filter(({rect}) => rect.bottom > 0 && rect.top < innerHeight)
      .sort((a, b) => Math.abs(a.rect.top - b.rect.top) < 12 ? a.rect.left - b.rect.left : a.rect.top - b.rect.top);
    let row = -1;
    let rowTop = -Infinity;
    let column = 0;
    for (const {element, rect} of positions) {
      if (Math.abs(rect.top - rowTop) > 12) {row++; rowTop = rect.top; column = 0;}
      const isCard = element.matches('.car-card');
      const isStep = element.matches('.steps-grid > article');
      const delay = Math.min(140, row * 55 + column++ * (isStep ? 65 : 30));
      // Individual translate composes with the card's existing hover transform.
      const animation = element.animate([
        {opacity: isCard || isStep ? 0.65 : 0.82, translate: `0 ${isCard ? 12 : 8}px`},
        {opacity: 1, translate: '0 0'},
      ], {duration: isCard ? 320 : 360, delay, easing: 'cubic-bezier(.2,.65,.3,1)', fill: 'backwards'});
      reveals.set(element, animation);
      animation.finished.then(() => {
        if (reveals.get(element) === animation) reveals.delete(element);
      }).catch(() => {});
    }
  };

  const observer = new IntersectionObserver(entries => {
    for (const entry of entries) {
      const element = entry.target;
      if (!entry.isIntersecting || !visible(element)) continue;
      observer.unobserve(element);
      seen.add(element);
      if (!reduced.matches) entering.add(element);
    }
    if (entering.size && !revealFrame) revealFrame = requestAnimationFrame(reveal);
  }, {threshold: 0.06, rootMargin: '0px 0px -16px 0px'});

  function enhanceAccordion(details) {
    if (accordions.has(details)) return;
    const summary = details.querySelector(':scope > summary');
    const body = details.querySelector(':scope > .prose');
    if (!summary || !body) return;
    const originalInert = body.inert;
    let animation;
    let targetOpen = details.open;

    const finish = () => {
      if (!animation) {targetOpen = details.open; body.inert = originalInert; return;}
      const running = animation;
      animation = null;
      if (running) {running.onfinish = null; running.cancel();}
      details.open = targetOpen;
      details.style.removeProperty('height');
      details.classList.remove('faq-is-moving', 'faq-is-closing');
      body.inert = originalInert;
    };

    const onClick = event => {
      if (event.defaultPrevented || event.button !== 0 || reduced.matches) return;
      if (event.target.closest('a, button, input, select, textarea')) return;
      event.preventDefault();
      const startHeight = details.getBoundingClientRect().height;
      targetOpen = animation ? !targetOpen : !details.open;
      if (animation) {animation.onfinish = null; animation.cancel(); animation = null;}
      details.style.removeProperty('height');
      details.classList.remove('faq-is-moving', 'faq-is-closing');
      if (targetOpen) details.open = true;
      // Content being closed must not keep a keyboard focus target while its
      // visual height shrinks. Native details takes over again on completion.
      if (!targetOpen && body.contains(document.activeElement)) summary.focus({preventScroll: true});
      body.inert = originalInert || !targetOpen;
      const style = getComputedStyle(details);
      const edges = ['borderTopWidth', 'borderBottomWidth', 'paddingTop', 'paddingBottom']
        .reduce((sum, key) => sum + (parseFloat(style[key]) || 0), 0);
      const endHeight = targetOpen ? details.getBoundingClientRect().height : summary.getBoundingClientRect().height + edges;
      details.classList.add('faq-is-moving');
      details.classList.toggle('faq-is-closing', !targetOpen);
      details.style.height = `${startHeight}px`;
      animation = details.animate([{height: `${startHeight}px`}, {height: `${endHeight}px`}], {
        duration: 240, easing: 'cubic-bezier(.2,.65,.3,1)', fill: 'forwards',
      });
      animation.onfinish = finish;
    };
    const onFocus = event => {if (animation && targetOpen && body.contains(event.target)) finish();};
    // External/native changes (including browser find-in-page) remain valid.
    const onToggle = () => {
      if (!animation) targetOpen = details.open;
      else if (!details.open) {targetOpen = false; finish();}
    };
    summary.addEventListener('click', onClick);
    details.addEventListener('focusin', onFocus);
    details.addEventListener('toggle', onToggle);
    accordions.set(details, {
      finish,
      dispose: () => {
        finish();
        summary.removeEventListener('click', onClick);
        details.removeEventListener('focusin', onFocus);
        details.removeEventListener('toggle', onToggle);
      },
    });
  }

  const scan = () => {
    scanFrame = 0;
    if (disposed) return;
    for (const element of observed) {
      if (!element.isConnected) {
        observer.unobserve(element); stopReveal(element); entering.delete(element); observed.delete(element);
      }
    }
    for (const [details, state] of accordions) {
      if (!details.isConnected) {state.dispose(); accordions.delete(details);}
    }
    // Existing fleet code reorders DOM nodes and toggles hidden in one task.
    // Reconcile the final state once, after filtering/sorting/show-more finishes.
    for (const grid of dirtyGrids) {
      grid.querySelectorAll('.car-card').forEach(card => {
        observer.unobserve(card); stopReveal(card); entering.delete(card); seen.delete(card);
      });
    }
    dirtyGrids.clear();
    document.querySelectorAll(selector).forEach(element => {
      observed.add(element);
      if (!seen.has(element) && visible(element)) observer.observe(element);
    });
    document.querySelectorAll('.faq-list > details').forEach(enhanceAccordion);
  };
  const scheduleScan = () => {if (!scanFrame) scanFrame = requestAnimationFrame(scan);};
  const mutations = new MutationObserver(records => {
    let relevant = false;
    for (const record of records) {
      const target = record.target;
      if (!(target instanceof Element)) continue;
      const grid = target.closest('.car-grid');
      if (grid) {dirtyGrids.add(grid); relevant = true;}
      if (target.matches('.faq-list')) relevant = true;
      if (record.type === 'childList') {
        const changed = [...record.addedNodes, ...record.removedNodes];
        relevant ||= changed.some(node => node instanceof Element &&
          (node.matches(`${selector}, .car-grid, .faq-list, .faq-list > details`) ||
            node.querySelector(`${selector}, .faq-list`)));
      }
    }
    if (relevant) scheduleScan();
  });
  const settle = () => {
    cancelAnimationFrame(revealFrame); revealFrame = 0; entering.clear();
    for (const element of reveals.keys()) stopReveal(element);
    for (const state of accordions.values()) state.finish();
  };
  const onPreference = () => {if (reduced.matches) settle(); else scheduleScan();};
  const onFocus = event => {
    const element = event.target.closest(selector);
    if (element) {
      seen.add(element); observer.unobserve(element); entering.delete(element); stopReveal(element);
    }
  };
  const onPageShow = event => {if (event.persisted) scheduleScan();};
  document.addEventListener('focusin', onFocus);
  reduced.addEventListener('change', onPreference);
  window.addEventListener('pagehide', settle);
  window.addEventListener('pageshow', onPageShow);
  mutations.observe(document.body, {subtree: true, childList: true, attributes: true, attributeFilter: ['hidden']});
  scan();

  currentInstance = () => {
    disposed = true;
    cancelAnimationFrame(scanFrame);
    mutations.disconnect(); observer.disconnect(); settle();
    for (const state of accordions.values()) state.dispose();
    accordions.clear(); observed.clear(); dirtyGrids.clear();
    document.removeEventListener('focusin', onFocus);
    reduced.removeEventListener('change', onPreference);
    window.removeEventListener('pagehide', settle);
    window.removeEventListener('pageshow', onPageShow);
    currentInstance = null;
  };
  return currentInstance;
}
