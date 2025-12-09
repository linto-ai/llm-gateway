import { create } from 'zustand';

interface ProviderFilters {
  search: string;
  providerType?: string;
  securityLevel?: string;
}

interface ModelFilters {
  search: string;
  providerId?: string;
  isVerified?: boolean;
}

interface ServiceFilters {
  search: string;
  serviceType?: string;
  organizationId?: string;
}

interface PromptFilters {
  search: string;
  organizationId?: string;
}

interface FilterState {
  // Provider filters
  providerFilters: ProviderFilters;
  setProviderFilters: (filters: Partial<ProviderFilters>) => void;
  resetProviderFilters: () => void;

  // Model filters
  modelFilters: ModelFilters;
  setModelFilters: (filters: Partial<ModelFilters>) => void;
  resetModelFilters: () => void;

  // Service filters
  serviceFilters: ServiceFilters;
  setServiceFilters: (filters: Partial<ServiceFilters>) => void;
  resetServiceFilters: () => void;

  // Prompt filters
  promptFilters: PromptFilters;
  setPromptFilters: (filters: Partial<PromptFilters>) => void;
  resetPromptFilters: () => void;

  // Global reset
  resetAllFilters: () => void;
}

const defaultProviderFilters: ProviderFilters = { search: '' };
const defaultModelFilters: ModelFilters = { search: '' };
const defaultServiceFilters: ServiceFilters = { search: '' };
const defaultPromptFilters: PromptFilters = { search: '' };

export const useFilterStore = create<FilterState>((set) => ({
  // Provider filters
  providerFilters: defaultProviderFilters,
  setProviderFilters: (filters) =>
    set((state) => ({
      providerFilters: { ...state.providerFilters, ...filters },
    })),
  resetProviderFilters: () => set({ providerFilters: defaultProviderFilters }),

  // Model filters
  modelFilters: defaultModelFilters,
  setModelFilters: (filters) =>
    set((state) => ({
      modelFilters: { ...state.modelFilters, ...filters },
    })),
  resetModelFilters: () => set({ modelFilters: defaultModelFilters }),

  // Service filters
  serviceFilters: defaultServiceFilters,
  setServiceFilters: (filters) =>
    set((state) => ({
      serviceFilters: { ...state.serviceFilters, ...filters },
    })),
  resetServiceFilters: () => set({ serviceFilters: defaultServiceFilters }),

  // Prompt filters
  promptFilters: defaultPromptFilters,
  setPromptFilters: (filters) =>
    set((state) => ({
      promptFilters: { ...state.promptFilters, ...filters },
    })),
  resetPromptFilters: () => set({ promptFilters: defaultPromptFilters }),

  // Global reset
  resetAllFilters: () =>
    set({
      providerFilters: defaultProviderFilters,
      modelFilters: defaultModelFilters,
      serviceFilters: defaultServiceFilters,
      promptFilters: defaultPromptFilters,
    }),
}));
