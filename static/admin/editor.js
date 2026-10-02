(() => {
  const init=()=>{
    const groups=[...document.querySelectorAll('.translation-inline')];
    if(groups.length&&!document.querySelector('.language-editor-tabs')){
      const tabs=document.createElement('div');tabs.className='language-editor-tabs';tabs.setAttribute('role','tablist');
      ['ru','kk','en'].forEach(language=>{const button=document.createElement('button');button.type='button';button.textContent=language.toUpperCase();button.setAttribute('role','tab');button.setAttribute('aria-selected',String(language==='ru'));
        button.onclick=()=>{
          tabs.querySelectorAll('button').forEach(b=>b.setAttribute('aria-selected',String(b===button)));
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
        };tabs.append(button);
      });
      const form=document.querySelector('#content-main form');form?.prepend(tabs);
      tabs.querySelector('button')?.click();
    }
    document.querySelectorAll('.sortable-inline tr.has_original').forEach(row=>{
      row.draggable=true;row.addEventListener('dragstart',()=>{window.legionDraggedRow=row;row.classList.add('dragging');});
      row.addEventListener('dragend',()=>{row.classList.remove('dragging');window.legionDraggedRow=null;});
      row.addEventListener('dragover',event=>{event.preventDefault();const dragged=window.legionDraggedRow;if(dragged&&dragged!==row&&dragged.parentNode===row.parentNode)row.before(dragged);});
      row.addEventListener('drop',()=>{[...row.parentNode.querySelectorAll('tr.has_original')].forEach((item,index)=>{const input=item.querySelector('[name$="-sort_order"]');if(input){input.value=index;input.dispatchEvent(new Event('change',{bubbles:true}));}});});
    });
  };document.addEventListener('DOMContentLoaded',init);document.addEventListener('formset:added',init);
})();
