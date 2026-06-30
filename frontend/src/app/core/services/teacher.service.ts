import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { forkJoin, Observable } from 'rxjs';
import { CourseCard, PersonalAnalyticsSnapshot, PersonalRecommendation } from '../models/dashboard.models';
import {
  TeacherCourseDashboard,
  TeacherStudentDetail,
  TopicResultAggregate
} from '../models/teacher.models';

@Injectable({
  providedIn: 'root'
})
export class TeacherService {
  private readonly http = inject(HttpClient);

  listCourses(): Observable<CourseCard[]> {
    return this.http.get<CourseCard[]>('/api/courses/');
  }

  getCourseDashboard(courseId: number): Observable<TeacherCourseDashboard> {
    return this.http.get<TeacherCourseDashboard>(`/api/teacher/courses/${courseId}/dashboard/`);
  }

  getGroupTopicResults(courseId: number, groupId: string): Observable<TopicResultAggregate[]> {
    return this.http.get<TopicResultAggregate[]>(
      `/api/teacher/courses/${courseId}/groups/${encodeURIComponent(groupId)}/topic-results/`
    );
  }

  getStudentSnapshot(courseId: number, studentId: number): Observable<PersonalAnalyticsSnapshot> {
    return this.http.get<PersonalAnalyticsSnapshot>(
      `/api/teacher/courses/${courseId}/students/${studentId}/snapshot/`
    );
  }

  getStudentRecommendations(courseId: number, studentId: number): Observable<PersonalRecommendation[]> {
    return this.http.get<PersonalRecommendation[]>(
      `/api/teacher/courses/${courseId}/students/${studentId}/recommendations/`
    );
  }

  getStudentDetail(courseId: number, studentId: number): Observable<TeacherStudentDetail> {
    return forkJoin({
      snapshot: this.getStudentSnapshot(courseId, studentId),
      recommendations: this.getStudentRecommendations(courseId, studentId)
    });
  }
}
