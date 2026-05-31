import { CommonModule, Location } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { LessonDetail } from '../../core/models/learning.models';
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

  readonly isLoading = signal(false);
  readonly isCompleting = signal(false);
  readonly errorMessage = signal('');
  readonly lesson = signal<LessonDetail | null>(null);
  readonly lessonId = computed(() => Number(this.route.snapshot.paramMap.get('lessonId')));
  readonly safeVideoUrl = computed<SafeResourceUrl | null>(() => {
    const url = this.lesson()?.video_url;
    return url ? this.sanitizer.bypassSecurityTrustResourceUrl(url) : null;
  });

  ngOnInit(): void {
    this.loadLesson();
  }

  goBack(): void {
    this.location.back();
  }

  markCompleted(): void {
    const lesson = this.lesson();
    if (!lesson || lesson.is_completed) {
      return;
    }

    this.isCompleting.set(true);
    this.learningService.completeLesson(lesson.id).subscribe({
      next: (result) => {
        this.lesson.set({ ...lesson, is_completed: result.is_completed });
        this.isCompleting.set(false);
        void this.router.navigate(['/modules', lesson.module_id]);
      },
      error: (error: HttpErrorResponse) => {
        this.errorMessage.set(error.error?.detail || 'Не удалось завершить урок.');
        this.isCompleting.set(false);
      }
    });
  }

  private loadLesson(): void {
    const lessonId = this.lessonId();
    if (!lessonId) {
      this.errorMessage.set('Урок не найден.');
      return;
    }

    this.isLoading.set(true);
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
}
