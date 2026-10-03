import {queueFrame,cancelFrame} from './motion-frame.js';
import './ambient-motion.css';

export function initAmbientMotion(){
  const reduced=matchMedia('(prefers-reduced-motion:reduce)');
  const coarse=matchMedia('(pointer:coarse)');
  const active=new Set(),animations=new Set();let frame=0;
  const animate=(element,frames,options)=>{
    const animation=element.animate(frames,options);animations.add(animation);
    animation.finished.catch(()=>{}).finally(()=>animations.delete(animation));
  };
  // Reserve final number widths; only decorative digit strips move. The real
  // price and units remain intact in the server HTML and accessible name.
  const rollers=[];
  document.querySelectorAll('.car-price-row strong,.mercedes-facts strong').forEach(el=>{
    const original=el.textContent,match=original.match(/^([\d\s]+)(.*)$/u);
    if(!match)return;
    const visual=document.createElement('span');visual.className='number-visual';visual.setAttribute('aria-hidden','true');
    for(const char of original){
      const digit=document.createElement('span');digit.textContent=char;
      if(/\d/.test(char)){
        digit.className='number-window';const strip=document.createElement('span');strip.className='number-strip';
        strip.textContent=Array.from({length:10},(_,i)=>(Number(char)+i+1)%10).join('\n');
        strip.style.transform='translateY(-90%)';digit.replaceChildren(strip);
      }
      visual.append(digit);
    }
    const sr=document.createElement('span');sr.className='number-value';
    while(el.firstChild)sr.append(el.firstChild);el.append(sr,visual);rollers.push(el);
  });
  const observer=new IntersectionObserver(entries=>{
    for(const entry of entries){
      const el=entry.target;
      if(el.matches('[data-ambient-parallax],.steps-grid,.class-marquee')){
        if(el.matches('.class-marquee')){el.dataset.visible=String(entry.isIntersecting);continue;}
        if(entry.isIntersecting)active.add(el);else active.delete(el);schedule();continue;
      }
      if(!entry.isIntersecting||el.closest('[hidden]'))continue;
      observer.unobserve(el);if(reduced.matches)continue;
      if(el.matches('.eyebrow'))animate(el.querySelector('svg path'),[{transform:'scaleX(0)'},{transform:'scaleX(1)'}],{duration:650,easing:'ease-out'});
      else el.querySelectorAll('.number-strip').forEach((strip,index)=>animate(strip,[{transform:'translateY(0)'},{transform:'translateY(-90%)'}],{duration:650+index*35,easing:'cubic-bezier(.16,1,.3,1)'}));
    }
  },{threshold:.08});
  rollers.forEach(el=>observer.observe(el));
  document.querySelectorAll('.eyebrow').forEach(el=>{
    const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 48 2');svg.setAttribute('aria-hidden','true');svg.classList.add('eyebrow-stroke');
    const path=document.createElementNS(svg.namespaceURI,'path');path.setAttribute('d','M0 1H48');path.setAttribute('stroke','currentColor');svg.append(path);el.prepend(svg);observer.observe(el);
  });
  const geometry=new Map();
  const measure=()=>{
    document.querySelectorAll('[data-ambient-parallax],.steps-grid').forEach(el=>{const r=el.getBoundingClientRect();geometry.set(el,{top:r.top+scrollY,height:r.height});});schedule();
  };
  const draw=()=>{
    frame=0;if(document.hidden)return;
    for(const el of active){const g=geometry.get(el);if(!g)continue;
      const progress=Math.max(0,Math.min(1,(scrollY+innerHeight-g.top)/(innerHeight+g.height)));
      if(el.matches('.steps-grid'))el.style.setProperty('--step-progress',reduced.matches?1:progress);
      else el.querySelector('img').style.transform=reduced.matches||coarse.matches?'none':`translateY(${(progress-.5)*24}px)`;
    }
  };
  const schedule=()=>{if(!frame&&!document.hidden)frame=queueFrame(draw);};
  document.querySelectorAll('[data-ambient-parallax],.steps-grid,.class-marquee').forEach(el=>observer.observe(el));
  window.addEventListener('scroll',schedule,{passive:true});window.addEventListener('resize',measure,{passive:true});
  const ro=new ResizeObserver(measure);ro.observe(document.body);measure();
  reduced.addEventListener('change',()=>{animations.forEach(a=>a.cancel());schedule();});
  document.addEventListener('visibilitychange',()=>{if(document.hidden){cancelFrame(frame);frame=0;}else schedule();});
  window.addEventListener('pagehide',()=>{animations.forEach(a=>a.cancel());cancelFrame(frame);frame=0;});
  const h1=document.querySelector('.mercedes-captions h1');
  if(h1&&!reduced.matches){const line=document.createElement('span');line.className='headline-mask-line';while(h1.firstChild)line.append(h1.firstChild);h1.append(line);h1.classList.add('headline-mask');animate(line,[{opacity:.6,transform:'translateY(18px)'},{opacity:1,transform:'translateY(0)'}],{duration:650,easing:'cubic-bezier(.2,.65,.3,1)'});}
}
