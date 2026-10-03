import {defineConfig} from 'vite';
export default defineConfig({
  base:'/static/build/',
  build:{outDir:'static/build',emptyOutDir:false,manifest:true,target:'es2022',minify:'terser',terserOptions:{compress:{passes:3}},
    rollupOptions:{input:{main:'frontend/main.js',styleguide:'frontend/styleguide.js'},output:{manualChunks(id){
      if(id.includes('/node_modules/gsap/'))return 'motion';
      if(id.includes('/node_modules/three/src/')||id.includes('/node_modules/three/build/'))return 'three';
    }}}
  }
});
