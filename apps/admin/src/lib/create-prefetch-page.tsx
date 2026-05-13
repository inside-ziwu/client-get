import 'server-only';

import { dehydrate, HydrationBoundary, type QueryKey } from '@tanstack/react-query';
import type { ComponentType } from 'react';
import { createServerQueryClient } from './server-query-client';
import { getServerToken } from './get-server-token';

interface PrefetchPageOptions<TData> {
  queryKey: QueryKey;
  fetchFn: (token: string) => Promise<TData>;
  Component: ComponentType;
}

export function createPrefetchPage<TData>({
  queryKey,
  fetchFn,
  Component,
}: PrefetchPageOptions<TData>) {
  return async function PrefetchPage() {
    const queryClient = createServerQueryClient();
    const token = await getServerToken();

    if (token) {
      try {
        await queryClient.prefetchQuery({
          queryKey,
          queryFn: () => fetchFn(token),
        });
      } catch {
        // 预取失败时交给客户端 useQuery 继续加载，避免服务端白屏。
      }
    }

    return (
      <HydrationBoundary state={dehydrate(queryClient)}>
        <Component />
      </HydrationBoundary>
    );
  };
}
