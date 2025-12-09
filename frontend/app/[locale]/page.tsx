'use client';

import { useTranslations, useLocale } from 'next-intl';
import Link from 'next/link';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useProviders } from '@/hooks/use-providers';
import { useModels } from '@/hooks/use-models';
import { useServices } from '@/hooks/use-services';
import { usePrompts } from '@/hooks/use-prompts';
import { LoadingSpinner } from '@/components/shared/LoadingSpinner';
import { DashboardHealthCard } from '@/components/dashboard/DashboardHealthCard';

export default function DashboardPage() {
  const t = useTranslations('nav');
  const locale = useLocale();

  // Fetch counts from API
  const { data: providersData, isLoading: providersLoading } = useProviders({ page: 1, page_size: 1 });
  const { data: modelsData, isLoading: modelsLoading } = useModels({ page: 1, page_size: 1 });
  const { data: servicesData, isLoading: servicesLoading } = useServices({ page: 1, page_size: 1 });
  const { data: promptsData, isLoading: promptsLoading } = usePrompts({ page: 1, page_size: 1 });

  const providersCount = providersData?.total ?? 0;
  const modelsCount = modelsData?.total ?? 0;
  const servicesCount = servicesData?.total ?? 0;
  const promptsCount = promptsData?.total ?? 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">{t('dashboard')}</h1>
        <p className="text-muted-foreground">
          {t('dashboardSubtitle')}
        </p>
      </div>

      {/* System Health Card */}
      <DashboardHealthCard />

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Link href={`/${locale}/providers`}>
          <Card className="hover:bg-muted/50 transition-colors cursor-pointer">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                {t('providers')}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {providersLoading ? (
                <LoadingSpinner size="sm" />
              ) : (
                <div className="text-2xl font-bold">{providersCount}</div>
              )}
              <p className="text-xs text-muted-foreground">
                {t('activeProviders')}
              </p>
            </CardContent>
          </Card>
        </Link>

        <Link href={`/${locale}/models`}>
          <Card className="hover:bg-muted/50 transition-colors cursor-pointer">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{t('models')}</CardTitle>
            </CardHeader>
            <CardContent>
              {modelsLoading ? (
                <LoadingSpinner size="sm" />
              ) : (
                <div className="text-2xl font-bold">{modelsCount}</div>
              )}
              <p className="text-xs text-muted-foreground">
                {t('availableModels')}
              </p>
            </CardContent>
          </Card>
        </Link>

        <Link href={`/${locale}/services`}>
          <Card className="hover:bg-muted/50 transition-colors cursor-pointer">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                {t('services')}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {servicesLoading ? (
                <LoadingSpinner size="sm" />
              ) : (
                <div className="text-2xl font-bold">{servicesCount}</div>
              )}
              <p className="text-xs text-muted-foreground">
                {t('configuredServices')}
              </p>
            </CardContent>
          </Card>
        </Link>

        <Link href={`/${locale}/prompts`}>
          <Card className="hover:bg-muted/50 transition-colors cursor-pointer">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{t('prompts')}</CardTitle>
            </CardHeader>
            <CardContent>
              {promptsLoading ? (
                <LoadingSpinner size="sm" />
              ) : (
                <div className="text-2xl font-bold">{promptsCount}</div>
              )}
              <p className="text-xs text-muted-foreground">
                {t('promptTemplates')}
              </p>
            </CardContent>
          </Card>
        </Link>
      </div>
    </div>
  );
}
