import './site.css';
const $=(selector,root=document)=>root.querySelector(selector);
const reduced=window.matchMedia('(prefers-reduced-motion: reduce)');
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
      const html=await response.text();result.innerHTML=html;
      if(push)history.pushState(null,'',url);$('meta[name=robots]').content='noindex,follow';
    }catch(error){if(error.name!=='AbortError')location.href=url;}finally{result.removeAttribute('aria-busy');}
  };
  filters.addEventListener('submit',event=>{event.preventDefault();const url=new URL(filters.action);url.search=new URLSearchParams(new FormData(filters)).toString();load(url);});
  document.addEventListener('click',event=>{const link=event.target.closest('[data-catalog-page]');if(link){event.preventDefault();load(link.href);$('#catalog-results').scrollIntoView({behavior:reduced.matches?'auto':'smooth'});}});
  window.addEventListener('popstate',()=>location.reload());
}

const hero=$('[data-hero]');
if(hero){
  const connection=navigator.connection,eligible=hero.dataset.enabled==='true'&&innerWidth>=768&&!connection?.saveData&&!reduced.matches&&(!navigator.deviceMemory||navigator.deviceMemory>=4)&&(!navigator.hardwareConcurrency||navigator.hardwareConcurrency>=4);
  if(eligible){
    let visible=false,idle=false,started=false;
    const start=async()=>{if(!visible||!idle||started)return;started=true;try{const {createHero}=await import('./hero.js');await createHero(hero);}catch(error){hero.dataset.state='fallback';console.warn('Legion 3D fallback:',error.message);}};
    const observer=new IntersectionObserver(entries=>{visible=entries[0].isIntersecting;start();},{rootMargin:'0px'});observer.observe(hero);
    const onIdle=()=>{idle=true;start();};
    window.addEventListener('load',()=>{if('requestIdleCallback'in window)requestIdleCallback(onIdle,{timeout:2500});else setTimeout(onIdle,1200);},{once:true});
    window.addEventListener('pagehide',()=>observer.disconnect(),{once:true});
  }else if(hero.dataset.video&&!connection?.saveData&&!reduced.matches){
    const video=document.createElement('video');video.src=hero.dataset.video;video.muted=true;video.loop=true;video.playsInline=true;video.preload='none';video.className='hero-poster';video.setAttribute('aria-hidden','true');hero.prepend(video);video.play().catch(()=>video.remove());
  }
}

// Defer analytics until LCP has had time to paint; retain all editable legacy IDs.
const analytics=$('[data-analytics]');
if(analytics){
  let loaded=false;
  const script=src=>{const tag=document.createElement('script');tag.async=true;tag.src=src;document.head.append(tag);};
  const start=()=>{
    if(loaded)return;loaded=true;
    if(analytics.dataset.gtm){window.dataLayer.push({'gtm.start':Date.now(),event:'gtm.js'});script(`https://www.googletagmanager.com/gtm.js?id=${encodeURIComponent(analytics.dataset.gtm)}`);}
    else{
      if(analytics.dataset.ga){script(`https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(analytics.dataset.ga)}`);const gtag=(...args)=>window.dataLayer.push(args);gtag('js',new Date());gtag('config',analytics.dataset.ga);}
      if(analytics.dataset.metrika){window.ym=function(){(window.ym.a=window.ym.a||[]).push(arguments);};window.ym.l=Date.now();script('https://mc.yandex.ru/metrika/tag.js');window.ym(Number(analytics.dataset.metrika),'init',{clickmap:true,trackLinks:true,accurateTrackBounce:true});}
    }
  };
  window.addEventListener('load',()=>setTimeout(()=>{if('requestIdleCallback'in window)requestIdleCallback(start,{timeout:4000});else start();},2500),{once:true});
}
