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
  role: 'student';
}

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
  role: string;
  university: string | null;
  group: string | null;
  course_year: number | null;
  created_at: string;
}
