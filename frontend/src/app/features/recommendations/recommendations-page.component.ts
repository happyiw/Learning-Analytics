import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { PersonalRecommendation } from '../../core/models/dashboard.models';
import {
  RecommendationScope,
  RecommendationService
} from '../../core/services/recommendation.service';

@Component({
  selector: 'app-recommendations-page',
  imports: [CommonModule, FormsModule],
  templateUrl: './recommendations-page.component.html',
  styleUrl: './recommendations-page.component.css'
})
export class RecommendationsPageComponent implements OnInit {
  private readonly recommendationService = inject(RecommendationService);

  readonly isLoading = signal(false);
  readonly errorMessage = signal('');
  readonly recommendations = signal<PersonalRecommendation[]>([]);

  scope: RecommendationScope = 'all';
  scopeId: number | null = null;

  ngOnInit(): void {
    this.loadRecommendations();
  }

  applyScope(scope: RecommendationScope): void {
    this.scope = scope;
    if (scope === 'all') {
      this.scopeId = null;
      this.loadRecommendations();
    }
  }

  submitFilter(): void {
    this.loadRecommendations();
  }

  trackByRecommendationId(_: number, item: PersonalRecommendation): number {
    return item.id;
  }

  private loadRecommendations(): void {
    this.isLoading.set(true);
    this.errorMessage.set('');

    this.recommendationService.getRecommendations(this.scope, this.scopeId).subscribe({
      next: (recommendations) => {
        this.recommendations.set(recommendations);
        this.isLoading.set(false);
      },
      error: (error: HttpErrorResponse) => {
        this.errorMessage.set(
          error.error?.detail || 'Не удалось загрузить персональные рекомендации.'
        );
        this.isLoading.set(false);
      }
    });
  }
}
