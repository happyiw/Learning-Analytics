export interface EnrolledCourse {
  course_id: number;
  enrolled_at: string;
}

export interface CourseEnrollment {
  id: number;
  course_id: number;
  user_id: number;
  assigned_by_id: number | null;
  username: string;
  email: string | null;
  first_name: string | null;
  last_name: string | null;
  university: string | null;
  group: string | null;
  course_year: number | null;
  created_at: string;
}

export interface StudentDirectoryItem {
  id: number;
  username: string;
  email: string | null;
  first_name: string | null;
  last_name: string | null;
  university: string | null;
  group: string | null;
  course_year: number | null;
  created_at: string;
}
