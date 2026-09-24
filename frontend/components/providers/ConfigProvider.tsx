'use client';

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import type { RuntimeConfig, ConfigContextValue } from '@/lib/config';
import { getConfig, setConfigCache } from '@/lib/config';

const defaultConfig: ConfigContextValue = {
  apiUrl: '',
  wsUrl: '',
  basePath: '',
  appName: 'LLM Gateway',
  isLoading: true,
};

const ConfigContext = createContext<ConfigContextValue>(defaultConfig);

export function ConfigProvider({ children }: { children: ReactNode }) {
  const [config, setConfig] = useState<ConfigContextValue>(defaultConfig);

  useEffect(() => {
    async function loadConfig() {
      try {
        // Use getConfig() which handles basePath detection automatically
        const data = await getConfig();

        // Update the module-level cache for synchronous access
        setConfigCache(data);

        setConfig({
          ...data,
          isLoading: false,
        });
      } catch (error) {
        console.error('Failed to load runtime config:', error);
        // Set loading to false even on error to allow app to render
        setConfig((prev) => ({ ...prev, isLoading: false }));
      }
    }

    loadConfig();
  }, []);

  // Children render only once the runtime config is known: queries run as soon as pages mount,
  // and the API client throws "Config not loaded" before that (the failed query then stays
  // paused and the page shows an empty list).
  return (
    <ConfigContext.Provider value={config}>
      {config.isLoading ? null : children}
    </ConfigContext.Provider>
  );
}

/**
 * Hook to access runtime configuration.
 * Must be used within a ConfigProvider.
 */
export function useConfig(): ConfigContextValue {
  const context = useContext(ConfigContext);
  if (context === undefined) {
    throw new Error('useConfig must be used within a ConfigProvider');
  }
  return context;
}
