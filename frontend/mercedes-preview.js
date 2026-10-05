// Native scroll with frame-quantized seeks and a complete static fallback.
import {queueFrame,cancelFrame} from './motion-frame.js';
import {initMobileHero} from './mobile-hero.js';
export function initMercedesPreview(root){
  const video=root.querySelector('video'),ring=root.querySelector('.mercedes-load');
  const bands=[...root.querySelectorAll('[data-band]')].map(el=>({el,start:Number(el.dataset.start),end:Number(el.dataset.end),opacity:-1}));
  const booking=root.querySelector('.search-wrap'),still=()=>root.dataset.mode!=='cinematic';
  const progressBar=root.querySelector('.mercedes-progress span');
  const queries=['(max-height:699px)','(max-width:899px)','(orientation:portrait) and (max-width:1024px)','(orientation:portrait) and (pointer:coarse)','(orientation:landscape) and (pointer:coarse) and (max-height:560px)','(prefers-reduced-motion:reduce)'].map(q=>matchMedia(q));
  const connection=navigator.connection;
  const picture=root.querySelector('.mercedes-picture');
  const chapter=root.querySelector('[data-chapter]');
  const sourceFPS=Number(root.dataset.fps)||24;
  initMobileHero(root,queries.slice(0,-1));
  let enabled=false,loading=false,dead=false,controller,objectURL,watchdog,loadTimer,seekTimer,seekBusy=false,presentCallback=0,releaseTimer;
  let lastSeekFrame=-1,lastChapter='01';
  let frame=0,lastTick=0,target=0,shown=0,lastPaint=-1,start=0,distance=1,inView=true,desired=0;
  const clamp=(n)=>Math.max(0,Math.min(1,n));
  const allowed=()=>Boolean(root.dataset.video)&&!queries.some(q=>q.matches)&&!connection?.saveData&&!['slow-2g','2g','3g'].includes(connection?.effectiveType)&&(!navigator.deviceMemory||navigator.deviceMemory>=4)&&(!navigator.hardwareConcurrency||navigator.hardwareConcurrency>=4);
  const paint=(p)=>{
    if(Math.abs(p-lastPaint)<.0002)return;lastPaint=p;
    const smooth=n=>n*n*(3-2*n);
    let active=0;
    bands.forEach((band,index)=>{
      const enter=index?smooth(clamp((p-band.start)/.01)):1;
      const leave=index===bands.length-1?1:1-smooth(clamp((p-band.end+.01)/.01));
      const opacity=still()?1:enter*leave;
      if(p>=band.start)active=index;
      if(Math.abs(opacity-band.opacity)<.002)return;
      band.opacity=opacity;band.el.style.opacity=String(opacity);
      band.el.style.transform=`translateY(${(1-enter)*12}px)`;
      band.el.style.visibility=opacity>.001?'visible':'hidden';
      band.el.inert=opacity<=.001;
      band.el.setAttribute('aria-hidden',String(opacity<=.001));
    });
    const bookingOpacity=still()||booking.contains(document.activeElement)?1:bands[0].opacity;
    if(booking.style.opacity!==String(bookingOpacity)){
      booking.style.opacity=String(bookingOpacity);booking.style.visibility=bookingOpacity>.001?'visible':'hidden';booking.inert=bookingOpacity<=.001;
    }
    progressBar.style.transform=`scaleX(${p})`;root.dataset.progress=p.toFixed(4);
    const label=String(active+1).padStart(2,'0');if(chapter&&label!==lastChapter){chapter.textContent=label;lastChapter=label;}
  };
  const requestSeek=()=>{
    if(!enabled||seekBusy||video.seeking||video.readyState<2||!Number.isFinite(video.duration))return;
    const wanted=Math.round(desired*sourceFPS);
    if(wanted===lastSeekFrame)return;
    lastSeekFrame=wanted;seekBusy=true;
    if(video.requestVideoFrameCallback){
      const presented=(now,metadata)=>{
        presentCallback=0;
        if(!video.seeking&&Math.abs(metadata.mediaTime-wanted/sourceFPS)<1/sourceFPS)releaseSeek();
        else if(enabled)presentCallback=video.requestVideoFrameCallback(presented);
      };
      presentCallback=video.requestVideoFrameCallback(presented);
    }
    video.currentTime=Math.min(video.duration-.002,(wanted+.01)/sourceFPS);
    clearTimeout(seekTimer);seekTimer=setTimeout(()=>{if(video.seeking)fallback();},12000);
  };
  const releaseSeek=()=>{
    clearTimeout(releaseTimer);clearTimeout(seekTimer);
    if(presentCallback)video.cancelVideoFrameCallback?.(presentCallback);presentCallback=0;
    seekBusy=false;requestSeek();
  };
  const tick=(now)=>{
    frame=0;if(!enabled||!inView||document.hidden){lastTick=0;return;}
    const dt=lastTick?Math.min(100,now-lastTick):16.667;lastTick=now;
    shown+=(target-shown)*(1-Math.exp(-dt/115));
    if(Math.abs(target-shown)<.0001)shown=target;
    paint(shown);desired=shown*Math.max(0,video.duration-1/sourceFPS);requestSeek();
    if(shown!==target)schedule();else lastTick=0;
  };
  const schedule=()=>{if(!frame&&enabled&&inView&&!document.hidden)frame=queueFrame(tick);};
  const onScroll=()=>{if(!enabled&&objectURL&&!loading&&allowed()&&root.getBoundingClientRect().top>=-64)activate();target=clamp((scrollY-start)/distance);schedule();};
  const measure=()=>{start=root.getBoundingClientRect().top+scrollY;distance=Math.max(1,root.offsetHeight-root.querySelector('.mercedes-stage').offsetHeight);onScroll();};
  const reset=()=>{
    enabled=false;cancelFrame(frame);frame=0;lastTick=0;clearTimeout(seekTimer);clearTimeout(releaseTimer);
    if(presentCallback)video.cancelVideoFrameCallback?.(presentCallback);presentCallback=0;
    seekBusy=false;lastSeekFrame=-1;
    video.pause();root.dataset.state='static';root.dataset.mode='static';
    picture.querySelector('img').src=root.dataset.static;lastPaint=-1;paint(0);ring.hidden=true;
  };
  const fallback=()=>{reset();root.dataset.state='fallback';};
  const activate=()=>{
    if(dead||!allowed()||!Number.isFinite(video.duration))return;
    // Do not expand a late-loading pin underneath a visitor already in the catalogue.
    if(scrollY>root.getBoundingClientRect().top+scrollY+root.offsetHeight-96)return;
    enabled=true;root.dataset.mode='cinematic';root.dataset.state='ready';ring.hidden=true;lastPaint=-1;
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
        const ready=()=>{cleanup();resolve();},fail=()=>{cleanup();reject(new Error('Video decode '+(video.error?.code||'timeout')));};
        video.addEventListener('loadeddata',ready,{once:true});video.addEventListener('error',fail,{once:true});
        loadTimer=setTimeout(fail,12000);video.src=objectURL;video.load();
      });
      activate();
    }catch(error){
      root.dataset.failure=error.message||error.name;
      if(objectURL){URL.revokeObjectURL(objectURL);objectURL=null;video.removeAttribute('src');video.load();}
      if(!dead)fallback();
    }finally{clearTimeout(watchdog);loading=false;ring.hidden=true;}
  }
  const apply=()=>{
    if(!allowed()){controller?.abort();reset();return;}
    root.dataset.mode='cinematic';picture.querySelector('img').src=root.dataset.poster;lastPaint=-1;paint(0);
    if(document.readyState==='complete')load();
  };
  // Let the decoded image reach the compositor before another seek replaces it.
  // On browsers without frame callbacks, one paint plus the watchdog releases it.
  video.addEventListener('seeked',()=>{
    clearTimeout(seekTimer);
    if(!video.requestVideoFrameCallback)queueFrame(releaseSeek);
    clearTimeout(releaseTimer);releaseTimer=setTimeout(releaseSeek,34);
  });
  video.addEventListener('error',()=>{if(enabled)fallback();});
  const observer=new IntersectionObserver(entries=>{inView=entries[0].isIntersecting;if(inView){onScroll();}else{cancelFrame(frame);frame=0;lastTick=0;}},{threshold:0});
  observer.observe(root);
  window.addEventListener('scroll',onScroll,{passive:true});window.addEventListener('resize',measure,{passive:true});
  window.addEventListener('load',apply,{once:true});queries.forEach(q=>q.addEventListener('change',()=>{apply();}));connection?.addEventListener?.('change',apply);
  document.addEventListener('visibilitychange',()=>{if(document.hidden){cancelFrame(frame);frame=0;lastTick=0;}else onScroll();});
  window.addEventListener('pageshow',event=>{if(event.persisted){measure();apply();}});
  window.addEventListener('pagehide',event=>{if(event.persisted)return;dead=true;controller?.abort();reset();observer.disconnect();if(objectURL)URL.revokeObjectURL(objectURL);});
  root.querySelectorAll('a[href="#fleet"]').forEach(link=>link.addEventListener('click',event=>{
    const fleet=document.querySelector('#fleet');if(!fleet)return;
    event.preventDefault();history.pushState(null,'','#fleet');window.scrollTo({top:fleet.getBoundingClientRect().top+scrollY-96,behavior:'instant'});
    const heading=fleet.querySelector('h2');if(heading){heading.tabIndex=-1;heading.focus({preventScroll:true});}
  }));
  measure();apply();
}
