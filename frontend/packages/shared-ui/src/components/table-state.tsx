import { Button } from './button';

export type TableStateSpec =
  | { kind: 'loading' }
  | { kind: 'empty'; filtered?: boolean; onResetFilters?: () => void }
  | { kind: 'error'; description?: string; onRetry?: () => void };

export interface TableStateProps {
  state: TableStateSpec;
  entityName: string;
  colSpan: number;
}

export function TableState({ state, entityName, colSpan }: TableStateProps) {
  let content;

  if (state.kind === 'loading') {
    content = <div role="status">正在加载{entityName}…</div>;
  } else if (state.kind === 'empty') {
    content = (
      <div className="flex flex-col items-center gap-ui-sm">
        <span>{state.filtered ? `没有符合当前条件的${entityName}` : `暂无${entityName}`}</span>
        {state.filtered && state.onResetFilters ? (
          <Button type="button" variant="outline" size="sm" onClick={state.onResetFilters}>
            重置筛选
          </Button>
        ) : null}
      </div>
    );
  } else {
    content = (
      <div role="alert" className="flex flex-col items-center gap-ui-sm">
        <strong className="text-ui-body-strong text-ui-foreground">{entityName}加载失败</strong>
        {state.description ? <span>{state.description}</span> : null}
        {state.onRetry ? (
          <Button type="button" variant="outline" size="sm" onClick={state.onRetry}>
            重试
          </Button>
        ) : null}
      </div>
    );
  }

  return (
    <tr>
      <td colSpan={colSpan} className="px-ui-md py-12 text-center text-ui-body text-ui-muted-foreground">
        {content}
      </td>
    </tr>
  );
}
