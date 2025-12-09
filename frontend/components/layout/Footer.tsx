'use client';

import { useTranslations } from 'next-intl';
import { useEffect, useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { api } from '@/lib/api';

export function Footer() {
  const t = useTranslations('app');
  const [isConnected, setIsConnected] = useState(true);

  useEffect(() => {
    const checkConnection = async () => {
      try {
        await api.get('/healthcheck');
        setIsConnected(true);
      } catch (error) {
        setIsConnected(false);
      }
    };

    checkConnection();
    const interval = setInterval(checkConnection, 30000); // Check every 30s

    return () => clearInterval(interval);
  }, []);

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
