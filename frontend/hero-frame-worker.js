// Decode off the page thread; only the finished bitmap crosses the boundary.
self.onmessage=async ({data:{id,blob}})=>{
  try{
    const image=await createImageBitmap(blob);
    self.postMessage({id,image},[image]);
  }catch{self.postMessage({id,error:true});}
};
self.postMessage({ready:typeof createImageBitmap==='function'});
