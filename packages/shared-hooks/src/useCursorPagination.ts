import { useInfiniteQuery, type QueryKey } from '@tanstack/react-query';
import type { PaginatedResponse } from '@shared/types';

export function useCursorPagination<T>(
  queryKey: QueryKey,
  fetcher: (cursor?: string) => Promise<PaginatedResponse<T>>,
) {
  return useInfiniteQuery({
    queryKey,
    queryFn: ({ pageParam }) => fetcher(pageParam),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last) =>
      last.pagination.has_more ? (last.pagination.cursor ?? undefined) : undefined,
  });
}
