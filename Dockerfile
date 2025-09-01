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
# Copy built app
COPY --from=build /app/build /usr/share/nginx/html/


# Copy nginx config
COPY nginx/default.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 8080

# Start nginx
CMD ["nginx", "-g", "daemon off;"]