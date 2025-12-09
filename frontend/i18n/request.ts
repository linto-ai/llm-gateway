import { getRequestConfig } from 'next-intl/server';
import { hasLocale } from 'next-intl';
import { routing } from './routing';

export default getRequestConfig(async ({ requestLocale }) => {
  // Await the requestLocale promise (Next.js 15 requirement)
  const requested = await requestLocale;

  // Validate and fallback to default locale
  const locale = hasLocale(routing.locales, requested)
    ? requested
    : routing.defaultLocale;

  // Import all scoped message files
  const [
    common,
    navigation,
    providers,
    models,
    services,
    prompts,
    jobs,
    errors,
    validation,
    flavors,
    presets,
    analytics,
    templates,
    metadata
  ] = await Promise.all([
    import(`../messages/${locale}/common.json`),
    import(`../messages/${locale}/navigation.json`),
    import(`../messages/${locale}/providers.json`),
    import(`../messages/${locale}/models.json`),
    import(`../messages/${locale}/services.json`),
    import(`../messages/${locale}/prompts.json`),
    import(`../messages/${locale}/jobs.json`),
    import(`../messages/${locale}/errors.json`),
    import(`../messages/${locale}/validation.json`),
    import(`../messages/${locale}/flavors.json`),
    import(`../messages/${locale}/presets.json`),
    import(`../messages/${locale}/analytics.json`),
    import(`../messages/${locale}/templates.json`),
    import(`../messages/${locale}/metadata.json`)
  ]);

  return {
    locale,
    messages: {
      common: common.default,
      app: navigation.default.app,
      nav: navigation.default.nav,
      providers: providers.default,
      models: models.default,
      services: services.default,
      prompts: prompts.default,
      jobs: jobs.default,
      errors: errors.default,
      validation: validation.default,
      flavors: flavors.default,
      presets: presets.default,
      analytics: analytics.default,
      templates: templates.default,
      metadata: metadata.default
    }
  };
});
