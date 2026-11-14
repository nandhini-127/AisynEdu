# ==============================================================================
# EduNex AI — Production Frontend Dockerfile
# Multi-stage optimized build: Node.js 20 build stage -> Nginx Alpine runtime
# ==============================================================================

# Stage 1: Build React + TypeScript + Vite Application
FROM node:20-alpine AS builder

WORKDIR /app

# Accept optional build argument for production API URL
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

# Copy package manifests first for efficient Docker layer caching
COPY package.json package-lock.json ./

RUN npm ci

# Copy full application source code
COPY . .

# Compile TypeScript and bundle with Vite
RUN npm run build

# Stage 2: Serve compiled static assets via high-performance Nginx Alpine
FROM nginx:1.25-alpine AS production

# Remove default Nginx welcome site
RUN rm -rf /usr/share/nginx/html/*

# Copy compiled SPA bundle from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy production Nginx server configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

# Health check probing Nginx health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:80/health || exit 1

CMD ["nginx", "-g", "daemon off;"]

