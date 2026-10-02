import {Scene,PerspectiveCamera,WebGLRenderer,Color,SRGBColorSpace,EquirectangularReflectionMapping,ACESFilmicToneMapping,PMREMGenerator,Mesh,MeshBasicMaterial,MeshStandardMaterial,PlaneGeometry,Group,Box3,Vector3,AmbientLight,DirectionalLight,SpotLight,CanvasTexture,DoubleSide,AdditiveBlending,Sprite,SpriteMaterial} from 'three';
import {GLTFLoader} from 'three/examples/jsm/loaders/GLTFLoader.js';
import {OrbitControls} from 'three/examples/jsm/controls/OrbitControls.js';
import {gsap} from 'gsap';
import {ScrollTrigger} from 'gsap/ScrollTrigger';
gsap.registerPlugin(ScrollTrigger);

export async function createHero(hero){
  const host=hero.querySelector('.hero-canvas'),poster=hero.querySelector('.hero-poster');
  const names=JSON.parse(document.querySelector('#hero-names')?.textContent||'{}');
  const renderer=new WebGLRenderer({antialias:true,alpha:false,powerPreference:'low-power'});
  renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.outputColorSpace=SRGBColorSpace;renderer.toneMapping=ACESFilmicToneMapping;renderer.toneMappingExposure=1.25;
  renderer.setClearColor(0x080a0c);host.append(renderer.domElement);
  const scene=new Scene(),camera=new PerspectiveCamera(35,1,.1,80);camera.position.set(7.1,2.2,9.4);
  const controls=new OrbitControls(camera,renderer.domElement);controls.enableZoom=false;controls.enablePan=false;controls.enableDamping=true;controls.dampingFactor=.08;controls.rotateSpeed=.45;
  controls.minPolarAngle=Math.PI*.36;controls.maxPolarAngle=Math.PI*.46;controls.target.set(0,.65,0);
  // Native vertical touch gestures scroll. OrbitControls handles horizontal gestures only.
  renderer.domElement.style.touchAction='pan-y';
  let touchStart;
  const touchCapture=event=>{
    if(event.pointerType!=='touch')return;
    if(event.type==='pointerdown')touchStart={x:event.clientX,y:event.clientY};
    if(event.type==='pointermove'&&touchStart&&Math.abs(event.clientY-touchStart.y)>Math.abs(event.clientX-touchStart.x))event.stopImmediatePropagation();
  };
  renderer.domElement.addEventListener('pointerdown',touchCapture,true);renderer.domElement.addEventListener('pointermove',touchCapture,true);
  // A generated studio panorama supplies real image-based lighting without an HDR download.
  const studio=document.createElement('canvas');studio.width=512;studio.height=256;const studioCtx=studio.getContext('2d');
  studioCtx.fillStyle='#10151b';studioCtx.fillRect(0,0,512,256);
  studioCtx.filter='blur(8px)';studioCtx.fillStyle='#dfeeff';studioCtx.fillRect(72,45,28,155);studioCtx.fillRect(355,38,70,135);studioCtx.fillStyle='#ffffff';studioCtx.fillRect(130,12,220,20);
  const studioTexture=new CanvasTexture(studio);studioTexture.mapping=EquirectangularReflectionMapping;studioTexture.colorSpace=SRGBColorSpace;
  const pmrem=new PMREMGenerator(renderer),env=pmrem.fromEquirectangular(studioTexture);scene.environment=env.texture;studioTexture.dispose();pmrem.dispose();
  scene.add(new AmbientLight(0xffffff,.25));
  const rim=new DirectionalLight(0xe6efff,2.5);rim.position.set(-3,5,-4);scene.add(rim);
  const key=new DirectionalLight(0xffffff,1.8);key.position.set(6,4,3);scene.add(key);
  const floor=new Mesh(new PlaneGeometry(100,100),new MeshBasicMaterial({color:0x080a0c,transparent:true,opacity:.92,depthWrite:false}));floor.rotation.x=-Math.PI/2;floor.position.y=-.03;floor.renderOrder=1;scene.add(floor);
  const textureCanvas=document.createElement('canvas');textureCanvas.width=textureCanvas.height=128;
  const ctx=textureCanvas.getContext('2d'),gradient=ctx.createRadialGradient(64,64,2,64,64,64);gradient.addColorStop(0,'rgba(0,0,0,.8)');gradient.addColorStop(.45,'rgba(0,0,0,.6)');gradient.addColorStop(1,'rgba(0,0,0,0)');ctx.fillStyle=gradient;ctx.fillRect(0,0,128,128);
  const shadowTexture=new CanvasTexture(textureCanvas);const shadow=new Mesh(new PlaneGeometry(5.8,3.2),new MeshBasicMaterial({map:shadowTexture,transparent:true,depthWrite:false}));shadow.rotation.x=-Math.PI/2;shadow.position.y=.002;scene.add(shadow);
  const loader=new GLTFLoader();
  let draco;
  // Optional compressed customer models: decoder code loads only when requested.
  loader.setDRACOLoader({preload(){},decodeDracoFile(...args){
    import('three/examples/jsm/loaders/DRACOLoader.js').then(({DRACOLoader})=>{draco ||=new DRACOLoader().setDecoderPath('/static/vendor/three/draco/');draco.decodeDracoFile(...args);});
  }});
  const meshopt=()=>import('three/examples/jsm/libs/meshopt_decoder.module.js');
  loader.setMeshoptDecoder({supported:true,get ready(){return meshopt().then(m=>m.MeshoptDecoder.ready);},decodeGltfBufferAsync:async(...args)=>{const {MeshoptDecoder}=await meshopt();await MeshoptDecoder.ready;return MeshoptDecoder.decodeGltfBufferAsync(...args);}});
  let gltf;
  const modelPath=hero.dataset.model==='/static/models/hero.glb'?'/static/models/hero-compressed.glb':hero.dataset.model;
  try{gltf=await loader.loadAsync(modelPath);}catch(error){controls.dispose();renderer.dispose();renderer.domElement.remove();env.dispose();shadowTexture.dispose();draco?.dispose();throw error;}
  const pivot=new Group(),model=gltf.scene;const bounds=new Box3().setFromObject(model),size=bounds.getSize(new Vector3()),center=bounds.getCenter(new Vector3());
  const scale=4.8/Math.max(size.x,size.z);model.scale.setScalar(scale);model.position.set(-center.x*scale,-bounds.min.y*scale,-center.z*scale);pivot.add(model);scene.add(pivot);
  // Cheap mirrored meshes rather than a second rendering pass.
  const mirror=model.clone(true);mirror.scale.y=-Math.abs(mirror.scale.y);mirror.position.y=-model.position.y-.035;
  mirror.traverse(node=>{if(node.isMesh){const fade=material=>{const copy=material.clone();copy.transparent=true;copy.opacity=.075;copy.depthWrite=false;copy.roughness=1;return copy;};node.material=Array.isArray(node.material)?node.material.map(fade):fade(node.material);}});pivot.add(mirror);
  const front=[],rear=[],lights=[],glows=[];
  const glowCanvas=document.createElement('canvas');glowCanvas.width=glowCanvas.height=64;const glowCtx=glowCanvas.getContext('2d'),radial=glowCtx.createRadialGradient(32,32,0,32,32,32);radial.addColorStop(0,'rgba(255,255,255,.8)');radial.addColorStop(.12,'rgba(225,240,255,.25)');radial.addColorStop(1,'rgba(255,255,255,0)');glowCtx.fillStyle=radial;glowCtx.fillRect(0,0,64,64);const glowTexture=new CanvasTexture(glowCanvas);
  model.traverse(node=>{if(node.isMesh){const materials=Array.isArray(node.material)?node.material:[node.material];materials.forEach(material=>{if(names.headlightMaterials?.includes(material.name))front.push(material);if(names.taillightMaterials?.includes(material.name))rear.push(material);});}});
  model.updateMatrixWorld(true);
  (names.headlightNodes||[]).forEach(name=>{const part=model.getObjectByName(name);if(!part)return;
    // Named meshes may contain baked vertex positions or quantization transforms.
    const position=pivot.worldToLocal(new Box3().setFromObject(part).getCenter(new Vector3()));
    const spot=new SpotLight(0xe3f2ff,0,10,.4,.65,1);spot.position.copy(position);pivot.add(spot);spot.target.position.set(position.x,.01,position.z+7);pivot.add(spot.target);lights.push(spot);
    const sprite=new Sprite(new SpriteMaterial({map:glowTexture,color:0xe6f3ff,transparent:true,opacity:0,blending:AdditiveBlending,depthWrite:false}));sprite.position.copy(position);sprite.scale.set(.75,.75,1);pivot.add(sprite);glows.push(sprite);
    // Floor beam is a soft additive quad, no bloom framebuffers or ray tracing.
    const beam=new Mesh(new PlaneGeometry(1.4,5),new MeshBasicMaterial({color:0xc9e7ff,map:glowTexture,transparent:true,opacity:0,blending:AdditiveBlending,depthWrite:false,side:DoubleSide}));beam.rotation.x=-Math.PI/2;beam.position.set(position.x,.014,position.z+2.4);pivot.add(beam);glows.push(beam);
  });
  front.forEach(m=>m.emissive.set(0xddeeff));rear.forEach(m=>m.emissive.set(0xff1515));
  const state={progress:0,dragging:false},originalCamera=new Vector3(7.1,2.2,9.4),originalTarget=new Vector3(-.15,.65,0);let toggle=null,visible=true,disposed=false,raf=null;
  const copy=hero.querySelector('.hero-copy'),end=hero.querySelector('.hero-end'),button=hero.querySelector('[data-light-toggle]');
  const apply=()=>{
    const progress=state.progress;pivot.rotation.y=.18-progress*Math.PI*2/3;pivot.position.x=1.6-progress*3.0;
    shadow.position.x=pivot.position.x;shadow.rotation.z=-pivot.rotation.y;
    if(!state.dragging){camera.position.lerp(originalCamera,.04);controls.target.lerp(originalTarget,.04);}
    const power=toggle===null?Math.min(1,Math.max(0,(progress-.25)/.75)):toggle;
    front.forEach(m=>m.emissiveIntensity=power*3);rear.forEach(m=>m.emissiveIntensity=power*2);lights.forEach(light=>light.intensity=power*9);glows.forEach(glow=>glow.material.opacity=power*(glow.isSprite?.6:.18));
    const endOpacity=Math.max(0,(progress-.55)/.35),copyOpacity=1-Math.min(1,progress/.55);copy.style.opacity=copyOpacity;copy.style.visibility=copyOpacity>0?'visible':'hidden';end.style.opacity=endOpacity;end.style.visibility=endOpacity>0?'visible':'hidden';end.style.pointerEvents=endOpacity>.4?'auto':'none';
    button.setAttribute('aria-pressed',String(power>.5));
  };
  const trigger=ScrollTrigger.create({trigger:hero,start:'top top',end:()=>`+=${innerHeight*.75}`,pin:true,scrub:.6,invalidateOnRefresh:true,onUpdate:self=>{gsap.to(state,{progress:self.progress,duration:.4,overwrite:true});}});
  const onToggle=()=>{toggle=button.getAttribute('aria-pressed')==='true'?0:1;};button.hidden=false;button.addEventListener('click',onToggle);hero.querySelector('.hero-hint').hidden=false;
  controls.addEventListener('start',()=>state.dragging=true);controls.addEventListener('end',()=>state.dragging=false);
  const resize=()=>{renderer.setSize(host.clientWidth,host.clientHeight);camera.aspect=host.clientWidth/host.clientHeight;camera.updateProjectionMatrix();};resize();window.addEventListener('resize',resize,{passive:true});
  let last=0;const render=now=>{raf=null;if(disposed||!visible||document.hidden)return;raf=requestAnimationFrame(render);if(now-last<1000/45)return;last=now;apply();controls.update();renderer.render(scene,camera);};
  const activity=()=>{if(disposed)return;if(visible&&!document.hidden){if(raf===null)raf=requestAnimationFrame(render);}else{cancelAnimationFrame(raf);raf=null;}};
  const observer=new IntersectionObserver(entries=>{visible=entries[0].isIntersecting;activity();});observer.observe(hero);document.addEventListener('visibilitychange',activity);activity();
  hero.dataset.state='ready';poster.style.opacity='0';
  const dispose=()=>{if(disposed)return;disposed=true;cancelAnimationFrame(raf);observer.disconnect();document.removeEventListener('visibilitychange',activity);trigger.kill();gsap.killTweensOf(state);controls.dispose();button.removeEventListener('click',onToggle);window.removeEventListener('resize',resize);renderer.domElement.removeEventListener('pointerdown',touchCapture,true);renderer.domElement.removeEventListener('pointermove',touchCapture,true);const materials=new Set(),geometries=new Set(),textures=new Set();scene.traverse(node=>{if(node.geometry)geometries.add(node.geometry);if(node.material)(Array.isArray(node.material)?node.material:[node.material]).forEach(m=>materials.add(m));});materials.forEach(m=>{Object.values(m).forEach(v=>{if(v?.isTexture)textures.add(v);});m.dispose();});textures.forEach(t=>t.dispose());geometries.forEach(g=>g.dispose());env.dispose();draco?.dispose();renderer.dispose();renderer.domElement.remove();};
  window.addEventListener('pagehide',dispose,{once:true});return {scene,renderer,camera,dispose};
}
