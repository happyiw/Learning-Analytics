import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { LessonItem, ModulePageSnapshot } from '../../core/models/learning.models';
import { LearningService } from '../../core/services/learning.service';

@Component({
  selector: 'app-module-page',
  imports: [CommonModule, RouterLink],
  templateUrl: './module-page.component.html',
  styleUrl: './module-page.component.css'
})
export class ModulePageComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly learningService = inject(LearningService);

  readonly isLoading = signal(false);
  readonly errorMessage = signal('');
  readonly snapshot = signal<ModulePageSnapshot | null>(null);
  readonly moduleId = computed(() => Number(this.route.snapshot.paramMap.get('moduleId')));
  readonly topicResult = computed(() => this.snapshot()?.topicResults[0] || null);

  ngOnInit(): void {
    this.loadModule();
  }

  goBack(): void {
    const courseId = this.snapshot()?.module.course_id;
    if (courseId) {
      void this.router.navigate(['/courses', courseId]);
      return;
    }
    void this.router.navigate(['/courses']);
  }

  lessonPreview(lesson: LessonItem): string {
    const trimmed = lesson.content.trim();
    if (trimmed.length <= 160) {
      return trimmed;
    }
    return `${trimmed.slice(0, 157).trimEnd()}...`;
  }

  private loadModule(): void {
    const moduleId = this.moduleId();
    if (!moduleId) {
      this.errorMessage.set('Модуль не найден.');
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set('');

    this.learningService.getModuleSnapshot(moduleId).subscribe({
      next: (snapshot) => {
        this.snapshot.set(snapshot);
        this.isLoading.set(false);
      },
      error: (error: HttpErrorResponse) => {
        this.errorMessage.set(error.error?.detail || 'Не удалось загрузить страницу модуля.');
        this.isLoading.set(false);
      }
    });
  }
}
