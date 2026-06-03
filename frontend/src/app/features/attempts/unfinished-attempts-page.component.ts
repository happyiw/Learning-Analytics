import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, OnInit, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { UnfinishedAttempt } from '../../core/models/learning.models';
import { LearningService } from '../../core/services/learning.service';

@Component({
  selector: 'app-unfinished-attempts-page',
  imports: [CommonModule, RouterLink],
  templateUrl: './unfinished-attempts-page.component.html',
  styleUrl: './unfinished-attempts-page.component.css'
})
export class UnfinishedAttemptsPageComponent implements OnInit {
  private readonly learningService = inject(LearningService);

  readonly isLoading = signal(false);
  readonly errorMessage = signal('');
  readonly attempts = signal<UnfinishedAttempt[]>([]);

  ngOnInit(): void {
    this.loadAttempts();
  }

  trackByAttemptId(_: number, attempt: UnfinishedAttempt): number {
    return attempt.attempt_id;
  }

  answeredLabel(attempt: UnfinishedAttempt): string {
    return `${attempt.answered_questions} / ${attempt.total_questions}`;
  }

  timeLimitLabel(attempt: UnfinishedAttempt): string {
    return attempt.time_limit ? `${attempt.time_limit} мин.` : 'Без лимита';
  }

  private loadAttempts(): void {
    this.isLoading.set(true);
    this.errorMessage.set('');

    this.learningService.getUnfinishedAttempts().subscribe({
      next: (attempts) => {
        this.attempts.set(attempts);
        this.isLoading.set(false);
      },
      error: (error: HttpErrorResponse) => {
        this.errorMessage.set(error.error?.detail || 'Не удалось загрузить незавершённые попытки.');
        this.isLoading.set(false);
      }
    });
  }
}
