const fs=require('fs');
const zlib=require('zlib');
const manifest=JSON.parse(fs.readFileSync('static/build/.vite/manifest.json'));
let total=0;
const files=new Set();
for(const entry of Object.values(manifest)){
  if(['three','hero','meshopt_decoder.module'].includes(entry.name))throw new Error('Retired 3D asset in active manifest');
  if(entry.file.endsWith('.js')&&entry.name!=='styleguide')files.add(entry.file);
}
for(const file of [...files])for(const match of fs.readFileSync('static/build/'+file,'utf8').matchAll(/\/static\/build\/(assets\/[\w.-]+\.js)/g))files.add(match[1]);
for(const file of files)total+=zlib.gzipSync(fs.readFileSync('static/build/'+file)).length;
console.log(JSON.stringify({allRuntimeJsGzipBytes:total,budget:15000}));
if(total>15000)process.exit(1);
