import './night-garage.css';
import './styleguide.css';
import {initGarageUI} from './night-garage.js';
initGarageUI();

document.querySelector('.sg-form')?.addEventListener('submit',event=>event.preventDefault());
document.querySelectorAll('.sg-action-grid .category-chip').forEach(button=>button.addEventListener('click',()=>{document.querySelectorAll('.sg-action-grid .category-chip').forEach(other=>{const active=other===button;other.classList.toggle('is-active',active);other.setAttribute('aria-pressed',String(active));});}));
