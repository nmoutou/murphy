##########################
# Development Stage
# Used for local development with hot-reload and source mounting
##########################
FROM node:22 AS development
WORKDIR /app

# Install system dependencies (curl for healthchecks)
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy package files
COPY package*.json ./

# Install ALL dependencies (including devDependencies for TypeScript, ts-node, etc.)
RUN npm ci

# Note: Source code is mounted via docker-compose volumes in dev mode
# No compilation needed - ts-node runs TypeScript directly

# Expose server port
EXPOSE 5000
ENV NODE_ENV=development

# Default command (overridden by docker-compose)
CMD ["npm", "run", "dev"]

##########################
# Builder Stage
# Compiles TypeScript to JavaScript
##########################
FROM node:22 AS builder
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install all dependencies for building
RUN npm ci --production=false

# Copy source code
COPY . .

# Compile TypeScript
RUN npm run build

##########################
# Production Stage
# Optimized image with only compiled code and production dependencies
##########################
FROM node:22-slim AS production
WORKDIR /app

# Install system dependencies (curl for healthchecks)
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy package files
COPY package*.json ./

# Install only production dependencies
RUN npm ci --omit=dev

# Copy compiled code from builder
COPY --from=builder /app/dist ./dist

# Expose server port
EXPOSE 5000
ENV NODE_ENV=production

# Start server
CMD ["node", "dist/server.js"]
