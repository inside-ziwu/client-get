import 'server-only';

import { cookies } from 'next/headers';

export const ADMIN_AUTH_COOKIE = 'admin_auth_token';

export async function getServerToken() {
  const cookieStore = await cookies();
  return cookieStore.get(ADMIN_AUTH_COOKIE)?.value ?? null;
}
