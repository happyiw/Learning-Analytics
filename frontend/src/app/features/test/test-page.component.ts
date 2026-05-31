import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { EMPTY, forkJoin, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { TestAttempt, TestItem } from '../../core/models/learning.models';
import { LearningService } from '../../core/services/learning.service';

@Component({
  selector: 'app-test-page',
  imports: [CommonModule, RouterLink],
  templateUrl: './test-page.component.html',
  styleUrl: './test-page.component.css'
})
export class TestPageComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly learningService = inject(LearningService);

  readonly isLoading = signal(false);
  readonly isStarting = signal(false);
  readonly errorMessage = signal('');
  readonly attemptsExhausted = signal(false);
  readonly test = signal<TestItem | null>(null);
  readonly activeAttempt = signal<TestAttempt | null>(null);
  readonly testId = computed(() => Number(this.route.snapshot.paramMap.get('testId')));
  readonly startButtonLabel = computed(() =>
    this.activeAttempt() ? 'Продолжить тест' : 'Начать тест'
  );

  ngOnInit(): void {
    this.loadTest();
  }

  goBack(): void {
    const moduleId = this.test()?.module_id;
    if (moduleId) {
      void this.router.navigate(['/modules', moduleId]);
      return;
    }
    void this.router.navigate(['/courses']);
  }

  startTest(): void {
    const test = this.test();
    if (!test || this.isStarting()) {
      return;
    }

    const activeAttempt = this.activeAttempt();
    if (activeAttempt) {
      void this.router.navigate(['/tests', test.id, 'attempt', activeAttempt.id]);
      return;
    }

    this.isStarting.set(true);
    this.errorMessage.set('');
    this.learningService.startTest(test.id).subscribe({
      next: (attempt) => {
        this.activeAttempt.set(attempt);
        this.isStarting.set(false);
        void this.router.navigate(['/tests', test.id, 'attempt', attempt.id]);
      },
      error: (error: HttpErrorResponse) => {
        const detail = error.error?.detail || 'Не удалось начать тест.';
        this.errorMessage.set(detail);
        this.attemptsExhausted.set(detail.includes('No attempts left'));
        this.isStarting.set(false);
      }
    });
  }

  private loadTest(): void {
    const testId = this.testId();
    if (!testId) {
      this.errorMessage.set('Тест не найден.');
      return;
    }

    this.isLoading.set(true);
    forkJoin({
      test: this.learningService.getTest(testId),
      activeAttempt: this.learningService.getActiveTestAttempt(testId).pipe(
        catchError(() => of(null))
      )
    }).subscribe({
      next: ({ test, activeAttempt }) => {
        this.test.set(test);
        this.activeAttempt.set(activeAttempt);
        this.isLoading.set(false);
      },
      error: (error: HttpErrorResponse) => {
        this.errorMessage.set(error.error?.detail || 'Не удалось загрузить тест.');
        this.isLoading.set(false);
      }
    });
  }
}
