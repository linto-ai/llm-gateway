import createMiddleware from 'next-intl/middleware';
import { routing } from './i18n/routing';

export default createMiddleware(routing);

export const config = {
  matcher: [
    // Match all pathnames except:
    // - API routes starting with /api
    // - Internal routes (for runtime config)
    // - Next.js internals (_next)
    // - Static files with extensions
    '/((?!api|internal|_next|.*\\..*).*)'
  ],
};
