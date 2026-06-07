import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { forkJoin } from 'rxjs';
import {
  AttemptQuestionResultView,
  AttemptResult,
  PublicQuestion,
  TestAttempt,
  TestItem,
  UserAnswer
} from '../../core/models/learning.models';
import { LearningService } from '../../core/services/learning.service';

@Component({
  selector: 'app-test-attempt-result-page',
  imports: [CommonModule],
  templateUrl: './test-attempt-result-page.component.html',
  styleUrl: './test-attempt-result-page.component.css'
})
export class TestAttemptResultPageComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly learningService = inject(LearningService);

  readonly isLoading = signal(false);
  readonly errorMessage = signal('');
  readonly test = signal<TestItem | null>(null);
  readonly result = signal<AttemptResult | null>(null);
  readonly questionResults = signal<AttemptQuestionResultView[]>([]);

  readonly testId = computed(() => Number(this.route.snapshot.paramMap.get('testId')));
  readonly attemptId = computed(() => Number(this.route.snapshot.paramMap.get('attemptId')));
  readonly attempt = computed<TestAttempt | null>(() => this.result()?.attempt || null);
  readonly isPassed = computed(() => !!this.attempt()?.is_passed);
  readonly finishedAtLabel = computed(() => this.formatDateTime(this.attempt()?.finished_at || null));
  readonly durationLabel = computed(() => this.formatDuration(this.attempt()));

  ngOnInit(): void {
    this.loadResultPage();
  }

  trackByQuestionId(_: number, item: AttemptQuestionResultView): number {
    return item.question_id;
  }

  openRecommendations(): void {
    void this.router.navigate(['/recommendations']);
  }

  goToModule(): void {
    const moduleId = this.test()?.module_id;
    if (moduleId) {
      void this.router.navigate(['/modules', moduleId]);
      return;
    }

    void this.router.navigate(['/tests', this.testId()]);
  }

  private loadResultPage(): void {
    const testId = this.testId();
    const attemptId = this.attemptId();
    if (!testId || !attemptId) {
      this.errorMessage.set('Результат попытки не найден.');
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set('');

    forkJoin({
      test: this.learningService.getTest(testId),
      questions: this.learningService.getTestQuestions(testId),
      result: this.learningService.getAttemptResult(attemptId)
    }).subscribe({
      next: ({ test, questions, result }) => {
        this.test.set(test);
        this.result.set(result);
        this.questionResults.set(this.buildQuestionResults(questions, result.answers));
        this.isLoading.set(false);
      },
      error: (error: HttpErrorResponse) => {
        this.errorMessage.set(error.error?.detail || 'Не удалось загрузить результат попытки.');
        this.isLoading.set(false);
      }
    });
  }

  private buildQuestionResults(
    questions: PublicQuestion[],
    answers: UserAnswer[]
  ): AttemptQuestionResultView[] {
    const answerMap = new Map<number, UserAnswer>(answers.map((answer) => [answer.question_id, answer]));

    return [...questions]
      .sort((left, right) => left.order - right.order || left.id - right.id)
      .map((question) => {
        const answer = answerMap.get(question.id);
        return {
          question_id: question.id,
          question_text: question.text,
          question_type: question.question_type,
          max_score: question.score,
          user_answer: this.resolveUserAnswer(question, answer),
          is_correct: !!answer?.is_correct,
          score_received: answer?.score_received || 0
        };
      });
  }

  private resolveUserAnswer(question: PublicQuestion, answer: UserAnswer | undefined): string {
    if (!answer) {
      return 'Ответ не дан';
    }

    if (answer.text_answer?.trim()) {
      return answer.text_answer.trim();
    }

    const selectedOptionIds = answer.selected_option_ids?.length
      ? answer.selected_option_ids
      : answer.selected_option_id !== null
        ? [answer.selected_option_id]
        : [];
    if (selectedOptionIds.length) {
      const optionTexts = selectedOptionIds
        .map((selectedOptionId) => question.answer_options.find((item) => item.id === selectedOptionId)?.text)
        .filter((value): value is string => !!value);
      if (optionTexts.length) {
        return optionTexts.join(', ');
      }

      return selectedOptionIds.length > 1
        ? 'Выбрано несколько вариантов ответа'
        : 'Выбран вариант ответа';
    }

    return 'Ответ не дан';
  }

  private formatDateTime(value: string | null): string {
    const timestamp = this.parseBackendDate(value);
    if (timestamp === null) {
      return 'Не завершено';
    }

    return new Date(timestamp).toLocaleString('ru-RU');
  }

  private formatDuration(attempt: TestAttempt | null): string {
    if (!attempt?.finished_at) {
      return 'Не завершено';
    }

    const startedAt = this.parseBackendDate(attempt.started_at);
    const finishedAt = this.parseBackendDate(attempt.finished_at);
    if (startedAt === null || finishedAt === null) {
      return 'Нет данных';
    }

    const totalSeconds = Math.max(0, Math.floor((finishedAt - startedAt) / 1000));
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;

    if (hours > 0) {
      return `${hours} ч ${minutes} мин ${seconds} с`;
    }
    if (minutes > 0) {
      return `${minutes} мин ${seconds} с`;
    }

    return `${seconds} с`;
  }

  private parseBackendDate(value: string | null): number | null {
    if (!value) {
      return null;
    }

    const normalized = value.includes('T') ? value : value.replace(' ', 'T');
    const hasTimezone = /[zZ]|[+-]\d{2}:\d{2}$/.test(normalized);
    const timestamp = Date.parse(hasTimezone ? normalized : `${normalized}Z`);
    return Number.isNaN(timestamp) ? null : timestamp;
  }
}
