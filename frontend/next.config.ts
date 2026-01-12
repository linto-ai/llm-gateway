import type { NextConfig } from "next";
import createNextIntlPlugin from 'next-intl/plugin';

const withNextIntl = createNextIntlPlugin('./i18n/request.ts');

// basePath configuration:
// - Docker: Set NEXT_PUBLIC_BASE_PATH="/__NEXT_BASEPATH_PLACEHOLDER__" at build time
//           Entrypoint script replaces placeholder with actual BASE_PATH at runtime
// - Local dev: Leave empty for root deployment, or set specific path
const basePath = process.env.NEXT_PUBLIC_BASE_PATH || '';

// Empty string means root deployment (undefined for Next.js)
const resolvedBasePath = basePath ? basePath : undefined;

const nextConfig: NextConfig = {
  output: 'standalone',
  basePath: resolvedBasePath,
  typescript: {
    ignoreBuildErrors: false,
  },
};

export default withNextIntl(nextConfig);
