import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, HostListener, computed, inject, OnDestroy, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { EMPTY, Observable, forkJoin } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { PublicQuestion, TestItem } from '../../core/models/learning.models';
import { AuthService } from '../../core/services/auth.service';
import { LearningService } from '../../core/services/learning.service';

interface AnswerDraft {
  selected_option_id: number | null;
  text_answer: string;
}

@Component({
  selector: 'app-test-attempt-page',
  imports: [CommonModule, FormsModule],
  templateUrl: './test-attempt-page.component.html',
  styleUrl: './test-attempt-page.component.css'
})
export class TestAttemptPageComponent implements OnInit, OnDestroy {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly learningService = inject(LearningService);
  private readonly authService = inject(AuthService);
  private intervalId: ReturnType<typeof setInterval> | null = null;
  private autosaveTimeoutId: ReturnType<typeof setTimeout> | null = null;

  readonly isLoading = signal(false);
  readonly isSaving = signal(false);
  readonly isFinishing = signal(false);
  readonly errorMessage = signal('');
  readonly saveMessage = signal('');
  readonly unansweredWarning = signal('');
  readonly test = signal<TestItem | null>(null);
  readonly attemptStartedAt = signal<string | null>(null);
  readonly questions = signal<PublicQuestion[]>([]);
  readonly currentQuestionIndex = signal(0);
  readonly timeLeftSeconds = signal<number | null>(null);
  readonly answers = signal<Record<number, AnswerDraft>>({});

  readonly testId = computed(() => Number(this.route.snapshot.paramMap.get('testId')));
  readonly attemptId = computed(() => Number(this.route.snapshot.paramMap.get('attemptId')));
  readonly currentQuestion = computed(() => this.questions()[this.currentQuestionIndex()] || null);
  readonly questionProgress = computed(
    () => `${this.currentQuestionIndex() + 1} / ${Math.max(1, this.questions().length)}`
  );

  ngOnInit(): void {
    this.loadAttempt();
  }

  ngOnDestroy(): void {
    this.flushAutosave();
    this.clearTimer();
  }

  @HostListener('window:beforeunload')
  handleBeforeUnload(): void {
    this.persistCurrentDraftWithKeepalive();
  }

  goBack(): void {
    void this.router.navigate(['/tests', this.testId()]);
  }

  previousQuestion(): void {
    this.flushAutosave();
    this.currentQuestionIndex.update((value) => Math.max(0, value - 1));
  }

  nextQuestion(): void {
    this.flushAutosave();
    this.currentQuestionIndex.update((value) => Math.min(this.questions().length - 1, value + 1));
  }

  updateSelectedOption(questionId: number, optionId: number): void {
    this.answers.update((drafts) => ({
      ...drafts,
      [questionId]: {
        selected_option_id: optionId,
        text_answer: drafts[questionId]?.text_answer || ''
      }
    }));
    this.scheduleAutosave(questionId);
  }

  updateTextAnswer(questionId: number, value: string): void {
    this.answers.update((drafts) => ({
      ...drafts,
      [questionId]: {
        selected_option_id: drafts[questionId]?.selected_option_id ?? null,
        text_answer: value
      }
    }));
    this.scheduleAutosave(questionId);
  }

  getDraft(questionId: number): AnswerDraft {
    return this.answers()[questionId] || { selected_option_id: null, text_answer: '' };
  }

  saveCurrentAnswer(): void {
    const question = this.currentQuestion();
    if (!question) {
      return;
    }

    if (!this.hasDraftValue(question.id)) {
      this.saveMessage.set('Сначала заполните ответ.');
      return;
    }

    this.isSaving.set(true);
    this.saveMessage.set('');

    this.persistDraft(question.id).subscribe({
      next: () => {
        this.saveMessage.set('Ответ сохранён.');
        this.isSaving.set(false);
      },
      error: (error: HttpErrorResponse) => {
        this.errorMessage.set(error.error?.detail || 'Не удалось сохранить ответ.');
        this.isSaving.set(false);
      }
    });
  }

  finishTest(): void {
    const unanswered = this.questions().filter((question) => {
      const draft = this.getDraft(question.id);
      return !draft.selected_option_id && !draft.text_answer.trim();
    });

    this.unansweredWarning.set(
      unanswered.length ? `Есть незаполненные вопросы: ${unanswered.length}.` : ''
    );

    this.flushAutosave();
    this.isFinishing.set(true);
    this.learningService.finishAttempt(this.attemptId()).subscribe({
      next: () => {
        this.isFinishing.set(false);
        void this.router.navigate(['/tests', this.testId()]);
      },
      error: (error: HttpErrorResponse) => {
        this.errorMessage.set(error.error?.detail || 'Не удалось завершить тест.');
        this.isFinishing.set(false);
      }
    });
  }

  formatTime(seconds: number | null): string {
    if (seconds === null) {
      return 'Без лимита';
    }

    const minutes = Math.floor(seconds / 60);
    const restSeconds = seconds % 60;
    return `${String(minutes).padStart(2, '0')}:${String(restSeconds).padStart(2, '0')}`;
  }

  private loadAttempt(): void {
    const testId = this.testId();
    if (!testId || !this.attemptId()) {
      this.errorMessage.set('Попытка теста не найдена.');
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set('');

    forkJoin({
      test: this.learningService.getTest(testId),
      questions: this.learningService.getTestQuestions(testId),
      result: this.learningService.getAttemptResult(this.attemptId())
    }).subscribe({
      next: ({ test, questions, result }) => {
        this.test.set(test);
        this.attemptStartedAt.set(result.attempt.started_at);
        this.questions.set(questions);
        this.answers.set(
          result.answers.reduce<Record<number, AnswerDraft>>((accumulator, answer) => {
            accumulator[answer.question_id] = {
              selected_option_id: answer.selected_option_id,
              text_answer: answer.text_answer || ''
            };
            return accumulator;
          }, {})
        );
        this.startTimer(test.time_limit, result.attempt.started_at);
        this.isLoading.set(false);
      },
      error: (error: HttpErrorResponse) => {
        this.errorMessage.set(error.error?.detail || 'Не удалось загрузить попытку теста.');
        this.isLoading.set(false);
      }
    });
  }

  private startTimer(timeLimitMinutes: number | null, startedAt: string | null): void {
    this.clearTimer();

    if (!timeLimitMinutes) {
      this.timeLeftSeconds.set(null);
      return;
    }

    const totalSeconds = timeLimitMinutes * 60;
    const startedAtTimestamp = this.parseBackendDate(startedAt);
    const elapsedSeconds = startedAtTimestamp
      ? Math.max(0, Math.floor((Date.now() - startedAtTimestamp) / 1000))
      : 0;
    const remainingSeconds = Math.max(0, totalSeconds - elapsedSeconds);

    this.timeLeftSeconds.set(remainingSeconds);
    if (remainingSeconds <= 0) {
      this.finishTest();
      return;
    }

    this.intervalId = setInterval(() => {
      const nextValue = (this.timeLeftSeconds() || 0) - 1;
      this.timeLeftSeconds.set(nextValue);

      if (nextValue <= 0) {
        this.clearTimer();
        this.finishTest();
      }
    }, 1000);
  }

  private clearTimer(): void {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
  }

  private hasDraftValue(questionId: number): boolean {
    const draft = this.getDraft(questionId);
    return !!draft.selected_option_id || !!draft.text_answer.trim();
  }

  private persistDraft(questionId: number): Observable<unknown> {
    const draft = this.getDraft(questionId);
    return this.learningService.saveAnswer(this.attemptId(), {
      question_id: questionId,
      selected_option_id: draft.selected_option_id,
      text_answer: draft.text_answer || null
    });
  }

  private scheduleAutosave(questionId: number): void {
    if (!this.hasDraftValue(questionId)) {
      return;
    }

    if (this.autosaveTimeoutId) {
      clearTimeout(this.autosaveTimeoutId);
    }

    this.autosaveTimeoutId = setTimeout(() => {
      this.persistDraft(questionId)
        .pipe(catchError(() => EMPTY))
        .subscribe(() => {
          this.saveMessage.set('Черновик ответа сохранён.');
        });
      this.autosaveTimeoutId = null;
    }, 800);
  }

  private flushAutosave(): void {
    if (this.autosaveTimeoutId) {
      clearTimeout(this.autosaveTimeoutId);
      this.autosaveTimeoutId = null;
    }

    const question = this.currentQuestion();
    if (!question || !this.hasDraftValue(question.id)) {
      return;
    }

    this.persistDraft(question.id)
      .pipe(catchError(() => EMPTY))
      .subscribe();
  }

  private persistCurrentDraftWithKeepalive(): void {
    const question = this.currentQuestion();
    const token = this.authService.getAccessToken();
    if (!question || !token || !this.hasDraftValue(question.id)) {
      return;
    }

    const draft = this.getDraft(question.id);
    void fetch(`/api/test-attempts/${this.attemptId()}/answers/`, {
      method: 'POST',
      keepalive: true,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify({
        question_id: question.id,
        selected_option_id: draft.selected_option_id,
        text_answer: draft.text_answer || null
      })
    });
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
