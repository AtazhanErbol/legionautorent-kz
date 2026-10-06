// One scroll pipeline on every device. No video seeks or autoplay permission.
import {queueFrame,cancelFrame} from './motion-frame.js';

export function initMercedesPreview(root){
  const data=JSON.parse(root.querySelector('#hero-frames').textContent);
  const canvas=root.querySelector('canvas'),poster=root.querySelector('img');
  let context;
  const stage=root.querySelector('.mercedes-stage'),booking=root.querySelector('.search-wrap');
  const pin=root.querySelector('.mercedes-pin');
  const progress=root.querySelector('.mercedes-progress span'),chapter=root.querySelector('[data-chapter]');
  const reduced=matchMedia('(prefers-reduced-motion:reduce)'),compact=matchMedia('(max-width:899px)');
  const bands=[...root.querySelectorAll('[data-band]')].map(el=>({el,start:+el.dataset.start,end:+el.dataset.end,opacity:-1}));
  const clamp=n=>Math.max(0,Math.min(1,n));
  let variant,enabled=false,dead=false,inView=true,frame=0,lastTick=0,shown=0,target=0;
  let start=0,distance=1,lastWidth=innerWidth,drawn=-1,epoch=0,loaded=0;
  let activeFetches=0,activeDecodes=0,background=0,hasMoved=false;
  const encoded=new Map(),images=new Map(),fetching=new Set(),decoding=new Set();
  const requests=[],decodeQueue=[],controllers=new Set(),failed=new Set();
  const maxImages=()=>compact.matches?18:26;
  const workerJobs=new Map();let worker,workerReady=false,workerSequence=0;
  const stopWorker=()=>{
    workerReady=false;worker?.terminate();worker=null;
    workerJobs.forEach(job=>job.reject());workerJobs.clear();
  };
  function startWorker(){if(worker||!data.count||reduced.matches||!('Worker'in window))return;try{
    worker=new Worker(new URL('./hero-frame-worker.js',import.meta.url));
    worker.onmessage=({data})=>{
      if('ready'in data){workerReady=data.ready;if(!data.ready)stopWorker();return;}
      const job=workerJobs.get(data.id);workerJobs.delete(data.id);
      if(!job){data.image?.close();return;}
      if(data.error)job.reject();else job.resolve(data.image);
    };
    worker.onerror=stopWorker;
  }catch{/* Image decoding remains available without workers. */}}

  function paint(p){
    const staticMode=!enabled;
    let active=0;
    bands.forEach((band,index)=>{
      const smooth=n=>n*n*(3-2*n);
      const enter=index?smooth(clamp((p-band.start)/.01)):1;
      const leave=index===bands.length-1?1:1-smooth(clamp((p-band.end+.01)/.01));
      const opacity=staticMode?1:enter*leave;
      if(p>=band.start)active=index;
      if(Math.abs(opacity-band.opacity)<.0005)return;
      band.opacity=opacity;
      band.el.style.opacity=String(opacity);
      band.el.style.transform=`translateY(${(1-enter)*12}px)`;
      band.el.style.visibility=opacity>.001?'visible':'hidden';
      band.el.inert=opacity<=.001;
      band.el.setAttribute('aria-hidden',String(opacity<=.001));
    });
    const visible=staticMode||compact.matches||booking.contains(document.activeElement)||bands[0].el.style.visibility==='visible';
    booking.style.opacity=visible?'1':'0';booking.style.visibility=visible?'visible':'hidden';booking.inert=!visible;
    progress.style.transform=`scaleX(${p})`;chapter.textContent=String(active+1).padStart(2,'0');
    root.dataset.progress=p.toFixed(4);
  }

  function draw(index){
    const image=images.get(index);
    if(!image)return false;
    if(drawn!==index){
      context||=canvas.getContext('2d',{alpha:false,desynchronized:true});
      if(!context){fallback();return false;}
      context.drawImage(image,0,0,canvas.width,canvas.height);
      images.delete(index);images.set(index,image);drawn=index;
      root.dataset.frame=String(index);
      if(root.dataset.rendered!=='true')root.dataset.rendered='true';
      if(root.dataset.state!=='ready')root.dataset.state='ready';
    }
    return true;
  }

  function trimImages(){
    while(images.size>maxImages()){
      const candidate=[...images.keys()].find(index=>index!==drawn);
      if(candidate===undefined)break;
      images.get(candidate).close?.();images.delete(candidate);
    }
    if(root.dataset.decoded!==String(images.size))root.dataset.decoded=String(images.size);
  }

  async function decode(blob){
    if(workerReady)try{
      return await new Promise((resolve,reject)=>{
        const id=++workerSequence;workerJobs.set(id,{resolve,reject});
        worker.postMessage({id,blob});
      });
    }catch{/* Fall back if worker decoding is unavailable. */}
    if('createImageBitmap'in window){
      try{return await createImageBitmap(blob);}catch{/* Older Safari uses Image. */}
    }
    const image=new Image(),url=URL.createObjectURL(blob);
    try{
      await new Promise((resolve,reject)=>{image.onload=resolve;image.onerror=reject;image.src=url;});
      return image;
    }finally{URL.revokeObjectURL(url);}
  }

  function pumpDecodes(){
    while(enabled&&activeDecodes<2&&decodeQueue.length){
      const index=decodeQueue.shift(),blob=encoded.get(index),generation=epoch;
      if(!blob||images.has(index)){decoding.delete(index);continue;}
      activeDecodes++;
      decode(blob).then(image=>{
        if(generation!==epoch||dead){image.close?.();return;}
        images.set(index,image);trimImages();schedule();
      }).catch(()=>{
        if(generation===epoch){failed.add(Math.floor(index/data.packSize));if(drawn<0)fallback();}
      }).finally(()=>{
        if(generation===epoch){activeDecodes--;decoding.delete(index);pumpDecodes();}
      });
    }
  }

  function needFrame(index,priority=true){
    if(images.has(index)||decoding.has(index))return;
    if(!encoded.has(index)){needPack(Math.floor(index/data.packSize),priority);return;}
    decoding.add(index);
    if(priority)decodeQueue.unshift(index);else decodeQueue.push(index);
    pumpDecodes();
  }

  function unpack(buffer,pack){
    const view=new DataView(buffer);let offset=0,index=pack*data.packSize;
    const frames=[];
    while(offset<buffer.byteLength){
      if(offset+4>buffer.byteLength)throw new Error('Incomplete frame pack');
      const size=view.getUint32(offset,true);offset+=4;
      if(!size||offset+size>buffer.byteLength)throw new Error('Invalid frame pack');
      frames.push(new Blob([new Uint8Array(buffer,offset,size)],{type:'image/webp'}));offset+=size;
    }
    if(frames.length!==Math.min(data.packSize,data.count-index))throw new Error('Frame count mismatch');
    frames.forEach(blob=>encoded.set(index++,blob));loaded++;
    root.dataset.loadedPacks=String(loaded);
  }

  function needPack(index,priority=false){
    if(index<0||index>=variant.packs.length||encoded.has(index*data.packSize)||fetching.has(index)||failed.has(index))return;
    const queued=requests.indexOf(index);
    if(queued!==-1){if(priority){requests.splice(queued,1);requests.unshift(index);}}
    else if(priority)requests.unshift(index);else requests.push(index);
    pumpFetches();
  }

  function pumpFetches(){
    if(!enabled||document.hidden||!inView)return;
    while(activeFetches<2){
      if(!requests.length){
        while(background<variant.packs.length&&(encoded.has(background*data.packSize)||fetching.has(background)||failed.has(background)))background++;
        if((!hasMoved&&background>=1)||navigator.connection?.saveData||background>=variant.packs.length)return;
        requests.push(background++);
      }
      const index=requests.shift(),generation=epoch,controller=new AbortController();
      controllers.add(controller);fetching.add(index);activeFetches++;
      const timeout=setTimeout(()=>controller.abort(),15000);
      fetch(variant.packs[index],{signal:controller.signal,priority:'low'}).then(response=>{
        if(!response.ok)throw new Error('Frame response '+response.status);
        return response.arrayBuffer();
      }).then(buffer=>{
        if(generation!==epoch||dead)return;
        unpack(buffer,index);
        needFrame(Math.round(shown*(data.count-1)));
        needFrame(Math.round(target*(data.count-1)));
        if(drawn<0)needFrame(0);
        schedule();
      }).catch(error=>{
        if(generation===epoch&&!dead){failed.add(index);root.dataset.failure=error.message||'Frame load';if(loaded===0&&index===0)fallback();}
      }).finally(()=>{
        clearTimeout(timeout);controllers.delete(controller);
        if(generation===epoch){activeFetches--;fetching.delete(index);pumpFetches();}
      });
    }
  }

  function tick(now){
    frame=0;
    if(!enabled||!inView||document.hidden){lastTick=0;return;}
    if(!hasMoved){primePoster();lastTick=0;return;}
    const dt=lastTick?Math.min(64,now-lastTick):16.667;lastTick=now;
    const change=(target-shown)*(1-Math.exp(-dt/130));
    const next=clamp(shown+Math.max(-dt/1400,Math.min(dt/1400,change)));
    const candidate=Math.round(next*(data.count-1));
    const direction=target>=shown?1:-1;
    const stride=Math.max(1,Math.abs(candidate-Math.round(shown*(data.count-1))));
    // Input time keeps advancing while a slow decoder catches up. Keep only
    // current/predicted requests; obsolete speculative frames must not queue.
    decodeQueue.forEach(index=>decoding.delete(index));decodeQueue.length=0;
    needFrame(candidate);
    for(let step=1;step<=3;step++)needFrame(Math.max(0,Math.min(data.count-1,candidate+step*stride*direction)),false);
    shown=Math.abs(target-next)<.00015?target:next;
    let available=candidate;
    if(!images.has(available)){
      const forward=candidate>=drawn;
      const nearby=[...images.keys()].filter(index=>Math.abs(index-candidate)<=32&&
        (forward?index>=drawn&&index<=candidate:index<=drawn&&index>=candidate));
      available=forward?Math.max(-1,...nearby):Math.min(data.count,...nearby);
    }
    if(draw(available))paint(drawn/(data.count-1));
    else if(drawn<0&&draw(0))paint(0);
    if(Math.abs(target-shown)>.00015)schedule();else lastTick=0;
  }

  function schedule(){if(!frame&&enabled&&inView&&!document.hidden)frame=queueFrame(tick);}
  function onScroll(){
    target=clamp((scrollY-start)/distance);
    if(target>.0001){hasMoved=true;startWorker();}
    if(!enabled)return;
    needPack(Math.floor(Math.round(target*(data.count-1))/data.packSize),true);pumpFetches();schedule();
  }
  function measure(){
    start=root.getBoundingClientRect().top+scrollY;
    distance=Math.max(1,pin.offsetHeight-stage.offsetHeight);
    onScroll();
  }
  function release(){
    epoch++;controllers.forEach(controller=>controller.abort());controllers.clear();
    cancelFrame(frame);frame=0;lastTick=0;
    images.forEach(image=>image.close?.());images.clear();encoded.clear();fetching.clear();decoding.clear();
    requests.length=0;decodeQueue.length=0;failed.clear();activeFetches=activeDecodes=background=loaded=0;drawn=-1;
  }
  function fallback(){
    enabled=false;release();root.dataset.mode='static';root.dataset.state='fallback';stage.append(booking);paint(0);
  }
  function apply(){
    if(!canvas.getContext||!data.count||reduced.matches){fallback();return;}
    enabled=false;release();hasMoved=false;variant=data[compact.matches?'mobile':'desktop'];
    bands.forEach(band=>band.opacity=-1);
    canvas.width=variant.width;canvas.height=variant.height;
    enabled=true;shown=0;root.dataset.variant=compact.matches?'mobile':'desktop';
    if(compact.matches)root.append(booking);else stage.append(booking);
    root.dataset.mode='cinematic';root.dataset.state='loading';root.dataset.rendered='false';paint(0);
    queueFrame(measure);
    primePoster();
    needPack(0,true);schedule();
  }
  function primePoster(){
    if(enabled&&poster.complete&&poster.naturalWidth&&!images.has(0)){
      images.set(0,poster);
      // Native HTML poster is already on screen. Avoid allocating/uploading a
      // canvas until movement; first frame downloading never delays the LCP.
      if(drawn<0){drawn=0;root.dataset.frame='0';root.dataset.state='ready';}
      schedule();
    }
  }

  const observer=new IntersectionObserver(([entry])=>{
    inView=entry.isIntersecting;
    if(inView){onScroll();pumpFetches();}else{cancelFrame(frame);frame=0;lastTick=0;}
  });observer.observe(root);
  window.addEventListener('scroll',onScroll,{passive:true});
  window.addEventListener('resize',()=>{if(innerWidth!==lastWidth){lastWidth=innerWidth;measure();}},{passive:true});
  window.addEventListener('orientationchange',()=>queueFrame(measure));
  compact.addEventListener('change',apply);reduced.addEventListener('change',apply);
  document.addEventListener('visibilitychange',()=>{
    if(document.hidden){cancelFrame(frame);frame=0;lastTick=0;}
    else{onScroll();pumpFetches();}
  });
  window.addEventListener('pageshow',event=>{if(event.persisted){measure();onScroll();}});
  window.addEventListener('pagehide',event=>{if(!event.persisted){dead=true;release();stopWorker();observer.disconnect();}});
  root.querySelectorAll('a[href="#fleet"]').forEach(link=>link.addEventListener('click',event=>{
    const fleet=document.querySelector('#fleet');if(!fleet)return;
    event.preventDefault();history.pushState(null,'','#fleet');window.scrollTo({top:fleet.getBoundingClientRect().top+scrollY-96,behavior:'instant'});
    const heading=fleet.querySelector('h2');if(heading){heading.tabIndex=-1;heading.focus({preventScroll:true});}
  }));
  if(location.hash==='#fleet')inView=false;
  poster.addEventListener('load',primePoster);
  apply();
}
