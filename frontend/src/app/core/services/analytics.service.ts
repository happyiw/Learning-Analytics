import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { PersonalAnalyticsSnapshot } from '../models/dashboard.models';

@Injectable({
  providedIn: 'root'
})
export class AnalyticsService {
  private readonly http = inject(HttpClient);

  getSnapshot(): Observable<PersonalAnalyticsSnapshot> {
    return this.http.get<PersonalAnalyticsSnapshot>('/api/analytics/my/snapshot/');
  }
}
