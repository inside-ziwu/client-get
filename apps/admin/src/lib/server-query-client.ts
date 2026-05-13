import 'server-only';

import { QueryClient } from '@tanstack/react-query';

export function createServerQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        retry: 0,
      },
    },
  });
}
