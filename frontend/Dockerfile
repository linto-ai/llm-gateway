# Stage 1: Dependencies
FROM node:20-alpine AS deps
WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm ci

# Stage 2: Builder
FROM node:20-alpine AS builder
WORKDIR /app

# Copy dependencies from deps stage
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Disable telemetry during build
ENV NEXT_TELEMETRY_DISABLED=1

# Build with /llm-admin basePath (hardcoded for K3S/production deployments)
# This image is meant for deployment behind a reverse proxy at /llm-admin
# For local development without basePath, use docker-compose.dev.yml
ENV BASE_PATH=/llm-admin
RUN npm run build

# Stage 3: Runner
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Create non-root user
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy built application
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# Copy entrypoint script
COPY --from=builder --chown=nextjs:nodejs /app/docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh

# Set ownership for nextjs user
RUN chown -R nextjs:nodejs /app

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# Runtime configuration (set via docker-compose or K8S ConfigMap):
# - NEXT_PUBLIC_API_URL: API endpoint (required for cross-origin, e.g., http://localhost:8000)
# - NEXT_PUBLIC_WS_URL: WebSocket endpoint (required for cross-origin, e.g., ws://localhost:8000)
# If not set, URLs are auto-detected from window.location (for same-origin K3S deployments)

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["node", "server.js"]
