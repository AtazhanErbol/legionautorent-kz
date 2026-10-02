const fs=require('fs');
const manifest=JSON.parse(fs.readFileSync('static/build/.vite/manifest.json'));
let total=0;
for(const entry of Object.values(manifest)){
  if(['three','hero','meshopt_decoder.module'].includes(entry.name))total+=fs.statSync('static/build/'+entry.file+'.gz').size;
}
console.log(JSON.stringify({threeSceneDecoderGzipBytes:total,budget:150000}));
if(total>=150000)process.exit(1);
