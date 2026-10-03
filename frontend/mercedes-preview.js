// Approved film, native scroll and complete static fallback.
export function initMercedesPreview(root){
  const video=root.querySelector('video'),ring=root.querySelector('.mercedes-load');
  const intro=root.querySelector('.mercedes-caption--intro'),ending=root.querySelector('.mercedes-caption--end');
  const progressBar=root.querySelector('.mercedes-progress span');
  const queries=['(max-height:699px)','(max-width:899px)','(orientation:portrait) and (max-width:1024px)','(orientation:portrait) and (pointer:coarse)','(orientation:landscape) and (pointer:coarse) and (max-height:560px)','(prefers-reduced-motion:reduce)'].map(q=>matchMedia(q));
  const connection=navigator.connection;
  const watch=root.querySelector('.mercedes-watch'),picture=root.querySelector('.mercedes-picture');
  let manualPlayer;
  const watchLabel=()=>{
    const playing=manualPlayer&&!manualPlayer.paused&&!manualPlayer.ended;
    watch.querySelector('[data-watch-label]').textContent=playing?watch.dataset.pauseLabel:watch.dataset.playLabel;
    watch.querySelector('[aria-hidden]').textContent=playing?'Ⅱ':'▶';
  };
  const stopManual=()=>{
    if(!manualPlayer)return;
    manualPlayer.pause();manualPlayer.removeAttribute('src');manualPlayer.load();manualPlayer.remove();manualPlayer=null;
    picture.setAttribute('aria-hidden','true');watchLabel();
  };
  // The narrow owner-review panel stays static until an explicit play click.
  // This separate native player never alters scroll gates or starts by itself.
  watch.addEventListener('click',event=>{
    event.preventDefault();
    if(!manualPlayer){
      manualPlayer=document.createElement('video');manualPlayer.className='mercedes-manual';
      manualPlayer.controls=true;manualPlayer.muted=true;manualPlayer.playsInline=true;manualPlayer.preload='none';
      manualPlayer.poster=picture.querySelector('img').currentSrc;manualPlayer.src=root.dataset.video;
      picture.removeAttribute('aria-hidden');picture.append(manualPlayer);
      ['play','pause','ended'].forEach(name=>manualPlayer.addEventListener(name,watchLabel));
    }
    if(manualPlayer.paused||manualPlayer.ended){if(manualPlayer.ended)manualPlayer.currentTime=0;manualPlayer.play().catch(watchLabel);}
    else manualPlayer.pause();
  });
  let enabled=false,loading=false,dead=false,controller,objectURL,watchdog,loadTimer,seekTimer;
  let frame=0,lastTick=0,target=0,shown=0,lastPaint=-1,start=0,distance=1,inView=true,desired=0;
  const clamp=(n)=>Math.max(0,Math.min(1,n));
  const allowed=()=>Boolean(root.dataset.video)&&!queries.some(q=>q.matches)&&!connection?.saveData&&!['slow-2g','2g','3g'].includes(connection?.effectiveType)&&(!navigator.deviceMemory||navigator.deviceMemory>=4)&&(!navigator.hardwareConcurrency||navigator.hardwareConcurrency>=4);
  const paint=(p)=>{
    if(Math.abs(p-lastPaint)<.0002)return;lastPaint=p;
    const out=clamp((p-.30)/.13),incoming=clamp((p-.53)/.13);
    intro.style.opacity=String(1-out);intro.style.transform=`translateY(${-out*16}px)`;
    ending.style.opacity=String(incoming);ending.style.transform=`translateY(${(1-incoming)*16}px)`;
    ending.style.visibility=incoming?'visible':'hidden';
    const hidden=String(incoming===0);if(ending.getAttribute('aria-hidden')!==hidden)ending.setAttribute('aria-hidden',hidden);
    progressBar.style.transform=`scaleX(${p})`;root.dataset.progress=p.toFixed(4);
  };
  const requestSeek=()=>{
    if(!enabled||video.seeking||video.readyState<2||!Number.isFinite(video.duration))return;
    if(Math.abs(video.currentTime-desired)<1/120)return;
    video.currentTime=desired;
    clearTimeout(seekTimer);seekTimer=setTimeout(()=>{if(video.seeking)fallback();},12000);
  };
  const tick=(now)=>{
    frame=0;if(!enabled||!inView||document.hidden){lastTick=0;return;}
    const dt=lastTick?Math.min(100,now-lastTick):16.667;lastTick=now;
    shown+=(target-shown)*(1-Math.pow(.84,dt/16.667));
    if(Math.abs(target-shown)<.0001)shown=target;
    paint(shown);desired=shown*Math.max(0,video.duration-1/24);requestSeek();
    if(shown!==target)schedule();else lastTick=0;
  };
  const schedule=()=>{if(!frame&&enabled&&inView&&!document.hidden)frame=requestAnimationFrame(tick);};
  const onScroll=()=>{if(!enabled&&objectURL&&!loading&&allowed()&&root.getBoundingClientRect().top>=-64)activate();target=clamp((scrollY-start)/distance);schedule();};
  const measure=()=>{start=root.getBoundingClientRect().top+scrollY;distance=Math.max(1,root.offsetHeight-root.querySelector('.mercedes-stage').offsetHeight);onScroll();};
  const reset=()=>{
    enabled=false;cancelAnimationFrame(frame);frame=0;lastTick=0;clearTimeout(seekTimer);
    video.pause();root.dataset.state='static';lastPaint=-1;paint(0);ring.hidden=true;
  };
  const fallback=()=>{reset();root.dataset.state='fallback';};
  const activate=()=>{
    if(dead||!allowed()||!Number.isFinite(video.duration))return;
    // Do not expand a late-loading pin underneath a visitor already in the catalogue.
    if(scrollY>root.getBoundingClientRect().top+scrollY+root.offsetHeight-96)return;
    enabled=true;root.dataset.state='ready';ring.hidden=true;lastPaint=-1;
    measure();shown=target;paint(shown);schedule();
  };
  async function load(){
    if(loading||dead||!allowed())return;
    if(objectURL){activate();return;}
    loading=true;controller=new AbortController();const active=controller;ring.hidden=false;
    const rearm=()=>{clearTimeout(watchdog);watchdog=setTimeout(()=>active.abort(),20000);};
    try{
      rearm();const response=await fetch(root.dataset.video,{signal:active.signal,priority:'low'});
      if(!response.ok)throw new Error('Video response');
      const total=Number(response.headers.get('Content-Length'))||Number(root.dataset.bytes);
      const reader=response.body.getReader(),chunks=[];let got=0,lastRing=0;
      for(;;){
        const {done,value}=await reader.read();if(done)break;rearm();chunks.push(value);got+=value.length;
        const now=performance.now();if(now-lastRing>100||got>=total){ring.style.setProperty('--loaded',String(Math.round(126*(1-(total?Math.min(1,got/total):0)))));lastRing=now;}
      }
      clearTimeout(watchdog);
      if(dead||!allowed())return;
      objectURL=URL.createObjectURL(new Blob(chunks,{type:'video/mp4'}));
      await new Promise((resolve,reject)=>{
        const cleanup=()=>{clearTimeout(loadTimer);video.removeEventListener('loadeddata',ready);video.removeEventListener('error',fail);};
        const ready=()=>{cleanup();resolve();},fail=()=>{cleanup();reject(new Error('Video decode'));};
        video.addEventListener('loadeddata',ready,{once:true});video.addEventListener('error',fail,{once:true});
        loadTimer=setTimeout(fail,12000);video.src=objectURL;video.load();
      });
      activate();
    }catch{
      if(objectURL){URL.revokeObjectURL(objectURL);objectURL=null;video.removeAttribute('src');video.load();}
      if(!dead)fallback();
    }finally{clearTimeout(watchdog);loading=false;ring.hidden=true;}
  }
  const apply=()=>{
    // Connection estimates change during a download; do not interrupt a
    // viewer who explicitly started playback in the static layout.
    if(manualPlayer&&!allowed())return;
    stopManual();
    if(!allowed()){controller?.abort();reset();return;}
    if(document.readyState==='complete')load();
  };
  video.addEventListener('seeked',()=>{clearTimeout(seekTimer);requestSeek();});
  video.addEventListener('error',()=>{if(enabled)fallback();});
  const observer=new IntersectionObserver(entries=>{inView=entries[0].isIntersecting;if(inView){onScroll();}else{cancelAnimationFrame(frame);frame=0;lastTick=0;manualPlayer?.pause();}},{threshold:0});
  observer.observe(root);
  window.addEventListener('scroll',onScroll,{passive:true});window.addEventListener('resize',measure,{passive:true});
  window.addEventListener('load',apply,{once:true});queries.forEach(q=>q.addEventListener('change',()=>{stopManual();apply();}));connection?.addEventListener?.('change',apply);
  document.addEventListener('visibilitychange',()=>{if(document.hidden){cancelAnimationFrame(frame);frame=0;lastTick=0;manualPlayer?.pause();}else onScroll();});
  window.addEventListener('pageshow',event=>{if(event.persisted){measure();apply();}});
  window.addEventListener('pagehide',event=>{manualPlayer?.pause();if(event.persisted)return;dead=true;controller?.abort();stopManual();reset();observer.disconnect();if(objectURL)URL.revokeObjectURL(objectURL);});
  root.querySelector('a[href="#fleet"]').addEventListener('click',event=>{
    const fleet=document.querySelector('#fleet');if(!fleet)return;
    event.preventDefault();history.pushState(null,'','#fleet');window.scrollTo({top:fleet.getBoundingClientRect().top+scrollY-96,behavior:'instant'});
    const heading=fleet.querySelector('h2');if(heading){heading.tabIndex=-1;heading.focus({preventScroll:true});}
  });
  measure();apply();
}
