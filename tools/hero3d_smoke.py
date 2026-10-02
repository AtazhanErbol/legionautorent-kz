"""Exercise the loader with a self-created off-origin triangle, not a commercial hero asset."""
import base64
import json
import os
import struct
from pathlib import Path
from playwright.sync_api import sync_playwright

root=Path(__file__).resolve().parents[1]
positions=[98.,49.,0.,102.,49.,0.,100.,52.,0.]
binary=struct.pack('<9f',*positions)
document={'asset':{'version':'2.0'},'scene':0,'scenes':[{'nodes':[0]}],
          'nodes':[{'mesh':0}], 'meshes':[{'primitives':[{'attributes':{'POSITION':0},'material':0}]}],
          'materials':[{'doubleSided':True,'pbrMetallicRoughness':{'baseColorFactor':[1,.1,.1,1],'metallicFactor':0,'roughnessFactor':.8}}],
          'buffers':[{'byteLength':len(binary)}], 'bufferViews':[{'buffer':0,'byteLength':len(binary),'target':34962}],
          'accessors':[{'bufferView':0,'componentType':5126,'count':3,'type':'VEC3','min':[98,49,0],'max':[102,52,0]}]}
body=json.dumps(document,separators=(',',':')).encode()
body+=b' '*((-len(body))%4)
glb=struct.pack('<III',0x46546c67,2,12+8+len(body)+8+len(binary))+struct.pack('<II',len(body),0x4e4f534a)+body+struct.pack('<II',len(binary),0x004e4942)+binary
model='data:model/gltf-binary;base64,'+base64.b64encode(glb).decode()
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page(viewport={'width':1440,'height':1000})
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(os.getenv('PREVIEW_URL','http://127.0.0.1:8002')+'/')
    result=page.evaluate('''async model => {
      const map=document.createElement('script');map.type='importmap';map.textContent=JSON.stringify({imports:{three:'/static/vendor/three/three.module.js'}});document.head.append(map);
      const container=document.createElement('div');container.style='width:640px;height:360px;position:fixed;top:100px;left:100px';container.dataset.model=model;
      const fallback=document.createElement('img');container.append(fallback);document.body.append(container);
      const module=await import('/static/js/hero3d.js');await module.mount(container);
      const canvas=container.querySelector('canvas');
      const painted=await new Promise(resolve=>requestAnimationFrame(()=>{
        const snapshot=document.createElement('canvas');snapshot.width=canvas.width;snapshot.height=canvas.height;
        const ctx=snapshot.getContext('2d');ctx.drawImage(canvas,0,0);
        const pixels=ctx.getImageData(0,0,snapshot.width,snapshot.height).data;
        let count=0;for(let i=3;i<pixels.length;i+=4)if(pixels[i]>0)count++;
        resolve(count);
      }));
      return {canvas:!!canvas,painted_pixels:painted,photo_hidden:fallback.style.opacity==='0'};
    }''',model)
    browser.close()
report={'off_origin_model':result,'errors':errors,'asset':'Self-created QA triangle; no production GLB activated.'}
out=root/'output/playwright/hero3d_report.json';out.write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report))
if errors or not result['canvas'] or result['painted_pixels']==0 or not result['photo_hidden']:raise SystemExit(1)
