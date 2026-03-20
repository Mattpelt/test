# ─── Stage 1 : build React ───────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .
RUN npm run build

# ─── Stage 2 : nginx ─────────────────────────────────────────────────────────
FROM nginx:alpine

# Fichiers statiques React compilés
COPY --from=builder /app/dist /usr/share/nginx/html

# Config nginx (proxy /api → backend + X-Accel-Redirect)
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
