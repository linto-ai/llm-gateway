import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { api } from '@/lib/api';
import { useConfig } from '@/components/providers/ConfigProvider';
import { buildApiUrl } from '@/lib/config';
import type {
  TokenizerListResponse,
  TokenizerPreloadResponse,
  TokenizerDeleteResponse,
} from '@/types/tokenizer';

/**
 * TanStack Query hooks for Tokenizer operations
 */

// List local tokenizers
export const useTokenizers = () => {
  return useQuery({
    queryKey: ['tokenizers'],
    queryFn: async (): Promise<TokenizerListResponse> => {
      return api.get('/api/v1/tokenizers');
    },
  });
};

// Preload tokenizer for a model
export const usePreloadTokenizer = () => {
  const queryClient = useQueryClient();
  return useMutation<TokenizerPreloadResponse, Error, string>({
    mutationFn: async (modelId: string) => {
      return api.post(`/api/v1/tokenizers/preload/${modelId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tokenizers'] });
    },
  });
};

// Preload tokenizer by HuggingFace repo (with extended timeout for downloads)
// Note: This hook requires config context, so it must be used within ConfigProvider
export const usePreloadTokenizerByRepo = () => {
  const queryClient = useQueryClient();
  const config = useConfig();

  return useMutation<TokenizerPreloadResponse, Error, string>({
    mutationFn: async (repo: string) => {
      if (config.isLoading) {
        throw new Error('Config not yet loaded');
      }
      const apiBaseUrl = buildApiUrl(config);
      const params = new URLSearchParams({ repo });
      // Use extended timeout (5 minutes) for tokenizer downloads
      try {
        const response = await axios.post<TokenizerPreloadResponse>(
          `${apiBaseUrl}/api/v1/tokenizers/preload-repo?${params.toString()}`,
          null,
          { timeout: 300000 }
        );
        return response.data;
      } catch (error: any) {
        // Extract error message from FastAPI response
        const detail = error.response?.data?.detail;
        throw new Error(detail || error.message || 'Failed to download tokenizer');
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tokenizers'] });
    },
  });
};

// Delete tokenizer
export const useDeleteTokenizer = () => {
  const queryClient = useQueryClient();
  return useMutation<TokenizerDeleteResponse, Error, string>({
    mutationFn: async (tokenizerId: string) => {
      return api.delete(`/api/v1/tokenizers/${encodeURIComponent(tokenizerId)}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tokenizers'] });
    },
  });
};
