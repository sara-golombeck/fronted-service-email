# Check if we should build for S3 or traditional Docker
ARG BUILD_TARGET=s3

# S3 Build - just build static files
FROM node:18-alpine AS s3-build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Traditional Docker build
FROM node:18-alpine AS docker-build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Nginx proxy for S3 setup
FROM nginxinc/nginx-unprivileged:alpine AS s3-proxy
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx/proxy.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]

# Traditional nginx with static files
FROM nginxinc/nginx-unprivileged:alpine AS docker-static
WORKDIR /usr/share/nginx/html
COPY --from=docker-build /app/build /usr/share/nginx/html/
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx/default.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]

# Final stage selection
FROM ${BUILD_TARGET}-proxy AS final