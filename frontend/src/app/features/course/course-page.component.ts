import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { CoursePageSnapshot } from '../../core/models/learning.models';
import { LearningService } from '../../core/services/learning.service';

@Component({
  selector: 'app-course-page',
  imports: [CommonModule, RouterLink],
  templateUrl: './course-page.component.html',
  styleUrl: './course-page.component.css'
})
export class CoursePageComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly learningService = inject(LearningService);

  readonly isLoading = signal(false);
  readonly errorMessage = signal('');
  readonly snapshot = signal<CoursePageSnapshot | null>(null);
  readonly courseId = computed(() => Number(this.route.snapshot.paramMap.get('courseId')));

  ngOnInit(): void {
    this.loadCourse();
  }

  goBack(): void {
    void this.router.navigate(['/courses']);
  }

  private loadCourse(): void {
    const courseId = this.courseId();
    if (!courseId) {
      this.errorMessage.set('Курс не найден.');
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set('');

    this.learningService.getCourseSnapshot(courseId).subscribe({
      next: (snapshot) => {
        this.snapshot.set(snapshot);
        this.isLoading.set(false);
      },
      error: (error: HttpErrorResponse) => {
        this.errorMessage.set(error.error?.detail || 'Не удалось загрузить страницу курса.');
        this.isLoading.set(false);
      }
    });
  }
}
