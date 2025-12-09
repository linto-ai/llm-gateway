import { useQuery, useMutation } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import type { FailoverChainResponse, ValidateFailoverResponse } from '@/types/service';

/**
 * Hook to fetch the complete failover chain for a flavor
 */
export function useFailoverChain(serviceId?: string, flavorId?: string) {
  return useQuery({
    queryKey: ['failover-chain', serviceId, flavorId],
    queryFn: async () => {
      const response = await apiClient.get<FailoverChainResponse>(
        `/api/v1/services/${serviceId}/flavors/${flavorId}/failover-chain`
      );
      return response;
    },
    enabled: !!serviceId && !!flavorId,
    staleTime: 30000, // 30 seconds cache
  });
}

/**
 * Hook to validate a proposed failover configuration (cycle detection)
 */
export function useValidateFailover(serviceId: string, flavorId: string) {
  return useMutation({
    mutationFn: async (failoverFlavorId: string) => {
      const response = await apiClient.post<ValidateFailoverResponse>(
        `/api/v1/services/${serviceId}/flavors/${flavorId}/validate-failover`,
        { failover_flavor_id: failoverFlavorId }
      );
      return response;
    },
  });
}
