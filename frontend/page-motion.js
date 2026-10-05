import {queueFrame,cancelFrame} from './motion-frame.js';
import {initAmbientMotion} from './ambient-motion.js';
import './page-motion.css';

let currentInstance;

// Everything is visible in the HTML/CSS. Enhancement starts only when an item
// reaches the viewport, so a failed script never leaves content hidden.
export function initPageMotion() {
  if (currentInstance) return currentInstance;
  if (!('IntersectionObserver' in window) || !Element.prototype.animate) return () => {};

  initAmbientMotion();
  const reduced = matchMedia('(prefers-reduced-motion: reduce), (hover: none), (pointer: coarse)');
  const selector = '.car-card, .steps-grid > article, .benefits-grid, .contact-layout > div';
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
    if (entering.size && !revealFrame) revealFrame = queueFrame(reveal);
  }, {threshold: 0.06, rootMargin: '0px 0px -16px 0px'});

  function enhanceAccordion(details) {
    if (accordions.has(details)) return;
    const body=details.querySelector(':scope > .prose');
    let animation;
    const finish=()=>{animation?.cancel();animation=null;};
    const onToggle=()=>{
      finish();if(!body||!details.open||reduced.matches)return;
      animation=body.animate([{opacity:.5,transform:'translateY(-4px)'},{opacity:1,transform:'translateY(0)'}],{duration:180,easing:'ease-out'});
    };
    details.addEventListener('toggle',onToggle);
    accordions.set(details,{finish,dispose:()=>{finish();details.removeEventListener('toggle',onToggle);}});
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
  const scheduleScan = () => {if (!scanFrame) scanFrame = queueFrame(scan);};
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
    cancelFrame(revealFrame); revealFrame = 0; entering.clear();
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
    cancelFrame(scanFrame);
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
