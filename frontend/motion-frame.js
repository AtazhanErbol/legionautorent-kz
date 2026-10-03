// Secondary effects share one frame queue, which is empty while at rest.
const jobs=new Map();let frame=0,sequence=0;
export function queueFrame(callback){
  const id=++sequence;jobs.set(id,callback);
  if(!frame)frame=requestAnimationFrame(now=>{
    frame=0;const pending=[...jobs.values()];jobs.clear();
    for(const callback of pending)callback(now);
  });
  return id;
}
export function cancelFrame(id){jobs.delete(id);if(!jobs.size){cancelAnimationFrame(frame);frame=0;}}
