import { NextResponse } from 'next/server';
import { ADMIN_AUTH_COOKIE } from '@/lib/get-server-token';

export async function POST(request: Request) {
  const body = (await request.json()) as { token?: unknown };

  if (typeof body.token !== 'string' || body.token.length === 0) {
    return NextResponse.json({ error: 'token is required' }, { status: 400 });
  }

  const response = NextResponse.json({ ok: true });
  response.cookies.set(ADMIN_AUTH_COOKIE, body.token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    path: '/',
  });

  return response;
}
