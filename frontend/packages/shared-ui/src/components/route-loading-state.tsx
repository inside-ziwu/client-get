export function RouteLoadingState() {
  return (
    <div
      aria-busy="true"
      aria-label="页面加载中"
      className="space-y-6"
      role="status"
    >
      <span className="sr-only">页面加载中</span>
      <div className="flex items-center justify-between gap-4">
        <div className="h-8 w-48 max-w-[60%] animate-pulse rounded-md bg-muted" />
        <div className="h-9 w-24 animate-pulse rounded-md bg-muted" />
      </div>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {Array.from({ length: 3 }).map((_, index) => (
          <div key={index} className="rounded-xl border border-border bg-card p-5">
            <div className="h-4 w-24 animate-pulse rounded bg-muted" />
            <div className="mt-4 h-8 w-32 animate-pulse rounded bg-muted" />
            <div className="mt-3 h-3 w-full animate-pulse rounded bg-muted" />
          </div>
        ))}
      </div>
      <div className="rounded-xl border border-border bg-card p-5">
        <div className="h-5 w-40 animate-pulse rounded bg-muted" />
        <div className="mt-6 space-y-3">
          {Array.from({ length: 5 }).map((_, index) => (
            <div key={index} className="h-10 animate-pulse rounded-md bg-muted" />
          ))}
        </div>
      </div>
    </div>
  );
}
