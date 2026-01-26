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

# Build with basePath - default to placeholder for subpath deployments (Kubernetes)
# For root deployment, pass --build-arg NEXT_PUBLIC_BASE_PATH= to build without basePath
ARG NEXT_PUBLIC_BASE_PATH="/__NEXT_BASEPATH_PLACEHOLDER__"
ENV NEXT_PUBLIC_BASE_PATH=${NEXT_PUBLIC_BASE_PATH}
ENV NEXT_PUBLIC_API_URL="__NEXT_API_URL_PLACEHOLDER__"
ENV NEXT_PUBLIC_WS_URL="__NEXT_WS_URL_PLACEHOLDER__"

# Build the application
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

# Copy entrypoint script (from builder to ensure it's available regardless of build context)
COPY --from=builder --chown=nextjs:nodejs /app/docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh

# Ensure nextjs user can write to /app for sed -i operations at runtime
RUN chown -R nextjs:nodejs /app

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# Runtime basePath configuration (optional)
# Set BASE_PATH=/your-subpath to deploy under a subpath
ENV BASE_PATH=""

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["node", "server.js"]
