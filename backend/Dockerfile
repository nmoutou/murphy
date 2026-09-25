##########################
# Development Stage
# The build context is the repository root: backend and the shared contract are npm
# workspaces resolved by the root lockfile. docker-compose.dev.yml mounts backend/src
# only (hot-reload); dependencies and the contract live in the image, so changing
# either means rebuilding it (`npm run serve:build`).
##########################
FROM node:22 AS development
WORKDIR /app

# Install system dependencies (curl for healthchecks)
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Every workspace manifest: `npm ci` checks the lockfile against all of them
COPY package.json package-lock.json ./
COPY backend/package.json backend/
COPY frontend/package.json frontend/
COPY packages/contract/package.json packages/contract/

# Scripts are skipped: the root postinstall would build the contract before its sources are here
RUN npm ci -w backend -w @murphy/contract --ignore-scripts

COPY packages/contract/ packages/contract/
RUN npm run build -w @murphy/contract

COPY backend/ backend/
WORKDIR /app/backend

# Expose server port
EXPOSE 5000
ENV NODE_ENV=development

# Default command (overridden by docker-compose)
CMD ["npm", "run", "dev"]

##########################
# Builder Stage
# Compiles TypeScript to JavaScript
##########################
FROM development AS builder
RUN npm run build

##########################
# Production Stage
# Optimized image with only compiled code and production dependencies
##########################
FROM node:22-slim AS production
WORKDIR /app

# Install system dependencies (curl for healthchecks)
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY package.json package-lock.json ./
COPY backend/package.json backend/
COPY frontend/package.json frontend/
COPY packages/contract/package.json packages/contract/

# Install only production dependencies
RUN npm ci --omit=dev -w backend --ignore-scripts

# Copy compiled code from builder
COPY --from=builder /app/packages/contract/dist packages/contract/dist
COPY --from=builder /app/backend/dist backend/dist
WORKDIR /app/backend

# Expose server port
EXPOSE 5000
ENV NODE_ENV=production

# Start server
CMD ["node", "dist/server.js"]
