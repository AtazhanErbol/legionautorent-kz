import * as THREE from '../vendor/three/three.module.js';
import { GLTFLoader } from '../vendor/three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from '../vendor/three/addons/loaders/DRACOLoader.js';

export async function mount(container) {
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(32, container.clientWidth / container.clientHeight, .1, 100);
  camera.position.set(5, 2.2, 6);
  const renderer = new THREE.WebGLRenderer({antialias: true, alpha: true, powerPreference: 'low-power'});
  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5)); renderer.setSize(container.clientWidth, container.clientHeight);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  scene.add(new THREE.HemisphereLight(0xffffff, 0x444a55, 2.5));
  for (const [x, y, z, intensity] of [[2, 5, 4, 4], [-4, 3, -2, 3]]) {const light = new THREE.DirectionalLight(0xffffff, intensity); light.position.set(x,y,z); scene.add(light);}
  const draco = new DRACOLoader(); draco.setDecoderPath('/static/vendor/three/draco/');
  const loader = new GLTFLoader(); loader.setDRACOLoader(draco);
  let model;
  try {model = (await loader.loadAsync(container.dataset.model)).scene;} catch (error) {renderer.dispose(); draco.dispose(); throw error;}
  const box = new THREE.Box3().setFromObject(model); const size = box.getSize(new THREE.Vector3()); const center = box.getCenter(new THREE.Vector3());
  const extent = Math.max(size.x, size.y, size.z);
  if (!Number.isFinite(extent) || extent <= 0) {renderer.dispose();draco.dispose();throw new Error('Empty hero model');}
  // Center the asset before scaling/rotating its parent, including off-origin GLBs.
  model.position.sub(center);
  const vehicle = new THREE.Group();vehicle.add(model);vehicle.scale.setScalar(4.2 / extent);vehicle.rotation.y = -.4;
  scene.add(vehicle); camera.lookAt(0,0,0);
  renderer.domElement.setAttribute('aria-hidden', 'true'); container.appendChild(renderer.domElement);
  const fallback = container.querySelector('img'); if (fallback) fallback.style.opacity = '0';
  let visible = true; let frame = 0; let target = -.4;
  const observer = new IntersectionObserver(entries => {visible = entries[0].isIntersecting;}); observer.observe(container);
  const resize = new ResizeObserver(() => {camera.aspect = container.clientWidth/container.clientHeight;camera.updateProjectionMatrix();renderer.setSize(container.clientWidth,container.clientHeight);}); resize.observe(container);
  container.addEventListener('pointermove', e => {const rect = container.getBoundingClientRect(); target = -.4 + ((e.clientX-rect.left)/rect.width-.5)*.18;}, {passive: true});
  const render = () => {frame = requestAnimationFrame(render);if (!visible || document.hidden) return;vehicle.rotation.y += (target-vehicle.rotation.y)*.06;renderer.render(scene,camera);}; render();
  renderer.domElement.addEventListener('webglcontextlost', e => {e.preventDefault();cancelAnimationFrame(frame);observer.disconnect();resize.disconnect();renderer.dispose();draco.dispose();renderer.domElement.remove();if(fallback)fallback.style.opacity='1';});
  window.addEventListener('pagehide', () => {cancelAnimationFrame(frame);observer.disconnect();resize.disconnect();renderer.dispose();draco.dispose();}, {once:true});
}
