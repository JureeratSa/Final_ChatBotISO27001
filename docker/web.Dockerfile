# TUH Chatbot AI — UserWeb / AdminWeb (build static แล้วเสิร์ฟด้วย nginx แทน XAMPP)
# ใช้ไฟล์เดียวกันทั้งสองเว็บ: --build-arg APP=UserWeb หรือ APP=AdminWeb (ดู docker-compose.yml)
FROM node:20-alpine AS build
ARG APP
# เว้นว่าง = frontend เรียก http://<host ที่เปิดเว็บ>:8000 เอง (เหมือนตอนรันบน XAMPP)
ARG VITE_API_URL=
WORKDIR /src
COPY ${APP}/package.json ${APP}/package-lock.json ./
RUN npm ci
COPY ${APP}/ ./
RUN VITE_API_URL=${VITE_API_URL} npm run build

FROM nginx:1.27-alpine
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /src/dist /usr/share/nginx/html
EXPOSE 80
