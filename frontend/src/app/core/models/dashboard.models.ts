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
  current_percentage: number;
  current_result: number;
  weakness_level: string;
  topic_state?: string | null;
  rule_key?: string | null;
  priority?: string | null;
  reason?: string | null;
  topic_reason?: string | null;
  progress_delta: number;
  completed_lessons_ratio: number;
}

export interface CourseCard {
  id: number;
  title: string;
  description: string | null;
  author_id: number | null;
  difficulty: number;
  is_published: boolean;
  is_open: boolean;
  created_at: string;
  updated_at: string;
}

export interface DashboardSnapshot {
  progress: ProgressSummary;
  summary: AnalyticsSummary;
  recommendations: PersonalRecommendation[];
  coursesCount: number;
}

export interface TopicResult {
  id: number | null;
  module_id: number;
  module_title: string;
  attempts_count: number;
  average_percentage: number;
  best_percentage: number;
  last_percentage: number;
  first_percentage: number;
  progress_delta: number;
  trend: string;
  stability_index: number | null;
  completed_lessons_ratio: number;
  completed_attempts_count: number;
  passed_attempts_count: number;
  failed_attempts_count: number;
  weakness_level: string;
  risk_level: string | null;
  learning_state: string | null;
  reason_code: string | null;
  last_attempt_at: string | null;
  updated_at: string | null;
  reason?: string | null;
  category?: string | null;
  tags: string[];
}

export interface AnalyticsDynamicsPoint {
  attempt_id: number;
  date: string;
  test_id: number;
  test_title: string;
  module_id: number | null;
  module_title: string | null;
  percentage: number;
  is_passed: boolean;
}

export interface PersonalAnalyticsSnapshot {
  progress: ProgressSummary;
  summary: AnalyticsSummary;
  topicResults: TopicResult[];
  weakTopics: TopicResult[];
  strongTopics: TopicResult[];
  bestTopics: TopicResult[];
  unstableTopics: TopicResult[];
  improvingTopics: TopicResult[];
  topicsWithoutEnoughData: TopicResult[];
  dynamics: AnalyticsDynamicsPoint[];
}
