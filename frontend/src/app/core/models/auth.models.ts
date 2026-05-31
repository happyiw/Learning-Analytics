export interface LoginPayload {
  username: string;
  password: string;
}

export interface RegisterPayload extends LoginPayload {
  email?: string | null;
  first_name?: string | null;
  last_name?: string | null;
  university?: string | null;
  group?: string | null;
  course_year?: number | null;
}

export type UserRole = 'student' | 'teacher' | 'admin';

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UserProfile {
  id: number;
  username: string;
  email: string | null;
  first_name: string | null;
  last_name: string | null;
  role: UserRole;
  university: string | null;
  group: string | null;
  course_year: number | null;
  created_at: string;
}
