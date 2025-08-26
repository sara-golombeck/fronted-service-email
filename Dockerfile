# Build stage
FROM node:18-alpine AS build
WORKDIR /app

# Copy package files first for better caching
COPY package*.json ./
RUN npm ci

# Copy source and build
COPY . .
RUN npm run build

# Production stage
FROM nginxinc/nginx-unprivileged:alpine AS production
WORKDIR /usr/share/nginx/html

# Remove default nginx files (as root first)
USER root
RUN rm -rf ./*
USER nginx

# Copy built app
COPY --from=build /app/build .

# Copy nginx config
COPY nginx/default.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost/health || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]