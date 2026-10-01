##########################
# Développement
# docker-compose.dev.yml ne monte que frontend/src et frontend/public : dépendances,
# config et contrat vivent dans l'image, en changer impose de la reconstruire
# (`npm run build`).
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
RUN npm ci -w frontend -w @murphy/contract --ignore-scripts

COPY packages/contract/ packages/contract/
RUN npm run build -w @murphy/contract

COPY frontend/ frontend/
WORKDIR /app/frontend

EXPOSE 3000
ENV NODE_ENV=development

# Remplacée par docker-compose
CMD ["npm", "run", "dev"]

##########################
# Build
##########################
FROM development AS builder
# Un NODE_ENV de développement embarquerait le build de dev de React
ENV NODE_ENV=production
# Inliné au build : l'image vise une seule URL de backend, en changer impose de reconstruire
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build

##########################
# Production : app construite et dépendances de production seulement
##########################
FROM node:22-slim AS production
WORKDIR /app

# curl pour les healthchecks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY package.json package-lock.json ./
COPY backend/package.json backend/
COPY frontend/package.json frontend/
COPY packages/contract/package.json packages/contract/

RUN npm ci --omit=dev -w frontend --ignore-scripts

COPY --from=builder /app/packages/contract/dist packages/contract/dist
# Appartient à `node` : `next start` écrit son cache sous .next/cache
COPY --from=builder --chown=node:node /app/frontend/.next frontend/.next
COPY --from=builder /app/frontend/public frontend/public
WORKDIR /app/frontend

EXPOSE 3000
ENV NODE_ENV=production

USER node
CMD ["npm", "start"]
