##########################
# Développement
# docker-compose.dev.yml ne monte que backend/src : dépendances et contrat vivent dans
# l'image, en changer impose de la reconstruire (`npm run build`).
##########################
FROM node:22 AS development
WORKDIR /app

# curl pour les healthchecks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Tous les manifestes : `npm ci` confronte le lockfile à chacun
COPY package.json package-lock.json ./
COPY backend/package.json backend/
COPY frontend/package.json frontend/
COPY packages/contract/package.json packages/contract/

# Sans scripts : le postinstall racine construirait le contrat avant l'arrivée de ses sources
RUN npm ci -w backend -w @murphy/contract --ignore-scripts

COPY packages/contract/ packages/contract/
RUN npm run build -w @murphy/contract

COPY backend/ backend/
WORKDIR /app/backend

EXPOSE 5000
ENV NODE_ENV=development

# Remplacée par docker-compose
CMD ["npm", "run", "dev"]

##########################
# Build
##########################
FROM development AS builder
RUN npm run build

##########################
# Production : code compilé et dépendances de production seulement
##########################
FROM node:22-slim AS production
WORKDIR /app

# curl pour les healthchecks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY package.json package-lock.json ./
COPY backend/package.json backend/
COPY frontend/package.json frontend/
COPY packages/contract/package.json packages/contract/

RUN npm ci --omit=dev -w backend --ignore-scripts

COPY --from=builder /app/packages/contract/dist packages/contract/dist
COPY --from=builder /app/backend/dist backend/dist
WORKDIR /app/backend

EXPOSE 5000
ENV NODE_ENV=production

USER node
CMD ["node", "dist/server.js"]
