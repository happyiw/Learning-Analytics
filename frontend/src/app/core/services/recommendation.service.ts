import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { PersonalRecommendation } from '../models/dashboard.models';

export type RecommendationScope = 'all' | 'course' | 'module';

@Injectable({
  providedIn: 'root'
})
export class RecommendationService {
  private readonly http = inject(HttpClient);

  getRecommendations(scope: RecommendationScope, scopeId?: number | null): Observable<PersonalRecommendation[]> {
    if (scope === 'course' && scopeId) {
      return this.http.get<PersonalRecommendation[]>(`/api/courses/${scopeId}/recommendations/my/`);
    }

    if (scope === 'module' && scopeId) {
      return this.http.get<PersonalRecommendation[]>(`/api/modules/${scopeId}/recommendations/my/`);
    }

    return this.http.get<PersonalRecommendation[]>('/api/recommendations/my/');
  }
}
