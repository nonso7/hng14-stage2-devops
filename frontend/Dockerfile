# syntax=docker/dockerfile:1.7

FROM node:20-alpine AS builder
WORKDIR /build
COPY package.json package-lock.json* ./
RUN npm install --omit=dev --no-audit --no-fund

FROM node:20-alpine AS runtime
ENV NODE_ENV=production
RUN apk --no-cache upgrade \
 && rm -rf /usr/local/lib/node_modules/npm \
           /usr/local/bin/npm /usr/local/bin/npx \
 && addgroup -S -g 10001 appuser \
 && adduser  -S -u 10001 -G appuser appuser
WORKDIR /app
COPY --from=builder --chown=appuser:appuser /build/node_modules ./node_modules
COPY --chown=appuser:appuser package.json app.js healthcheck.js ./
COPY --chown=appuser:appuser views ./views
USER appuser
EXPOSE 3000
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
  CMD ["node", "/app/healthcheck.js"]
CMD ["node", "app.js"]
