import {gsap} from 'gsap';
import {ScrollTrigger} from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

// A paused, real camera orbit and one damped composition/video clock.
// Every transform is applied to the whole studio frame, never to a cutout car.
export async function createFilmHero(hero){
  const stage=hero.querySelector('.hero-stage'),media=hero.querySelector('.hero-media');
  const poster=stage.querySelector('.hero-poster');
  const intro=hero.querySelector('.hero-copy'),about=hero.querySelector('.story-about');
  const details=hero.querySelector('.story-details'),rear=hero.querySelector('.hero-end');
  const search=hero.querySelector('.search-wrap'),bar=hero.querySelector('.story-progress-fill');
  const detailItems=[...details.querySelectorAll('.story-detail, .story-detail-title')];
  const panels=[intro,about,details,rear,search];
  const animated=[media,...panels,...detailItems,bar].filter(Boolean);
  const originals=animated.map(node=>({node,style:node.getAttribute('style'),inert:node.inert,aria:node.getAttribute('aria-hidden')}));
  const reduced=matchMedia('(prefers-reduced-motion: reduce)'),desktop=matchMedia('(min-width:900px)');
  const video=document.createElement('video');
  video.className='hero-video';video.muted=true;video.playsInline=true;
  video.preload='auto';video.setAttribute('aria-hidden','true');video.tabIndex=-1;video.disablePictureInPicture=true;
  let trigger,timeline,disposed=false,frame=null,desired=0,duration=0,lastRequested=-1;
  let readyReject,readyTimer,seekTimer,visibility;
  let target=0,displayed=0,lastTick=0,inView=true;
  const timeKeys=[[0,0],[.2,.15],[.45,.58],[.7,.76],[.9,1],[1,1]];
  const dispose=(fallback=false)=>{
    if(disposed)return;disposed=true;
    readyReject?.(new Error('Hero video initialization cancelled'));readyReject=null;
    cancelAnimationFrame(frame);clearTimeout(readyTimer);clearTimeout(seekTimer);
    trigger?.kill(true);timeline?.kill();
    visibility?.disconnect();
    for(const {node,style,inert,aria} of originals){
      if(style===null)node.removeAttribute('style');else node.setAttribute('style',style);
      node.inert=inert;if(aria===null)node.removeAttribute('aria-hidden');else node.setAttribute('aria-hidden',aria);
    }
    poster.style.removeProperty('opacity');
    if(fallback&&hero.dataset.staticPoster)poster.src=hero.dataset.staticPoster;
    reduced.removeEventListener('change',onPreference);desktop.removeEventListener('change',onPreference);
    document.removeEventListener('visibilitychange',onVisibility);
    window.removeEventListener('pagehide',onPageHide);window.removeEventListener('pageshow',onPageShow);
    video.removeEventListener('seeked',onSeeked);video.removeEventListener('error',onError);
    video.pause();video.removeAttribute('src');video.load();video.remove();
    delete hero.dataset.videoStage;delete hero.dataset.storyProgress;
    hero.dataset.state=fallback?'fallback':'idle';
    if(fallback)ScrollTrigger.refresh();
  };
  const onError=()=>{readyReject?.(new Error('Hero video could not be decoded'));dispose(true);};
  const onPreference=()=>{if(reduced.matches||!desktop.matches)dispose(true);};
  const onPageHide=event=>{if(!event.persisted)dispose();};
  const onPageShow=event=>{if(event.persisted&&!disposed){ScrollTrigger.refresh();target=displayed=trigger?.progress||0;present(displayed);schedule();}};
  const seek=()=>{
    if(disposed||document.hidden||video.seeking||!duration)return;
    if(Math.abs(video.currentTime-desired)<1/120||Math.abs(lastRequested-desired)<1/240)return;
    lastRequested=desired;
    try{
      video.currentTime=desired;
      clearTimeout(seekTimer);seekTimer=setTimeout(()=>{if(video.seeking)dispose(true);},12000);
    }catch{dispose(true);}
  };
  // One custom RAF owns both composition and seeking. Geometry is read only by
  // ScrollTrigger at refresh; the clock writes transforms/opacity, never layout.
  const tick=now=>{
    frame=null;
    if(disposed||document.hidden||!inView){lastTick=0;return;}
    const elapsed=lastTick?Math.min(64,now-lastTick):1000/60;lastTick=now;
    const difference=target-displayed;
    if(Math.abs(difference)>0.000025){
      displayed+=difference*(1-Math.exp(-elapsed/75));
      if(Math.abs(target-displayed)<0.000025)displayed=target;
      present(displayed);
    }
    seek();
    if(displayed!==target)schedule();else lastTick=0;
  };
  const schedule=()=>{if(!disposed&&inView&&!document.hidden&&frame===null)frame=requestAnimationFrame(tick);};
  const onSeeked=()=>{clearTimeout(seekTimer);lastRequested=-1;schedule();};
  const onVisibility=()=>{lastTick=0;if(document.hidden){cancelAnimationFrame(frame);frame=null;}else schedule();};
  const setInteractive=(node,active)=>{
    if(node.inert===!active&&node.getAttribute('aria-hidden')===String(!active))return;
    if(!active&&node.contains(document.activeElement))hero.focus({preventScroll:true});
    node.inert=!active;node.setAttribute('aria-hidden',String(!active));node.style.pointerEvents=active?'auto':'none';
  };
  const timeAt=progress=>{
    for(let i=1;i<timeKeys.length;i++)if(progress<=timeKeys[i][0]){
      const [a,t0]=timeKeys[i-1],[b,t1]=timeKeys[i];return (t0+(t1-t0)*(progress-a)/(b-a))*(duration-1/24);
    }
    return duration-1/24;
  };
  const present=progress=>{
    if(disposed||!timeline)return;
    timeline.progress(progress);desired=Math.max(0,timeAt(progress));
    setInteractive(intro,progress<.20);setInteractive(about,progress>=.28&&progress<.43);
    setInteractive(details,progress>=.5&&progress<.69);setInteractive(rear,progress>=.79&&progress<.97);
    setInteractive(search,progress>=.94);
    hero.dataset.videoStage=progress<.2?'front':progress<.45?'composition':progress<.7?'details':progress<.9?'rear':'exit';
    hero.dataset.storyProgress=progress.toFixed(4);
  };
  const aim=progress=>{target=progress;if(!inView){displayed=target;present(displayed);}else schedule();};
  video.addEventListener('error',onError);video.addEventListener('seeked',onSeeked);
  reduced.addEventListener('change',onPreference);desktop.addEventListener('change',onPreference);
  document.addEventListener('visibilitychange',onVisibility);
  window.addEventListener('pagehide',onPageHide);window.addEventListener('pageshow',onPageShow);
  media.append(video);
  try{
    await new Promise((resolve,reject)=>{
      readyReject=reject;
      video.addEventListener('loadeddata',()=>{
        if(!Number.isFinite(video.duration)||video.duration<=0){reject(new Error('Hero video needs a finite duration'));return;}
        duration=video.duration;resolve();
      },{once:true});
      readyTimer=setTimeout(()=>reject(new Error('Hero video load timed out')),12000);
      video.src=hero.dataset.video;video.load();
    });
    readyReject=null;clearTimeout(readyTimer);
    if(disposed||reduced.matches||!desktop.matches){dispose(true);return {dispose};}
    video.pause();hero.dataset.state='video-ready';
    gsap.set(media,{scale:1.04,xPercent:0,yPercent:6,autoAlpha:1});
    gsap.set(intro,{autoAlpha:1,yPercent:0});
    gsap.set([about,rear],{autoAlpha:0,y:48});
    gsap.set(details,{autoAlpha:1,yPercent:0});
    gsap.set(detailItems,{autoAlpha:0,y:64});
    gsap.set(search,{autoAlpha:0,y:40});
    timeline=gsap.timeline({paused:true,defaults:{ease:'none'}})
      .to(media,{scale:1,yPercent:6,duration:.18},0)
      .to(intro,{yPercent:-9,autoAlpha:0,duration:.11},.13)
      .to(media,{scale:.76,xPercent:-19,yPercent:0,duration:.14},.18)
      .to(about,{autoAlpha:1,y:0,duration:.12},.22)
      .to(about,{autoAlpha:0,y:-64,duration:.10},.4)
      .to(media,{scale:.58,xPercent:-23,yPercent:-15,autoAlpha:0,duration:.14},.4)
      .to(detailItems,{autoAlpha:1,y:0,duration:.13,stagger:.025},.43)
      .to(details,{autoAlpha:0,yPercent:-12,duration:.10},.66)
      .set(media,{scale:.92,xPercent:-19,yPercent:2},.65)
      .to(media,{autoAlpha:1,duration:.13},.68)
      .to(rear,{autoAlpha:1,y:0,duration:.12},.72)
      .to(media,{scale:.88,yPercent:-6,duration:.10},.9)
      .to(rear,{y:-48,autoAlpha:.35,duration:.09},.91)
      .to(search,{autoAlpha:1,y:0,duration:.08},.9)
      .to(bar,{scaleX:1,duration:1},0);
    trigger=ScrollTrigger.create({id:'legion-story',trigger:hero,start:'top top',end:()=>`+=${innerHeight*2.6}`,pin:true,
      invalidateOnRefresh:true,onUpdate:self=>aim(self.progress),onRefresh:self=>{target=displayed=self.progress;present(displayed);schedule();}});
    target=displayed=trigger.progress;present(displayed);schedule();video.style.opacity='1';poster.style.opacity='0';
    visibility=new IntersectionObserver(entries=>{inView=entries[0].isIntersecting;if(inView)schedule();else{cancelAnimationFrame(frame);frame=null;lastTick=0;}},{threshold:0});
    visibility.observe(hero);
  }catch(error){dispose(true);throw error;}
  return {video,dispose};
}
