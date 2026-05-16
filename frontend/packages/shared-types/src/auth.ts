export interface JWTPayload {
  sub: string;
  tid?: string;
  slug?: string;
  roles: string[];
  exp: number;
  iat: number;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TenantLoginRequest extends LoginRequest {
  slug: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: 'bearer';
  must_change_pwd?: boolean;
}

export interface ChangePasswordRequest {
  old_password: string;
  new_password: string;
}

export interface CurrentUser {
  id: string;
  tenant_id: string;
  slug?: string;
  email: string;
  name: string;
  roles: string[];
  needs_onboarding: boolean;
  must_change_pwd: boolean;
}
