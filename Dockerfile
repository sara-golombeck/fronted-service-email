# Build stage
FROM node:18-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# S3 deployment stage - contains build output
FROM node:18-alpine AS s3-build
WORKDIR /app
COPY --from=build /app/build ./build
CMD ["sh", "-c", "echo 'Build files ready'"]

# Nginx proxy stage
FROM nginxinc/nginx-unprivileged:alpine AS s3-proxy
COPY nginx/proxy.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]

# Traditional nginx with static files
FROM nginxinc/nginx-unprivileged:alpine AS docker-static
COPY --from=build /app/build /usr/share/nginx/html/
COPY nginx/default.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]