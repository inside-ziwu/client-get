'use client';

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { EmailStatsDaily } from '@shared/types';

interface EmailTrendChartProps {
  data: EmailStatsDaily[];
}

export function EmailTrendChart({ data }: EmailTrendChartProps) {
  if (!data.length) {
    return (
      <div className="flex h-[300px] items-center justify-center text-sm text-muted-foreground">
        暂无发送数据
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} />
        <XAxis
          dataKey="date"
          fontSize={12}
          tickFormatter={(v: string) => v.slice(5)}
        />
        <YAxis fontSize={12} />
        <Tooltip />
        <Legend />
        <Bar dataKey="sent" name="已发送" stackId="a" fill="#1677ff" />
        <Bar dataKey="delivered" name="已送达" stackId="a" fill="#52c41a" />
        <Bar dataKey="opens" name="打开" stackId="a" fill="#fa8c16" />
      </BarChart>
    </ResponsiveContainer>
  );
}
