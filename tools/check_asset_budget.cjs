const fs=require('fs');
const zlib=require('zlib');
const manifest=JSON.parse(fs.readFileSync('static/build/.vite/manifest.json'));
let total=0;
for(const entry of Object.values(manifest)){
  if(['three','hero','meshopt_decoder.module'].includes(entry.name))throw new Error('Retired 3D asset in active manifest');
  if(entry.file.endsWith('.js')&&entry.name!=='styleguide')total+=zlib.gzipSync(fs.readFileSync('static/build/'+entry.file)).length;
}
console.log(JSON.stringify({allRuntimeJsGzipBytes:total,budget:15000}));
if(total>15000)process.exit(1);
