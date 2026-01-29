'use client';

import { useTranslations } from 'next-intl';
import { useEffect, useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { useConfig } from '@/components/providers/ConfigProvider';
import { getApi } from '@/lib/api';

export function Footer() {
  const t = useTranslations('app');
  const config = useConfig();
  const [isConnected, setIsConnected] = useState(true);

  useEffect(() => {
    // Wait for config to load before checking connection
    if (config.isLoading) return;

    const checkConnection = async () => {
      try {
        const api = getApi();
        await api.get('/healthcheck');
        setIsConnected(true);
      } catch (error) {
        setIsConnected(false);
      }
    };

    checkConnection();
    const interval = setInterval(checkConnection, 30000); // Check every 30s

    return () => clearInterval(interval);
  }, [config.isLoading]);

  return (
    <footer className="border-t bg-background">
      <div className="flex h-12 items-center justify-between px-4">
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          <span>{t('version')}: 0.1.0</span>
          <Separator orientation="vertical" className="h-4" />
          <div className="flex items-center gap-2">
            <span>{t('connectionStatus')}:</span>
            <Badge
              variant={isConnected ? 'default' : 'destructive'}
              className="text-xs"
            >
              {isConnected ? t('connected') : t('disconnected')}
            </Badge>
          </div>
        </div>
      </div>
    </footer>
  );
}
