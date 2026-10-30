# TUH Chatbot AI — UserWeb / AdminWeb (build static แล้วเสิร์ฟด้วย nginx แทน XAMPP)
# ใช้ไฟล์เดียวกันทั้งสองเว็บ: --build-arg APP=UserWeb หรือ APP=AdminWeb (ดู docker-compose.yml)
FROM node:20-alpine AS build
ARG APP
# same-origin = เรียก API ผ่าน origin เดียวกับหน้าเว็บ (https://<host>/api ผ่าน reverse proxy — ดู docker-compose.yml)
# เว้นว่าง = เรียก http://<host ที่เปิดเว็บ>:8000 ตรงๆ แบบเดิม (สมัย XAMPP / dev server)
ARG VITE_API_URL=
# path ที่เว็บนี้อยู่หลัง proxy — AdminWeb อยู่ที่ /admin/
ARG BASE=/
WORKDIR /src
COPY ${APP}/package.json ${APP}/package-lock.json ./
RUN npm ci
COPY ${APP}/ ./
RUN VITE_API_URL=${VITE_API_URL} npm run build -- --base=${BASE}

FROM nginx:1.27-alpine
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /src/dist /usr/share/nginx/html
EXPOSE 80
