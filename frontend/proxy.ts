import createMiddleware from 'next-intl/middleware';
import { NextRequest, NextResponse } from 'next/server';
import { routing } from './i18n/routing';

const intlMiddleware = createMiddleware(routing);

export default function proxy(request: NextRequest): NextResponse {
  const timestamp = new Date().toISOString();
  const ip =
    request.headers.get('x-forwarded-for')?.split(',')[0]?.trim() ||
    request.headers.get('x-real-ip') ||
    '-';
  const method = request.method;
  const path = request.nextUrl.pathname;

  console.log(`${timestamp} ${ip} ${method} ${path}`);

  return intlMiddleware(request) as NextResponse;
}

export const config = {
  matcher: [
    // Match root path for locale redirect
    '/',
    // Match all pathnames except:
    // - API routes starting with /api
    // - Internal routes (for runtime config)
    // - Next.js internals (_next)
    // - Static files with extensions
    '/((?!api|internal|_next|.*\\..*).*)'
  ],
};
