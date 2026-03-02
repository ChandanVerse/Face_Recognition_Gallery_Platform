import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import fs from 'fs'

// Helper function to check if SSL certificates exist
const getHttpsConfig = () => {
  const keyPath = path.resolve(__dirname, '../certs/key.pem')
  const certPath = path.resolve(__dirname, '../certs/cert.pem')

  if (fs.existsSync(keyPath) && fs.existsSync(certPath)) {
    return {
      key: fs.readFileSync(keyPath),
      cert: fs.readFileSync(certPath),
    }
  }

  return undefined
}

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 7003,
    host: '0.0.0.0',
    https: getHttpsConfig(),
    allowedHosts: ['recommendations.vosmos.events', '.vosmos.events'],
    proxy: {
      '/api': {
        target: 'https://recommendations.vosmos.events:7008',
        changeOrigin: true,
        secure: false, // Allow self-signed certificates in development
      },
    },
  },
})