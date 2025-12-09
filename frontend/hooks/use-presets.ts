import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type {
  FlavorPreset,
  CreatePresetRequest,
  UpdatePresetRequest,
} from '@/types/preset';

const PRESETS_KEY = ['flavor-presets'];

export function usePresets(serviceType?: string) {
  return useQuery<FlavorPreset[]>({
    queryKey: [...PRESETS_KEY, serviceType],
    queryFn: async (): Promise<FlavorPreset[]> => {
      const params = serviceType ? `?service_type=${serviceType}` : '';
      // api interceptor extracts response.data
      return api.get(`/api/v1/flavor-presets${params}`);
    },
  });
}

export function usePreset(presetId: string) {
  return useQuery<FlavorPreset>({
    queryKey: [...PRESETS_KEY, presetId],
    queryFn: async (): Promise<FlavorPreset> => {
      return api.get(`/api/v1/flavor-presets/${presetId}`);
    },
    enabled: !!presetId,
  });
}

export function useCreatePreset() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: CreatePresetRequest): Promise<FlavorPreset> => {
      return api.post('/api/v1/flavor-presets', data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PRESETS_KEY });
    },
  });
}

export function useUpdatePreset() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ presetId, data }: { presetId: string; data: UpdatePresetRequest }): Promise<FlavorPreset> => {
      return api.patch(`/api/v1/flavor-presets/${presetId}`, data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PRESETS_KEY });
    },
  });
}

export function useDeletePreset() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (presetId: string): Promise<void> => {
      await api.delete(`/api/v1/flavor-presets/${presetId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PRESETS_KEY });
    },
  });
}

export function useApplyPreset() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      presetId,
      serviceId,
      modelId,
      flavorName,
    }: {
      presetId: string;
      serviceId: string;
      modelId: string;
      flavorName: string;
    }) => {
      const formData = new FormData();
      formData.append('service_id', serviceId);
      formData.append('model_id', modelId);
      formData.append('flavor_name', flavorName);

      return api.post(`/api/v1/flavor-presets/${presetId}/apply`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['services'] });
    },
  });
}
