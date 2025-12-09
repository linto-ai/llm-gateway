import { getRequestConfig } from 'next-intl/server';
import { notFound } from 'next/navigation';

export const locales = ['en', 'fr'] as const;
export type Locale = (typeof locales)[number];

export default getRequestConfig(async ({ requestLocale }) => {
  // Await the requestLocale promise (Next.js 15 requirement)
  const requestedLocale = await requestLocale;

  // Default to 'en' if locale is undefined, or use the requested locale
  const locale = requestedLocale && locales.includes(requestedLocale as Locale)
    ? requestedLocale
    : 'en';

  return {
    locale,
    messages: (await import(`./messages/${locale}.json`)).default,
  };
});
