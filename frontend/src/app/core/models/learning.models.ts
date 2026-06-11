import {
  CourseCard,
  PersonalRecommendation,
  ProgressSummary,
  TopicResult
} from './dashboard.models';

export type QuestionType = 'single_choice' | 'multiple_choice' | 'text';

export interface LessonStatItem {
  label: string;
  value: string;
  hint: string | null;
}

export interface LessonContentBlock {
  type: 'rich_text' | 'callout' | 'bullets' | 'checklist' | 'table' | 'chart' | 'image' | 'stat_grid';
  title: string | null;
  text: string | null;
  tone: 'default' | 'info' | 'success' | 'warning' | 'accent' | null;
  paragraphs: string[];
  items: string[];
  columns: string[];
  rows: string[][];
  labels: string[];
  values: number[];
  unit: string | null;
  src: string | null;
  alt: string | null;
  caption: string | null;
  stats: LessonStatItem[];
}

export interface ModuleItem {
  id: number;
  course_id: number;
  title: string;
  description: string | null;
  order: number;
  created_at: string;
  updated_at: string;
}

export interface LessonItem {
  id: number;
  module_id: number;
  title: string;
  content: string;
  content_blocks: LessonContentBlock[];
  video_url: string | null;
  external_url: string | null;
  order: number;
  created_at: string;
  updated_at: string;
}

export interface LessonDetail extends LessonItem {
  is_completed: boolean;
  next_lesson_id: number | null;
  next_lesson_title: string | null;
}

export interface LessonCompletion {
  lesson_id: number;
  is_completed: boolean;
  completed_at: string | null;
}

export interface TaskItem {
  id: number;
  module_id: number;
  title: string;
  description: string;
  max_score: number;
  order: number;
  created_at: string;
  updated_at: string;
}

export interface TestItem {
  id: number;
  course_id: number;
  module_id: number | null;
  title: string;
  description: string | null;
  time_limit: number | null;
  passing_score: number;
  attempts_allowed: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AnswerOptionPublic {
  id: number;
  question_id: number;
  text: string;
}

export interface PublicQuestion {
  id: number;
  test_id: number;
  text: string;
  question_type: QuestionType;
  difficulty_level: string | null;
  score: number;
  order: number;
  answer_options: AnswerOptionPublic[];
}

export interface TestAttempt {
  id: number;
  user_id: number;
  test_id: number;
  started_at: string;
  finished_at: string | null;
  score: number;
  max_score: number;
  percentage: number;
  is_passed: boolean;
}

export interface TestAttemptAnalyticsItem {
  attempt_id: number;
  started_at: string;
  finished_at: string | null;
  completion_percentage: number;
  percentage: number;
  is_passed: boolean;
  time_spent_seconds: number | null;
  duration_seconds: number | null;
  answered_questions_count: number;
  status: string;
}

export interface TestAnalytics {
  test_id: number;
  attempts_count: number;
  completed_attempts_count: number;
  unfinished_attempts_count: number;
  completion_percentage: number;
  best_result: number;
  average_result: number;
  first_result: number;
  last_result: number;
  progress_delta: number;
  best_improvement: number;
  failure_streak: number;
  overall_trend: string;
  insight: string | null;
  time_spent_seconds: number | null;
  status: string;
  attempts: TestAttemptAnalyticsItem[];
}

export interface QuestionWrongOption {
  option_id: number;
  option_text: string;
  selections_count: number;
}

export interface QuestionAnalytics {
  question_id: number;
  test_id: number;
  module_id: number | null;
  question_text: string;
  question_type: QuestionType;
  order: number;
  max_score: number;
  attempts_count: number;
  correct_answers_count: number;
  incorrect_answers_count: number;
  success_rate: number;
  average_score: number;
  common_wrong_options: QuestionWrongOption[];
}

export interface UserAnswer {
  id: number;
  attempt_id: number;
  question_id: number;
  selected_option_id: number | null;
  selected_option_ids: number[];
  text_answer: string | null;
  is_correct: boolean;
  score_received: number;
  answered_at: string;
}

export interface AttemptResult {
  attempt: TestAttempt;
  answers: UserAnswer[];
}

export interface AttemptQuestionResultView {
  question_id: number;
  question_text: string;
  question_type: QuestionType;
  max_score: number;
  user_answer: string;
  is_correct: boolean;
  score_received: number;
}

export interface UnfinishedAttempt {
  attempt_id: number;
  test_id: number;
  test_title: string;
  course_id: number;
  course_title: string;
  module_id: number | null;
  module_title: string | null;
  started_at: string;
  last_activity_at: string;
  answered_questions: number;
  total_questions: number;
  time_limit: number | null;
}

export interface UserAnswerPayload {
  question_id: number;
  selected_option_id?: number | null;
  selected_option_ids?: number[];
  text_answer?: string | null;
}

export interface CoursePageSnapshot {
  course: CourseCard;
  modules: ModuleItem[];
  progress: ProgressSummary;
  topicResults: TopicResult[];
  recommendations: PersonalRecommendation[];
}

export interface ModulePageSnapshot {
  module: ModuleItem;
  lessons: LessonItem[];
  tasks: TaskItem[];
  tests: TestItem[];
  progress: ProgressSummary;
  topicResults: TopicResult[];
  recommendations: PersonalRecommendation[];
}
