// Optional, local effects. No work is scheduled on touch or reduced-motion.
export function initGarageUI(){
  const desktopEffects=matchMedia('(hover:hover) and (pointer:fine) and (prefers-reduced-motion:no-preference)');
  let stopLight=()=>{};
  const mountLight=()=>{
    stopLight();if(!desktopEffects.matches)return;
    const light=document.createElement('div');light.className='catalog-light';light.setAttribute('aria-hidden','true');document.body.append(light);
    let frame=0,x=0,y=0;
    const draw=()=>{frame=0;light.style.transform=`translate3d(${x-240}px,${y-240}px,0)`;};
    const move=event=>{
      if(event.pointerType==='touch')return;
      if(event.target.closest('.car-grid')){x=event.clientX;y=event.clientY;light.dataset.visible='';if(!frame)frame=requestAnimationFrame(draw);}
      else delete light.dataset.visible;
    };
    const hide=()=>{delete light.dataset.visible;};
    document.addEventListener('pointermove',move,{passive:true});document.addEventListener('pointerleave',hide);
    window.addEventListener('scroll',hide,{passive:true});
    stopLight=()=>{cancelAnimationFrame(frame);light.remove();document.removeEventListener('pointermove',move);document.removeEventListener('pointerleave',hide);window.removeEventListener('scroll',hide);};
  };
  mountLight();desktopEffects.addEventListener('change',mountLight);

  const sheet=document.querySelector('.catalog-sidebar');
  if(!sheet)return;
  const narrow=matchMedia('(max-width:767px)'),form=sheet.querySelector('form'),summary=sheet.querySelector('summary');
  const close=sheet.querySelector('[data-sheet-close]');
  let locked=[],lastOverflow='',active=false;
  const restore=()=>{
    if(!active)return;active=false;
    for(const [node,inert] of locked)node.inert=inert;
    locked=[];document.body.style.overflow=lastOverflow;
    form.removeAttribute('role');form.removeAttribute('aria-modal');
  };
  const sync=()=>{
    if(!sheet.open||!narrow.matches){restore();return;}
    if(active)return;active=true;
    lastOverflow=document.body.style.overflow;document.body.style.overflow='hidden';
    // Inert siblings along the form's ancestor chain, retaining prior state.
    let current=form;
    while(current.parentElement&&current.parentElement!==document.documentElement){
      for(const node of current.parentElement.children)if(node!==current){locked.push([node,node.inert]);node.inert=true;}
      current=current.parentElement;
    }
    form.setAttribute('role','dialog');form.setAttribute('aria-modal','true');
    form.setAttribute('aria-labelledby','catalog-filter-title');close?.focus({preventScroll:true});
  };
  const shut=()=>{sheet.open=false;restore();summary.focus({preventScroll:true});};
  close?.addEventListener('click',shut);
  sheet.addEventListener('toggle',sync);narrow.addEventListener('change',sync);
  document.addEventListener('keydown',event=>{
    if(!active)return;
    if(event.key==='Escape'){event.preventDefault();shut();}
    if(event.key==='Tab'){
      const items=[...form.querySelectorAll('a[href],button,input:not([type=hidden]),select,textarea')].filter(el=>!el.disabled);
      const first=items[0],last=items.at(-1);
      if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}
      else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}
    }
  });
  // Pointer on the backdrop closes the sheet; submit retains existing AJAX.
  sheet.addEventListener('click',event=>{if(active&&event.target===sheet)shut();});
  form.addEventListener('submit',()=>{if(active)shut();});
  window.addEventListener('pagehide',restore);
}
