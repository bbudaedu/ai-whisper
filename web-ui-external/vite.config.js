import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
// https://vite.dev/config/
export default defineConfig({
    plugins: [react(), tailwindcss()],
    server: {
        allowedHosts: ['fayi.budaedu.dpdns.org'],
        host: true,
        port: 5173,
        proxy: {
            '/api': {
                target: 'http://localhost:8002',
                changeOrigin: true,
                xfwd: true,
            }
        }
    }
});
