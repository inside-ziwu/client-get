import { type NextRequest, NextResponse } from 'next/server';

const AUTH_COOKIE = 'admin_auth_token';

export function middleware(request: NextRequest) {
  const token = request.cookies.get(AUTH_COOKIE)?.value;

  if (!token) {
    return NextResponse.redirect(new URL('/login', request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!login|admin/api|api|_next/static|_next/image|favicon\\.ico).*)'],
};
