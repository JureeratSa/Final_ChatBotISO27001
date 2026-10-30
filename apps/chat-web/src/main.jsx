/**
 * TUH Chatbot AI — UserWeb Entry Point
 * จุดเริ่มต้นการทำงานของแอปพลิเคชันฝั่งผู้ใช้งาน:
 * 1. Mount คอมโพเนนต์หลัก <App /> เข้าสู่ DOM element '#root'
 * 2. นำเข้า index.css (Tailwind/Custom styling) และ FontAwesome ไอคอน
 */
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'
import '@fortawesome/fontawesome-free/css/all.min.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
