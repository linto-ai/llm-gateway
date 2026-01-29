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

  return (
    <ConfigContext.Provider value={config}>
      {children}
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
