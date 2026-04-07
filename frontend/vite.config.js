import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

const vendorGroups = {
  vue: ['vue', 'vue-router', 'pinia'],
  elementPlus: ['element-plus', '@element-plus/icons-vue'],
  axios: ['axios'],
  markdown: ['marked']
}

function resolveVendorChunk(id) {
  if (!id.includes('node_modules')) {
    return null
  }

  for (const [chunkName, deps] of Object.entries(vendorGroups)) {
    if (deps.some(dep => id.includes(`/node_modules/${dep}/`) || id.includes(`\\node_modules\\${dep}\\`))) {
      return chunkName
    }
  }

  return 'vendor'
}

export default defineConfig({
  plugins: [
    vue(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  },
  build: {
    chunkSizeWarningLimit: 800,
    rollupOptions: {
      output: {
        manualChunks(id) {
          const vendorChunk = resolveVendorChunk(id)
          if (vendorChunk) {
            return vendorChunk
          }

          if (id.includes('/src/views/') || id.includes('\\src\\views\\')) {
            const normalizedId = id.replace(/\\/g, '/')
            const fileName = normalizedId.split('/').pop()?.replace(/\.vue$/, '')
            return fileName ? `view-${fileName}` : null
          }

          return null
        }
      }
    }
  }
})
