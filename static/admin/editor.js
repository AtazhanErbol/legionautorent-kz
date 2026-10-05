(() => {
  const init=()=>{
    const groups=[...document.querySelectorAll('.translation-inline')];
    if(groups.length&&!document.querySelector('.language-editor-tabs')){
      const tabs=document.createElement('div');tabs.className='language-editor-tabs';tabs.setAttribute('role','tablist');
      ['ru','kk','en'].forEach(language=>{const button=document.createElement('button');button.type='button';button.textContent=language==='kk'?'KZ':language.toUpperCase();button.dataset.language=language;button.tabIndex=language==='ru'?0:-1;button.setAttribute('role','tab');button.setAttribute('aria-selected',String(language==='ru'));
        button.onclick=()=>{
          tabs.querySelectorAll('button').forEach(b=>{b.setAttribute('aria-selected',String(b===button));b.tabIndex=b===button?0:-1;});
          groups.forEach(group=>{
            const rows=[...group.querySelectorAll('.inline-related:not(.empty-form)')];
            const present=rows.map(row=>row.querySelector('select[name$="-language"]')?.value).filter(Boolean);
            if(language!=='ru'&&!present.includes(language)){
              const empty=rows.find(row=>!row.querySelector('select[name$="-language"]')?.value);
              const select=empty?.querySelector('select[name$="-language"]');if(select)select.value=language;
            }
            rows.forEach(row=>{
            const select=row.querySelector('select[name$="-language"]');if(!select)return;
            row.hidden=language==='ru'||select.value!==language;
          });});
        };button.addEventListener('keydown',event=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;event.preventDefault();const all=[...tabs.querySelectorAll('button')],i=all.indexOf(button);const next=event.key==='Home'?0:event.key==='End'?2:(i+(event.key==='ArrowRight'?1:2))%3;all[next].click();all[next].focus();});tabs.append(button);
      });
      const form=document.querySelector('#content-main form');form?.prepend(tabs);
      const errorRow=document.querySelector('.translation-inline .inline-related .errorlist')?.closest('.inline-related');const errorLanguage=errorRow?.querySelector('select[name$="-language"]')?.value;
      (tabs.querySelector(`[data-language="${errorLanguage || 'ru'}"]`)||tabs.querySelector('button'))?.click();
    }
    document.querySelectorAll('.sortable-inline tr.has_original').forEach(row=>{
      if(row.dataset.sortReady)return;row.dataset.sortReady='true';
      const controls=document.createElement('span');controls.className='cms-order-controls';
      ['↑','↓'].forEach((label,index)=>{const button=document.createElement('button');button.type='button';button.textContent=label;button.setAttribute('aria-label',index?'Переместить фото ниже':'Переместить фото выше');button.onclick=()=>{const sibling=index?row.nextElementSibling:row.previousElementSibling;if(sibling?.classList.contains('has_original')){if(index)sibling.after(row);else sibling.before(row);[...row.parentNode.querySelectorAll('tr.has_original')].forEach((item,i)=>{const input=item.querySelector('[name$="-sort_order"]');if(input){input.value=i;input.dispatchEvent(new Event('change',{bubbles:true}));}})};};controls.append(button);});row.querySelector('td')?.append(controls);
      row.draggable=true;row.addEventListener('dragstart',()=>{window.legionDraggedRow=row;row.classList.add('dragging');});
      row.addEventListener('dragend',()=>{row.classList.remove('dragging');window.legionDraggedRow=null;});
      row.addEventListener('dragover',event=>{event.preventDefault();const dragged=window.legionDraggedRow;if(dragged&&dragged!==row&&dragged.parentNode===row.parentNode)row.before(dragged);});
      row.addEventListener('drop',()=>{[...row.parentNode.querySelectorAll('tr.has_original')].forEach((item,index)=>{const input=item.querySelector('[name$="-sort_order"]');if(input){input.value=index;input.dispatchEvent(new Event('change',{bubbles:true}));}});});
    });
  };document.addEventListener('DOMContentLoaded',init);document.addEventListener('formset:added',init);
})();
