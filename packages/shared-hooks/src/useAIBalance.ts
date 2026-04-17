import { useQuery } from '@tanstack/react-query';

// This will be connected to the actual API in the app layer
// For now, expose the hook interface
export function useAIBalance() {
  return useQuery<{ amount: number; currency: string }>({
    queryKey: ['ai-balance'],
    queryFn: async () => {
      // Will be overridden by app-level provider
      throw new Error('useAIBalance must be used within an API provider');
    },
    enabled: false, // Disabled by default, apps will enable with proper queryFn
  });
}
