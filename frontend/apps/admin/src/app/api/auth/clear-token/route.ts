import { NextResponse } from 'next/server';
import { ADMIN_AUTH_COOKIE } from '@/lib/get-server-token';

export async function POST() {
  const response = NextResponse.json({ ok: true });
  response.cookies.delete(ADMIN_AUTH_COOKIE);
  return response;
}
