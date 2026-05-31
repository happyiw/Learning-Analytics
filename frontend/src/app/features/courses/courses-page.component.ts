import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, OnInit, signal } from '@angular/core';
import { CourseCard } from '../../core/models/dashboard.models';
import { AuthService } from '../../core/services/auth.service';
import { CourseService } from '../../core/services/course.service';

@Component({
  selector: 'app-courses-page',
  imports: [CommonModule],
  templateUrl: './courses-page.component.html',
  styleUrl: './courses-page.component.css'
})
export class CoursesPageComponent implements OnInit {
  private readonly courseService = inject(CourseService);
  readonly authService = inject(AuthService);

  readonly isLoading = signal(false);
  readonly errorMessage = signal('');
  readonly courses = signal<CourseCard[]>([]);

  ngOnInit(): void {
    this.loadCourses();
  }

  trackByCourseId(_: number, course: CourseCard): number {
    return course.id;
  }

  private loadCourses(): void {
    this.isLoading.set(true);
    this.errorMessage.set('');

    this.courseService.getCourses().subscribe({
      next: (courses) => {
        this.courses.set(courses);
        this.isLoading.set(false);
      },
      error: (error: HttpErrorResponse) => {
        this.errorMessage.set(error.error?.detail || 'Не удалось загрузить список курсов.');
        this.isLoading.set(false);
      }
    });
  }
}
