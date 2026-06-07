import { CommonModule, Location } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, DestroyRef, inject, OnInit, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { DomSanitizer, SafeResourceUrl, SafeUrl } from '@angular/platform-browser';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { LessonContentBlock, LessonDetail } from '../../core/models/learning.models';
import { LearningService } from '../../core/services/learning.service';

@Component({
  selector: 'app-lesson-page',
  imports: [CommonModule, RouterLink],
  templateUrl: './lesson-page.component.html',
  styleUrl: './lesson-page.component.css'
})
export class LessonPageComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly learningService = inject(LearningService);
  private readonly location = inject(Location);
  private readonly router = inject(Router);
  private readonly sanitizer = inject(DomSanitizer);
  private readonly destroyRef = inject(DestroyRef);

  readonly isLoading = signal(false);
  readonly isCompleting = signal(false);
  readonly errorMessage = signal('');
  readonly lesson = signal<LessonDetail | null>(null);
  readonly lessonId = signal<number | null>(null);
  readonly hasNextLesson = computed(() => !!this.lesson()?.next_lesson_id);
  readonly actionLabel = computed(() => {
    const lesson = this.lesson();
    if (!lesson) {
      return 'Завершить';
    }
    if (this.isCompleting()) {
      return lesson.next_lesson_id ? 'Переходим...' : 'Сохраняем...';
    }
    if (lesson.next_lesson_id) {
      return 'Далее';
    }
    return lesson.is_completed ? 'Урок завершен' : 'Завершить';
  });
  readonly safeVideoUrl = computed<SafeResourceUrl | null>(() => {
    const url = this.lesson()?.video_url;
    return url ? this.sanitizer.bypassSecurityTrustResourceUrl(url) : null;
  });

  ngOnInit(): void {
    this.route.paramMap
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((params) => {
        const lessonId = Number(params.get('lessonId'));
        this.lessonId.set(Number.isFinite(lessonId) && lessonId > 0 ? lessonId : null);
        this.loadLesson();
      });
  }

  goBack(): void {
    this.location.back();
  }

  trackByBlock(index: number): number {
    return index;
  }

  markCompleted(): void {
    const lesson = this.lesson();
    if (!lesson) {
      return;
    }

    if (lesson.is_completed) {
      this.navigateAfterCompletion(lesson);
      return;
    }

    this.isCompleting.set(true);
    this.learningService.completeLesson(lesson.id).subscribe({
      next: (result) => {
        const updatedLesson = { ...lesson, is_completed: result.is_completed };
        this.lesson.set(updatedLesson);
        this.isCompleting.set(false);
        this.navigateAfterCompletion(updatedLesson);
      },
      error: (error: HttpErrorResponse) => {
        this.errorMessage.set(error.error?.detail || 'Не удалось завершить урок.');
        this.isCompleting.set(false);
      }
    });
  }

  chartMax(block: LessonContentBlock): number {
    return Math.max(...block.values, 1);
  }

  chartBarWidth(block: LessonContentBlock, value: number): string {
    return `${Math.max(12, Math.round((value / this.chartMax(block)) * 100))}%`;
  }

  safeImageUrl(url: string | null): SafeUrl | null {
    return url ? this.sanitizer.bypassSecurityTrustUrl(url) : null;
  }

  private loadLesson(): void {
    const lessonId = this.lessonId();
    if (!lessonId) {
      this.lesson.set(null);
      this.errorMessage.set('Урок не найден.');
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set('');
    this.lesson.set(null);
    this.learningService.getLesson(lessonId).subscribe({
      next: (lesson) => {
        this.lesson.set(lesson);
        this.isLoading.set(false);
      },
      error: (error: HttpErrorResponse) => {
        this.errorMessage.set(error.error?.detail || 'Не удалось загрузить урок.');
        this.isLoading.set(false);
      }
    });
  }

  private navigateAfterCompletion(lesson: LessonDetail): void {
    if (lesson.next_lesson_id) {
      void this.router.navigate(['/lessons', lesson.next_lesson_id]);
      return;
    }

    void this.router.navigate(['/modules', lesson.module_id]);
  }
}
