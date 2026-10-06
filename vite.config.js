import {defineConfig} from 'vite';
export default defineConfig({
  base:'/static/build/',
  build:{outDir:'static/build',emptyOutDir:true,manifest:true,target:'es2022',minify:'terser',terserOptions:{compress:{passes:3}},
    rollupOptions:{input:{main:'frontend/main.js',styleguide:'frontend/styleguide.js'}}
  }
});
