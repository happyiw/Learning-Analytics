export interface ProgressSummary {
  scope_type: string;
  scope_id: number | null;
  completed_lessons: number;
  total_lessons: number;
  passed_tests: number;
  total_tests: number;
  average_test_percentage: number;
  completion_rate: number;
}

export interface AnalyticsSummary {
  total_attempts: number;
  completed_attempts: number;
  passed_attempts: number;
  average_score: number;
  average_percentage: number;
  lessons_completed: number;
  unique_courses_started: number;
}

export interface PersonalRecommendation {
  id: number;
  module_id: number;
  module_title: string;
  title: string;
  description: string;
  resource_url: string | null;
  trigger_score_threshold: number;
  current_percentage: number;
  weakness_level: string;
}

export interface CourseCard {
  id: number;
  title: string;
  description: string | null;
  author_id: number | null;
  difficulty_level: string | null;
  is_published: boolean;
  created_at: string;
  updated_at: string;
}

export interface DashboardSnapshot {
  progress: ProgressSummary;
  summary: AnalyticsSummary;
  recommendations: PersonalRecommendation[];
  coursesCount: number;
}
