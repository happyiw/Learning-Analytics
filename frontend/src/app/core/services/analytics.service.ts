import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { forkJoin, Observable } from 'rxjs';
import {
  AnalyticsDynamicsPoint,
  AnalyticsSummary,
  PersonalAnalyticsSnapshot,
  ProgressSummary,
  TopicResult
} from '../models/dashboard.models';

@Injectable({
  providedIn: 'root'
})
export class AnalyticsService {
  private readonly http = inject(HttpClient);

  getSnapshot(): Observable<PersonalAnalyticsSnapshot> {
    return forkJoin({
      progress: this.http.get<ProgressSummary>('/api/progress/my/'),
      summary: this.http.get<AnalyticsSummary>('/api/analytics/my/summary/'),
      topicResults: this.http.get<TopicResult[]>('/api/topic-results/my/'),
      weakTopics: this.http.get<TopicResult[]>('/api/analytics/my/weak-topics/'),
      bestTopics: this.http.get<TopicResult[]>('/api/analytics/my/best-topics/'),
      dynamics: this.http.get<AnalyticsDynamicsPoint[]>('/api/analytics/my/dynamics/')
    });
  }
}
