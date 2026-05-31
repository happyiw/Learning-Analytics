import {
  CourseCard,
  PersonalRecommendation,
  ProgressSummary,
  TopicResult
} from './dashboard.models';

export interface ModuleItem {
  id: number;
  course_id: number;
  title: string;
  description: string | null;
  order: number;
}

export interface LessonItem {
  id: number;
  module_id: number;
  title: string;
  content: string;
  video_url: string | null;
  external_url: string | null;
  order: number;
  created_at: string;
}

export interface LessonDetail extends LessonItem {
  is_completed: boolean;
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
  task_type: string | null;
  difficulty_level: string | null;
  explanation: string | null;
  max_score: number;
  order: number;
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
  question_type: string;
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

export interface UserAnswer {
  id: number;
  attempt_id: number;
  question_id: number;
  selected_option_id: number | null;
  text_answer: string | null;
  is_correct: boolean;
  score_received: number;
  answered_at: string;
}

export interface AttemptResult {
  attempt: TestAttempt;
  answers: UserAnswer[];
}

export interface UserAnswerPayload {
  question_id: number;
  selected_option_id?: number | null;
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
