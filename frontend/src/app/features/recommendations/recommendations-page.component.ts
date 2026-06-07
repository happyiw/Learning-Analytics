import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CourseCard, PersonalRecommendation } from '../../core/models/dashboard.models';
import { ModuleItem } from '../../core/models/learning.models';
import { CourseService } from '../../core/services/course.service';
import { LearningService } from '../../core/services/learning.service';
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
  private readonly courseService = inject(CourseService);
  private readonly learningService = inject(LearningService);

  readonly isLoading = signal(false);
  readonly isFilterLoading = signal(false);
  readonly errorMessage = signal('');
  readonly recommendations = signal<PersonalRecommendation[]>([]);
  readonly courses = signal<CourseCard[]>([]);
  readonly modules = signal<ModuleItem[]>([]);
  readonly selectedCourseId = signal<number | null>(null);
  readonly selectedModuleId = signal<number | null>(null);
  readonly hasSelectedCourse = computed(() => !!this.selectedCourseId());
  readonly hasSelectedModule = computed(() => !!this.selectedModuleId());

  scope: RecommendationScope = 'all';

  ngOnInit(): void {
    this.loadCourses();
    this.loadRecommendations();
  }

  applyScope(scope: RecommendationScope): void {
    this.scope = scope;
    if (scope === 'all') {
      this.selectedCourseId.set(null);
      this.selectedModuleId.set(null);
      this.modules.set([]);
      this.loadRecommendations();
      return;
    }

    if (scope === 'course') {
      this.selectedModuleId.set(null);
    }
  }

  submitFilter(): void {
    this.loadRecommendations();
  }

  trackByRecommendationId(_: number, item: PersonalRecommendation): number {
    return item.id;
  }

  trackByCourseId(_: number, item: CourseCard): number {
    return item.id;
  }

  trackByModuleId(_: number, item: ModuleItem): number {
    return item.id;
  }

  onCourseChange(courseIdValue: number | string | null): void {
    const courseId = Number(courseIdValue);
    const normalizedCourseId = Number.isFinite(courseId) && courseId > 0 ? courseId : null;
    this.selectedCourseId.set(normalizedCourseId);
    this.selectedModuleId.set(null);
    this.modules.set([]);

    if (!normalizedCourseId) {
      return;
    }

    this.loadModules(normalizedCourseId);
  }

  onModuleChange(moduleIdValue: number | string | null): void {
    const moduleId = Number(moduleIdValue);
    this.selectedModuleId.set(Number.isFinite(moduleId) && moduleId > 0 ? moduleId : null);
  }

  private loadCourses(): void {
    this.isFilterLoading.set(true);
    this.courseService.getCourses().subscribe({
      next: (courses) => {
        this.courses.set(courses);
        this.isFilterLoading.set(false);
      },
      error: (error: HttpErrorResponse) => {
        this.errorMessage.set(error.error?.detail || 'Не удалось загрузить список курсов.');
        this.isFilterLoading.set(false);
      }
    });
  }

  private loadModules(courseId: number): void {
    this.isFilterLoading.set(true);
    this.learningService.getCourseModules(courseId).subscribe({
      next: (modules) => {
        this.modules.set(modules);
        this.isFilterLoading.set(false);
      },
      error: (error: HttpErrorResponse) => {
        this.errorMessage.set(error.error?.detail || 'Не удалось загрузить список модулей.');
        this.isFilterLoading.set(false);
      }
    });
  }

  private loadRecommendations(): void {
    this.isLoading.set(true);
    this.errorMessage.set('');

    const scopeId =
      this.scope === 'course'
        ? this.selectedCourseId()
        : this.scope === 'module'
          ? this.selectedModuleId()
          : null;

    this.recommendationService.getRecommendations(this.scope, scopeId).subscribe({
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
