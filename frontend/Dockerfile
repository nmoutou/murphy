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

# Install ALL dependencies (including devDependencies)
RUN npm ci

# Note: Source code is mounted via docker-compose volumes in dev mode
# Next.js dev server with hot-reload

EXPOSE 3000
ENV NODE_ENV=development

# Default command (overridden by docker-compose)
CMD ["npm", "run", "dev"]

##########################
# Builder Stage
# Builds Next.js application
##########################
FROM node:22 AS builder
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build Next.js app
RUN npm run build

##########################
# Production Stage
# Optimized image with only built app and production dependencies
##########################
FROM node:22-slim AS production
WORKDIR /app

# Install system dependencies (curl for healthchecks)
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy built app from builder
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/package*.json ./

# Install only production dependencies
RUN npm ci --omit=dev

EXPOSE 3000
ENV NODE_ENV=production

CMD ["npm", "start"]
