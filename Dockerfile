# Multi-stage build for React app
FROM node:18-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production --silent

# Copy source code
COPY . .

# Build the app
RUN npm run build

# Verify build output
RUN ls -la build/ && test -d build/static

# Final stage - minimal image with build output
FROM alpine:latest AS artifacts
COPY --from=builder /app/build /build
CMD ["sh"]