export interface User {
  id: string;
  email: string;
  name: string;
  role: 'student' | 'administrator';
  preferred_llm?: string;
  is_active: boolean;
  current_streak?: number;
  longest_streak?: number;
  last_login_date?: string | null;
  last_login?: string | null;
  created_at: string;
  updated_at: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  streak_increased?: boolean;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  name: string;
  role?: 'student' | 'administrator';
  preferred_llm?: string;
}

export interface AuthResponse {
  success: boolean;
  message: string;
  data: AuthTokens & { user: User };
}

