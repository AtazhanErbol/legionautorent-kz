// Native inline playback on compact screens. Loading waits for interaction so
// the poster, navigation and booking controls get the first network/CPU budget.
export function initMobileHero(root,compactQueries){
  const reduced=matchMedia('(prefers-reduced-motion:reduce)'),connection=navigator.connection;
  const picture=root.querySelector('.mercedes-picture');
  const video=document.createElement('video');video.className='mercedes-mobile-film';
  video.muted=true;video.defaultMuted=true;video.loop=true;video.playsInline=true;
  video.setAttribute('playsinline','');video.setAttribute('webkit-playsinline','');
  video.setAttribute('aria-hidden','true');video.tabIndex=-1;video.preload='none';
  video.disablePictureInPicture=true;video.disableRemotePlayback=true;picture.append(video);
  let interacted=false,visible=true,started=false,dead=false;
  const allowed=()=>root.dataset.mobileVideo&&compactQueries.some(q=>q.matches)&&!reduced.matches&&!connection?.saveData&&!['slow-2g','2g','3g'].includes(connection?.effectiveType)&&(!navigator.deviceMemory||navigator.deviceMemory>=4)&&(!navigator.hardwareConcurrency||navigator.hardwareConcurrency>=4);
  const update=()=>{
    if(dead)return;
    if(!allowed()){
      video.pause();root.dataset.ambient='static';
      if(started){video.removeAttribute('src');video.load();started=false;}
      return;
    }
    if(!interacted||!visible||document.hidden){video.pause();return;}
    if(!started){video.src=root.dataset.mobileVideo;video.load();started=true;root.dataset.ambient='loading';}
    video.play().catch(()=>{root.dataset.ambient='static';});
  };
  video.addEventListener('playing',()=>{root.dataset.ambient='ready';});
  video.addEventListener('error',()=>{root.dataset.ambient='fallback';});
  const interact=()=>{interacted=true;update();};
  ['pointerdown','touchstart','keydown'].forEach(event=>window.addEventListener(event,interact,{passive:true}));
  window.addEventListener('scroll',()=>{if(!interacted&&scrollY>0)interact();},{passive:true});
  const observer=new IntersectionObserver(entries=>{visible=entries[0].isIntersecting;update();},{threshold:.05});
  observer.observe(picture);
  [...compactQueries,reduced].forEach(query=>query.addEventListener('change',update));
  connection?.addEventListener?.('change',update);
  document.addEventListener('visibilitychange',update);
  window.addEventListener('pageshow',update);
  window.addEventListener('pagehide',event=>{video.pause();if(!event.persisted){dead=true;observer.disconnect();video.removeAttribute('src');video.load();}});
}
