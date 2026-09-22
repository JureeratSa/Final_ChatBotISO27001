import { defineConfig } from 'vite'

// แยก config ออกจาก vite.config.js (dev server) เพราะ test runner ไม่ต้องการ proxy/host settings
// เทสไฟล์อยู่ที่ web_testing/unit-frontend/ (นอก UserWeb/) ให้สอดคล้องกับโครงสร้าง web_testing/
// ที่ใช้เก็บ Unit Test ทั้งฝั่ง Backend (pytest) และ Frontend (Vitest) ไว้ที่เดียวกัน — server.fs.allow
// ต้องเปิดเพราะ Vite ปิดกั้นการ serve ไฟล์นอก root โดย default
export default defineConfig({
  server: {
    fs: { allow: ['..'] },
  },
  test: {
    environment: 'jsdom',
    include: ['../web_testing/unit-frontend/**/*.test.js'],
  },
})
