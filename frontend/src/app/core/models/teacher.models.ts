import { CourseCard, PersonalAnalyticsSnapshot, PersonalRecommendation } from './dashboard.models';

export interface TopicResultAggregate {
  module_id: number;
  module_title: string;
  users_count: number;
  attempts_count: number;
  average_percentage: number;
  best_percentage: number;
  high_weakness_count: number;
  medium_weakness_count: number;
  low_weakness_count: number;
}

export interface TeacherCourseSummary {
  enrolled_students_count: number;
  groups_count: number;
  active_students_count: number;
  average_completion_rate: number;
  average_test_percentage: number;
  at_risk_students_count: number;
}

export interface TeacherGroupSummary {
  group_id: string;
  students_count: number;
  average_completion_rate: number;
  average_test_percentage: number;
  average_completed_lessons: number;
  average_passed_tests: number;
  at_risk_students_count: number;
  low_activity_students_count: number;
}

export interface TeacherStudentSummary {
  id: number;
  username: string;
  first_name: string | null;
  last_name: string | null;
  group: string | null;
  course_year: number | null;
  completion_rate: number;
  average_test_percentage: number;
  completed_lessons: number;
  total_lessons: number;
  passed_tests: number;
  total_tests: number;
  attempts_count: number;
  weak_topics_count: number;
  high_risk_topics_count: number;
  unfinished_topics_count: number;
  last_activity_at: string | null;
}

export interface TeacherCourseDashboard {
  course: CourseCard;
  summary: TeacherCourseSummary;
  groups: TeacherGroupSummary[];
  students: TeacherStudentSummary[];
  module_topic_results: TopicResultAggregate[];
}

export interface TeacherStudentDetail {
  summary: TeacherStudentSummary;
  snapshot: PersonalAnalyticsSnapshot;
  recommendations: PersonalRecommendation[];
}
