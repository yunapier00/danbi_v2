import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.ico', 'apple-touch-icon.png', 'masked-icon.svg'],
      devOptions: {
        enabled: true // 로컬 개발 환경(npm run dev)에서도 PWA 활성화
      },
      manifest: {
        name: '단비 - 단국대 AI 어시스턴트',
        short_name: '단비',
        description: '단국대학교 RAG 기반 학사 정보 AI 챗봇',
        theme_color: '#ffffff',
        icons: [
          {
            src: 'pwa-192x192.png',
            sizes: '192x192',
            type: 'image/png'
          },
          {
            src: 'pwa-512x512.png',
            sizes: '512x512',
            type: 'image/png'
          }
        ]
      }
    })
  ]
})