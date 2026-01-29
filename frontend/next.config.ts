import type { NextConfig } from "next";
import createNextIntlPlugin from 'next-intl/plugin';

const withNextIntl = createNextIntlPlugin('./i18n/request.ts');

// basePath is set at BUILD TIME via BASE_PATH env var (Next.js limitation)
// - Production Dockerfile: BASE_PATH=/llm-admin (hardcoded)
// - Development (npm run dev): no basePath (runs at root)
const basePath = process.env.BASE_PATH || undefined;

const nextConfig: NextConfig = {
  output: 'standalone',
  basePath,
  typescript: {
    ignoreBuildErrors: false,
  },
};

export default withNextIntl(nextConfig);
