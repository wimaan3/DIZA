import {defineConfig} from 'vite';
export default defineConfig({
  base:'/city-3d/',
  server:{port:18783,strictPort:true,proxy:{'/api':'http://127.0.0.1:8000'}},
  build:{rollupOptions:{output:{manualChunks:{maplibre:['maplibre-gl']}}}}
});
