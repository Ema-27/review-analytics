# syntax=docker/dockerfile:1

# --- Fase 1: build della SPA React con Vite ---
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# --- Fase 2: immagine finale, nginx serve i file statici e fa da proxy /api ---
FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

# 127.0.0.1 e non "localhost": in questa immagine Alpine "localhost" risolve
# prima su ::1 (IPv6), mentre nginx ascolta solo su IPv4 -> healthcheck KO.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=5 \
    CMD wget -q -O- http://127.0.0.1:80/ || exit 1
