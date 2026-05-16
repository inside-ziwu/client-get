'use client';

import { type ReactNode } from 'react';
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Input,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@shared/ui';

export function PageHeader({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="tenant-page-header">
      <div>
        <h1 className="tenant-page-title">{title}</h1>
        {description ? <p className="tenant-page-description">{description}</p> : null}
      </div>
      {action}
    </div>
  );
}

export function SearchBar({
  value,
  onChange,
  onSubmit,
  placeholder = '搜索',
}: {
  value: string;
  onChange: (value: string) => void;
  onSubmit?: () => void;
  placeholder?: string;
}) {
  return (
    <div className="flex flex-col gap-2 sm:flex-row">
      <Input value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} />
      <Button type="button" variant="outline" onClick={onSubmit}>
        搜索
      </Button>
    </div>
  );
}

export function DataTable<T>({
  title,
  rows,
  columns,
  emptyText = '暂无数据',
}: {
  title?: string;
  rows?: T[];
  columns: Array<{ key: string; title: string; render: (row: T) => ReactNode }>;
  emptyText?: string;
}) {
  return (
    <Card>
      {title ? (
        <CardHeader>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
      ) : null}
      <CardContent className={title ? undefined : 'pt-5'}>
        <Table>
          <TableHeader>
            <TableRow>
              {columns.map((column) => (
                <TableHead key={column.key}>{column.title}</TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {(rows ?? []).map((row, index) => (
              <TableRow key={String((row as { id?: string }).id ?? index)}>
                {columns.map((column) => (
                  <TableCell key={column.key}>{column.render(row)}</TableCell>
                ))}
              </TableRow>
            ))}
            {!rows?.length ? (
              <TableRow>
                <TableCell colSpan={columns.length} className="py-8 text-center text-muted-foreground">
                  {emptyText}
                </TableCell>
              </TableRow>
            ) : null}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
