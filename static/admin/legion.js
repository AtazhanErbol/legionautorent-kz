(() => {
  const init = () => {
    const nav = document.querySelector('.cms-nav');
    if (nav) {
      nav.classList.add('cms-nav-collapsible');
      const toggle = document.createElement('button');
      toggle.type = 'button'; toggle.className = 'cms-menu-toggle'; toggle.textContent = 'Разделы';
      toggle.setAttribute('aria-expanded', 'false');
      toggle.addEventListener('click', () => {toggle.setAttribute('aria-expanded', String(nav.classList.toggle('is-open')));});
      nav.prepend(toggle);
      nav.querySelector('[data-nav-search]')?.addEventListener('input', event => {
        const query = event.target.value.trim().toLocaleLowerCase();
        nav.querySelectorAll('.cms-nav-group').forEach(group => {
          const links = [...group.querySelectorAll('a')];
          links.forEach(link => { link.hidden = !link.textContent.toLocaleLowerCase().includes(query); });
          group.hidden = links.every(link => link.hidden);
        });
      });
    }
    const form = document.querySelector('#content-main form[method="post"]');
    if (!form) return;
    const fieldsets = [...form.querySelectorAll(':scope > div > fieldset.module, :scope > div > .inline-group')];
    if (fieldsets.length > 2) {
      const index = document.createElement('nav');index.className = 'cms-form-nav';index.setAttribute('aria-label', 'Разделы формы');
      fieldsets.forEach((fieldset, i) => {
        const title = fieldset.querySelector('h2')?.textContent.trim(); if (!title) return;
        fieldset.id ||= `cms-section-${i}`;
        const link = document.createElement('a');link.href = `#${fieldset.id}`;link.textContent = title;
        link.addEventListener('click', () => {const details = fieldset.querySelector('details');if (details) details.open = true;});index.append(link);
      });
      form.prepend(index);
    }
    form.querySelectorAll('textarea[data-rich-editor]').forEach(area => {
      const wrap = document.createElement('div');wrap.className = 'cms-editor-wrap';area.before(wrap);wrap.append(area);
      const toolbar = document.createElement('div');toolbar.className = 'cms-editor-toolbar';toolbar.setAttribute('aria-label', 'Форматирование текста');
      [['Абзац','p'],['Подзаголовок','h2'],['Жирный','strong'],['Курсив','em'],['Список','ul']].forEach(([label, tag]) => {
        const button = document.createElement('button');button.type = 'button';button.textContent = label;
        button.addEventListener('click', () => {
          const start = area.selectionStart, end = area.selectionEnd;
          const selection = area.value.slice(start, end) || 'Текст';
          const value = tag === 'ul' ? `<ul>\n<li>${selection}</li>\n</ul>` : `<${tag}>${selection}</${tag}>`;
          area.setRangeText(value, start, end, 'select');area.dispatchEvent(new Event('input', {bubbles:true}));area.focus();
        });toolbar.append(button);
      });wrap.prepend(toolbar);
    });
    form.addEventListener('invalid', event => {
      const details = event.target.closest('details');if(details) details.open = true;
    }, true);
  };
  document.addEventListener('DOMContentLoaded', init);
})();
