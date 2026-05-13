import type { Metadata } from 'next';
import type { ReactNode } from 'react';
import { Providers } from '../providers';
import './globals.css';

export const metadata: Metadata = {
  title: '外贸获客SaaS',
  description: '外贸获客SaaS 后台管理系统',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
