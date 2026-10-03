import './site.css';
import './hero-story.css';
import './night-garage.css';
import './mercedes-preview.css';
import {initPageMotion} from './page-motion.js';
import {initGarageUI} from './night-garage.js';
initGarageUI();
const $=(selector,root=document)=>root.querySelector(selector);
const reduced=window.matchMedia('(prefers-reduced-motion: reduce)');
const header=$('.site-header');
const updateHeader=()=>header?.classList.toggle('is-scrolled',scrollY>32);
updateHeader();window.addEventListener('scroll',updateHeader,{passive:true});

// Every car remains in SSR HTML. Only the presentation is paged, with no request.
function initFleets(root=document){
  root.querySelectorAll('[data-fleet]').forEach(fleet=>{
    if(fleet.dataset.ready)return;fleet.dataset.ready='true';
    const grid=$('[data-fleet-grid]',fleet),cards=[...grid.querySelectorAll('.car-card')];
    const more=$('[data-show-more]',fleet),status=$('[data-fleet-status]',fleet),empty=$('[data-fleet-empty]',fleet);
    let category='',sort='',expanded=false;
    const render=()=>{
      const matching=cards.filter(card=>!category||card.dataset.category===category);
      const ordered=sort?[...matching].sort((a,b)=>(Number(a.dataset.price)-Number(b.dataset.price))*(sort==='price'?1:-1)):matching;
      cards.forEach(card=>card.hidden=true);
      ordered.forEach((card,index)=>{grid.append(card);card.hidden=!expanded&&index>=12;});
      grid.dataset.ready='true';more.hidden=expanded||matching.length<=12;
      status.textContent=matching.length?`${Math.min(expanded?matching.length:12,matching.length)} / ${matching.length}`:'';
      empty.hidden=!!matching.length||!cards.length;
      fleet.querySelectorAll('[data-category]:not(.car-card)').forEach(button=>{const active=button.dataset.category===category;button.classList.toggle('is-active',active);button.setAttribute('aria-pressed',String(active));});
    };
    fleet.setCategory=value=>{category=value;expanded=false;render();};
    fleet.querySelectorAll('button[data-category]').forEach(button=>button.addEventListener('click',()=>fleet.setCategory(button.dataset.category)));
    $('[data-fleet-sort]',fleet)?.addEventListener('change',event=>{sort=event.target.value;expanded=false;render();});
    more.addEventListener('click',()=>{expanded=true;render();});render();
  });
}
initFleets();
// The optional reveal/accordion enhancement waits for the first layout and
// fonts; native content and details remain usable while the page is loading.
const startPageMotion=()=>{
  if('requestIdleCallback'in window)requestIdleCallback(initPageMotion,{timeout:1800});
  else setTimeout(initPageMotion,300);
};
if(document.readyState==='complete')startPageMotion();else window.addEventListener('load',startPageMotion,{once:true});
const quick=$('[data-quick-search]');
if(quick){
  const start=$('[name=start_date]',quick),end=$('[name=end_date]',quick);
  const validateDates=()=>{end.min=start.value;end.setCustomValidity(start.value&&end.value&&end.value<=start.value?quick.dataset.dateError:'');};
  start.addEventListener('change',validateDates);end.addEventListener('change',validateDates);
  quick.addEventListener('submit',event=>{
    if($('[name=city]',quick).value!==quick.dataset.city)return;
    event.preventDefault();const fleet=$('#fleet [data-fleet]');
    fleet.setCategory($('[name=category]',quick).value);
    // Dates are a request, never a claim of confirmed availability.
    fleet.querySelectorAll('[data-event=click_whatsapp]').forEach(link=>{
      link.dataset.originalHref||=link.href;const url=new URL(link.dataset.originalHref);
      const dates=[start.value,end.value].filter(Boolean).join(' — ');
      if(dates)url.searchParams.set('text',`${url.searchParams.get('text')} ${dates}`);link.href=url;
    });
    $('#fleet').scrollIntoView({behavior:reduced.matches?'auto':'smooth'});
  });
}
window.dataLayer=window.dataLayer||[];
document.addEventListener('click',event=>{
  const link=event.target.closest('[data-event]');
  if(link)window.dataLayer.push({event:link.dataset.event,context:link.dataset.context||'contact',page:location.pathname});
});
const submitted=$('[data-page-event]');
if(submitted)window.dataLayer.push({event:submitted.dataset.pageEvent,page:location.pathname});

// Forms work through normal POST and CSRF even with JavaScript disabled.
document.querySelectorAll('[data-request-form]').forEach(form=>form.addEventListener('submit',()=>{
  if(!form.checkValidity())return;
  const button=$('button[type=submit]',form);button.disabled=true;button.setAttribute('aria-busy','true');
}));
document.querySelectorAll('[data-gallery]').forEach(gallery=>{
  const track=$('.gallery-track',gallery),figures=[...track.querySelectorAll('figure')];
  const move=direction=>track.scrollBy({left:direction*track.clientWidth,behavior:reduced.matches?'auto':'smooth'});
  $('[data-gallery-prev]',gallery)?.addEventListener('click',()=>move(-1));
  $('[data-gallery-next]',gallery)?.addEventListener('click',()=>move(1));
  track.addEventListener('keydown',event=>{if(event.key==='ArrowRight'||event.key==='ArrowLeft'){event.preventDefault();move(event.key==='ArrowRight'?1:-1);}});
  track.addEventListener('scroll',()=>{const count=$('[data-gallery-count]',gallery);if(count)count.textContent=`${Math.round(track.scrollLeft/track.clientWidth)+1} / ${figures.length}`;},{passive:true});
});
const booking=$('[data-car-booking]');
if(booking){
  const update=()=>{
    const start=$('[name=start_date]',booking)?.value,end=$('[name=end_date]',booking)?.value;
    const message=[booking.dataset.message,booking.dataset.city,start&&`${start}${end?' — '+end:''}`].filter(Boolean).join(' ');
    const href=`https://wa.me/${booking.dataset.whatsapp.replace(/\D/g,'')}?text=${encodeURIComponent(message)}`;
    $('[data-car-wa]',booking).href=href;const mobile=$('[data-mobile-wa]');if(mobile)mobile.href=href;
  };booking.addEventListener('change',update);update();
}
document.querySelectorAll('[data-map]').forEach(map=>map.addEventListener('toggle',()=>{const frame=$('iframe',map);if(map.open&&frame&&!frame.src)frame.src=frame.dataset.src;}));
document.addEventListener('click',event=>{document.querySelectorAll('.city-menu[open],.mobile-menu[open]').forEach(menu=>{if(!menu.contains(event.target))menu.open=false;});});

const filters=$('[data-catalog-filter]');
if(filters&&window.fetch){
  let active;
  const load=async(url,push=true)=>{
    active?.abort();active=new AbortController();const result=$('#catalog-results');result.setAttribute('aria-busy','true');
    try{
      const response=await fetch(url,{headers:{'X-Legion-Partial':'catalog'},signal:active.signal});
      if(!response.ok)throw new Error('Catalog response');
      const html=await response.text();result.innerHTML=html;initFleets(result);
      if(push)history.pushState(null,'',url);$('meta[name=robots]').content='noindex,follow';
    }catch(error){if(error.name!=='AbortError')location.href=url;}finally{result.removeAttribute('aria-busy');}
  };
  filters.addEventListener('submit',event=>{event.preventDefault();const url=new URL(filters.action);url.search=new URLSearchParams(new FormData(filters)).toString();load(url);});
  document.addEventListener('click',event=>{const link=event.target.closest('[data-catalog-page]');if(link){event.preventDefault();load(link.href);$('#catalog-results').scrollIntoView({behavior:reduced.matches?'auto':'smooth'});}});
  window.addEventListener('popstate',()=>location.reload());
}

const mercedesPreview=$('[data-mercedes-preview]');
if(mercedesPreview)import('./mercedes-preview.js').then(({initMercedesPreview})=>initMercedesPreview(mercedesPreview)).catch(()=>{mercedesPreview.dataset.state='fallback';});
const hero=$('[data-hero]');
if(hero){
  const minimum=hero.hasAttribute('data-story')?900:768;
  const desktop=matchMedia(`(min-width:${minimum}px)`);let stopHero=()=>{};
  const mountHero=()=>{
  stopHero();
  const connection=navigator.connection,motionAllowed=desktop.matches&&!connection?.saveData&&!reduced.matches;
  const videoMode=Boolean(hero.dataset.video);
  const eligible=motionAllowed&&(videoMode||(hero.dataset.enabled==='true'&&(!navigator.deviceMemory||navigator.deviceMemory>=4)&&(!navigator.hardwareConcurrency||navigator.hardwareConcurrency>=4)));
  if(eligible){
    const restoring=performance.getEntriesByType('navigation')[0]?.type==='back_forward';
    let visible=restoring,idle=false,started=false,alive=true,scene,idleTask,loadTimer;
    const start=async()=>{if(!alive||!visible||!idle||started)return;started=true;try{if(videoMode){const {createVideoHero}=await import('./hero-video.js');if(!alive)return;scene=await createVideoHero(hero);}else{const {createHero}=await import('./hero.js');if(!alive)return;scene=await createHero(hero);}if(!alive)scene?.dispose();}catch(error){if(alive){hero.dataset.state='fallback';console.warn('Legion hero fallback:',error.message);}}};
    const observer=new IntersectionObserver(entries=>{visible=entries[0].isIntersecting||restoring;start();},{rootMargin:'0px'});observer.observe(hero);
    const onIdle=()=>{idle=true;start();};
    const afterLoad=()=>{if('requestIdleCallback'in window)idleTask=requestIdleCallback(onIdle,{timeout:2500});else loadTimer=setTimeout(onIdle,1200);};
    if(document.readyState==='complete')afterLoad();else window.addEventListener('load',afterLoad,{once:true});
    stopHero=()=>{alive=false;observer.disconnect();window.removeEventListener('load',afterLoad);if(idleTask)cancelIdleCallback(idleTask);clearTimeout(loadTimer);scene?.dispose();};
  }else if(hero.dataset.staticPoster){
    const poster=hero.querySelector('.hero-poster');poster.src=hero.dataset.staticPoster;
  }
  };
  mountHero();desktop.addEventListener('change',mountHero);reduced.addEventListener('change',mountHero);
  window.addEventListener('pagehide',event=>{if(!event.persisted)stopHero();});
  window.addEventListener('pageshow',event=>{if(event.persisted&&hero.dataset.state!=='video-ready')mountHero();});
  hero.querySelectorAll('[data-story-skip]').forEach(link=>link.addEventListener('click',event=>{
    event.preventDefault();const fleet=$('#fleet');if(!fleet)return;
    history.pushState(null,'','#fleet');window.scrollTo({top:fleet.getBoundingClientRect().top+scrollY-96,behavior:'instant'});
    const heading=$('h2',fleet);heading.tabIndex=-1;heading.focus({preventScroll:true});
  }));
}

// Defer analytics until LCP has had time to paint; retain all editable legacy IDs.
const analytics=$('[data-analytics]');
if(analytics){
  let loaded=false;
  const script=src=>{const tag=document.createElement('script');tag.async=true;tag.src=src;document.head.append(tag);};
  const start=()=>{
    if(loaded)return;loaded=true;
    if(analytics.dataset.gtm){window.dataLayer.push({'gtm.start':Date.now(),event:'gtm.js'});script(`https://www.googletagmanager.com/gtm.js?id=${encodeURIComponent(analytics.dataset.gtm)}`);}
  };
  window.addEventListener('load',()=>setTimeout(()=>{if('requestIdleCallback'in window)requestIdleCallback(start,{timeout:4000});else start();},2500),{once:true});
}
