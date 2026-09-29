##########################
# Development Stage
# The build context is the repository root: frontend and the shared contract are npm
# workspaces resolved by the root lockfile. docker-compose.dev.yml mounts frontend/src
# and frontend/public only (hot-reload); dependencies, config and the contract live in
# the image, so changing them means rebuilding it (`npm run serve:build`).
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
RUN npm ci -w frontend -w @murphy/contract --ignore-scripts

COPY packages/contract/ packages/contract/
RUN npm run build -w @murphy/contract

COPY frontend/ frontend/
WORKDIR /app/frontend

EXPOSE 3000
ENV NODE_ENV=development

# Default command (overridden by docker-compose)
CMD ["npm", "run", "dev"]

##########################
# Builder Stage
# Builds Next.js application
##########################
FROM development AS builder
# `next build` expects production: a development NODE_ENV would bundle React's dev build
ENV NODE_ENV=production
# Next inlines NEXT_PUBLIC_* into the client bundle at build time: the image targets
# one backend URL, and changing it means rebuilding (docker-compose.prod.yml passes it)
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build

##########################
# Production Stage
# Optimized image with only built app and production dependencies
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
RUN npm ci --omit=dev -w frontend --ignore-scripts

# Copy built app from builder
COPY --from=builder /app/packages/contract/dist packages/contract/dist
# Owned by `node`: `next start` writes its cache under .next/cache
COPY --from=builder --chown=node:node /app/frontend/.next frontend/.next
COPY --from=builder /app/frontend/public frontend/public
WORKDIR /app/frontend

EXPOSE 3000
ENV NODE_ENV=production

USER node
CMD ["npm", "start"]
