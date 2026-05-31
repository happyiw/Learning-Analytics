import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { forkJoin, map, Observable } from 'rxjs';
import {
  AnalyticsSummary,
  CourseCard,
  DashboardSnapshot,
  PersonalRecommendation,
  ProgressSummary
} from '../models/dashboard.models';

@Injectable({
  providedIn: 'root'
})
export class DashboardService {
  private readonly http = inject(HttpClient);

  getSnapshot(): Observable<DashboardSnapshot> {
    return forkJoin({
      progress: this.http.get<ProgressSummary>('/api/progress/my/'),
      summary: this.http.get<AnalyticsSummary>('/api/analytics/my/summary/'),
      recommendations: this.http.get<PersonalRecommendation[]>('/api/recommendations/my/'),
      courses: this.http.get<CourseCard[]>('/api/courses/')
    }).pipe(
      map(({ progress, summary, recommendations, courses }) => ({
        progress,
        summary,
        recommendations,
        coursesCount: courses.length
      }))
    );
  }
}
