import {gsap} from 'gsap';
import {ScrollTrigger} from 'gsap/ScrollTrigger';
import {createFilmHero} from './hero-film';

gsap.registerPlugin(ScrollTrigger);

// The clip is paused. Scrolling selects its time; there is no autoplay or loop.
export async function createVideoHero(hero){
  if(hero.hasAttribute('data-story'))return createFilmHero(hero);
  const stage=hero.querySelector('.hero-stage'),poster=stage.querySelector('.hero-poster');
  const copy=hero.querySelector('.hero-copy'),end=hero.querySelector('.hero-end');
  const reduced=matchMedia('(prefers-reduced-motion: reduce)');
  const desktop=matchMedia('(min-width:768px)');
  const video=document.createElement('video');
  video.className='hero-video';video.muted=true;video.playsInline=true;
  video.preload='auto';video.setAttribute('aria-hidden','true');video.tabIndex=-1;
  video.disablePictureInPicture=true;
  let trigger,disposed=false,frame=null,desired=0,duration=0,lastRequested=-1;
  let readyReject,readyTimer,seekTimer;
  const resetCopy=()=>{for(const node of [copy,end])for(const property of ['opacity','visibility','pointer-events'])node.style.removeProperty(property);};
  const dispose=(fallback=false)=>{
    if(disposed)return;disposed=true;
    readyReject?.(new Error('Hero video initialization cancelled'));readyReject=null;
    cancelAnimationFrame(frame);clearTimeout(readyTimer);clearTimeout(seekTimer);
    trigger?.kill(true);resetCopy();poster.style.removeProperty('opacity');
    reduced.removeEventListener('change',onPreference);
    desktop.removeEventListener('change',onPreference);
    document.removeEventListener('visibilitychange',onVisibility);
    window.removeEventListener('pagehide',onPageHide);
    video.removeEventListener('seeked',onSeeked);video.removeEventListener('error',onError);
    video.pause();video.removeAttribute('src');video.load();video.remove();
    delete hero.dataset.videoStage;
    hero.dataset.state=fallback?'fallback':'idle';
    if(fallback)ScrollTrigger.refresh();
  };
  const onError=()=>{readyReject?.(new Error('Hero video could not be decoded'));dispose(true);};
  const onPreference=()=>{if(reduced.matches||!desktop.matches)dispose(true);};
  const onPageHide=()=>dispose();
  const seek=()=>{
    frame=null;
    if(disposed||document.hidden||video.seeking||!duration)return;
    if(Math.abs(video.currentTime-desired)<1/30)return;
    if(Math.abs(lastRequested-desired)<1/120)return;
    lastRequested=desired;
    try{
      video.currentTime=desired;
      // A stalled network seek must not leave the page permanently pinned.
      clearTimeout(seekTimer);seekTimer=setTimeout(()=>{if(video.seeking)dispose(true);},12000);
    }catch{dispose(true);}
  };
  const schedule=()=>{if(!disposed&&frame===null)frame=requestAnimationFrame(seek);};
  const onSeeked=()=>{clearTimeout(seekTimer);lastRequested=-1;schedule();};
  const onVisibility=()=>{if(!document.hidden)schedule();};
  const present=progress=>{
    desired=Math.max(0,Math.min(duration-1/30,progress*duration));
    const first=1-Math.min(1,Math.max(0,(progress-.2)/.3));
    const last=Math.min(1,Math.max(0,(progress-.64)/.22));
    copy.style.opacity=String(first);copy.style.visibility=first>0?'visible':'hidden';
    copy.style.pointerEvents=first>.15?'auto':'none';
    end.style.opacity=String(last);end.style.visibility=last>0?'visible':'hidden';
    end.style.pointerEvents=last>.4?'auto':'none';
    hero.dataset.videoStage=progress<.34?'front':progress<.67?'profile':'rear';
    schedule();
  };
  video.addEventListener('error',onError);
  video.addEventListener('seeked',onSeeked);
  reduced.addEventListener('change',onPreference);
  desktop.addEventListener('change',onPreference);
  document.addEventListener('visibilitychange',onVisibility);
  window.addEventListener('pagehide',onPageHide,{once:true});
  stage.insertBefore(video,stage.querySelector('.hero-shade'));
  try{
    await new Promise((resolve,reject)=>{
      readyReject=reject;
      const onData=()=>{
        if(!Number.isFinite(video.duration)||video.duration<=0){reject(new Error('Hero video needs a finite duration'));return;}
        duration=video.duration;resolve();
      };
      video.addEventListener('loadeddata',onData,{once:true});
      readyTimer=setTimeout(()=>reject(new Error('Hero video load timed out')),12000);
      video.src=hero.dataset.video;video.load();
    });
    readyReject=null;clearTimeout(readyTimer);
    if(disposed||reduced.matches){dispose(true);return {dispose};}
    video.pause();
    trigger=ScrollTrigger.create({
      trigger:hero,start:'top top',end:()=>`+=${innerHeight*1.2}`,pin:true,
      invalidateOnRefresh:true,onUpdate:self=>present(self.progress),onRefresh:self=>present(self.progress),
    });
    present(trigger.progress);video.style.opacity='1';poster.style.opacity='0';
    hero.dataset.state='video-ready';
  }catch(error){dispose(true);throw error;}
  return {video,dispose};
}
