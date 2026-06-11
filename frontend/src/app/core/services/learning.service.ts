import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { forkJoin, Observable } from 'rxjs';
import { PersonalRecommendation, ProgressSummary, TopicResult } from '../models/dashboard.models';
import {
  AttemptResult,
  CoursePageSnapshot,
  LessonCompletion,
  LessonDetail,
  ModuleItem,
  ModulePageSnapshot,
  PublicQuestion,
  QuestionAnalytics,
  TaskItem,
  TestAnalytics,
  TestAttempt,
  TestItem,
  UnfinishedAttempt,
  UserAnswer,
  UserAnswerPayload
} from '../models/learning.models';
import { CourseCard } from '../models/dashboard.models';
import { LessonItem } from '../models/learning.models';

@Injectable({
  providedIn: 'root'
})
export class LearningService {
  private readonly http = inject(HttpClient);

  getCourse(courseId: number): Observable<CourseCard> {
    return this.http.get<CourseCard>(`/api/courses/${courseId}/`);
  }

  getCourseModules(courseId: number): Observable<ModuleItem[]> {
    return this.http.get<ModuleItem[]>(`/api/courses/${courseId}/modules/`);
  }

  getCourseProgress(courseId: number): Observable<ProgressSummary> {
    return this.http.get<ProgressSummary>(`/api/courses/${courseId}/progress/my/`);
  }

  getCourseTopicResults(courseId: number): Observable<TopicResult[]> {
    return this.http.get<TopicResult[]>(`/api/courses/${courseId}/topic-results/my/`);
  }

  getCourseRecommendations(courseId: number): Observable<PersonalRecommendation[]> {
    return this.http.get<PersonalRecommendation[]>(`/api/courses/${courseId}/recommendations/my/`);
  }

  getCourseSnapshot(courseId: number): Observable<CoursePageSnapshot> {
    return forkJoin({
      course: this.getCourse(courseId),
      modules: this.getCourseModules(courseId),
      progress: this.getCourseProgress(courseId),
      topicResults: this.getCourseTopicResults(courseId),
      recommendations: this.getCourseRecommendations(courseId)
    });
  }

  getModule(moduleId: number): Observable<ModuleItem> {
    return this.http.get<ModuleItem>(`/api/modules/${moduleId}/`);
  }

  getModuleLessons(moduleId: number): Observable<LessonItem[]> {
    return this.http.get<LessonItem[]>(`/api/modules/${moduleId}/lessons/`);
  }

  getModuleTasks(moduleId: number): Observable<TaskItem[]> {
    return this.http.get<TaskItem[]>(`/api/modules/${moduleId}/tasks/`);
  }

  getModuleTests(moduleId: number): Observable<TestItem[]> {
    return this.http.get<TestItem[]>(`/api/modules/${moduleId}/tests/`);
  }

  getModuleProgress(moduleId: number): Observable<ProgressSummary> {
    return this.http.get<ProgressSummary>(`/api/modules/${moduleId}/progress/my/`);
  }

  getModuleTopicResults(moduleId: number): Observable<TopicResult[]> {
    return this.http.get<TopicResult[]>(`/api/modules/${moduleId}/topic-results/my/`);
  }

  getModuleRecommendations(moduleId: number): Observable<PersonalRecommendation[]> {
    return this.http.get<PersonalRecommendation[]>(`/api/modules/${moduleId}/recommendations/my/`);
  }

  getModuleSnapshot(moduleId: number): Observable<ModulePageSnapshot> {
    return forkJoin({
      module: this.getModule(moduleId),
      lessons: this.getModuleLessons(moduleId),
      tasks: this.getModuleTasks(moduleId),
      tests: this.getModuleTests(moduleId),
      progress: this.getModuleProgress(moduleId),
      topicResults: this.getModuleTopicResults(moduleId),
      recommendations: this.getModuleRecommendations(moduleId)
    });
  }

  getLesson(lessonId: number): Observable<LessonDetail> {
    return this.http.get<LessonDetail>(`/api/lessons/${lessonId}/`);
  }

  completeLesson(lessonId: number): Observable<LessonCompletion> {
    return this.http.post<LessonCompletion>(`/api/lessons/${lessonId}/complete/`, {});
  }

  getTask(taskId: number): Observable<TaskItem> {
    return this.http.get<TaskItem>(`/api/tasks/${taskId}/`);
  }

  getTest(testId: number): Observable<TestItem> {
    return this.http.get<TestItem>(`/api/tests/${testId}/`);
  }

  getActiveTestAttempt(testId: number): Observable<TestAttempt> {
    return this.http.get<TestAttempt>(`/api/tests/${testId}/active-attempt/`);
  }

  getTestAnalytics(testId: number): Observable<TestAnalytics> {
    return this.http.get<TestAnalytics>(`/api/tests/${testId}/analytics/my/`);
  }

  getUnfinishedAttempts(): Observable<UnfinishedAttempt[]> {
    return this.http.get<UnfinishedAttempt[]>(`/api/test-attempts/my/unfinished/`);
  }

  startTest(testId: number): Observable<TestAttempt> {
    return this.http.post<TestAttempt>(`/api/tests/${testId}/start/`, {});
  }

  getTestQuestions(testId: number): Observable<PublicQuestion[]> {
    return this.http.get<PublicQuestion[]>(`/api/tests/${testId}/questions/`);
  }

  saveAnswer(attemptId: number, payload: UserAnswerPayload): Observable<UserAnswer> {
    return this.http.post<UserAnswer>(`/api/test-attempts/${attemptId}/answers/`, payload);
  }

  finishAttempt(attemptId: number): Observable<TestAttempt> {
    return this.http.post<TestAttempt>(`/api/test-attempts/${attemptId}/finish/`, {});
  }

  getAttemptResult(attemptId: number): Observable<AttemptResult> {
    return this.http.get<AttemptResult>(`/api/test-attempts/${attemptId}/result/`);
  }

  getTestQuestionAnalytics(testId: number, userId?: number | null): Observable<QuestionAnalytics[]> {
    const query = typeof userId === 'number' ? `?user_id=${userId}` : '';
    return this.http.get<QuestionAnalytics[]>(`/api/analytics/tests/${testId}/questions/${query}`);
  }
}
