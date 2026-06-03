import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, forkJoin, of } from 'rxjs';
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
  private readonly router = inject(Router);
  readonly authService = inject(AuthService);

  readonly isLoading = signal(false);
  readonly isEnrolling = signal<Record<number, boolean>>({});
  readonly errorMessage = signal('');
  readonly infoMessage = signal('');
  readonly courses = signal<CourseCard[]>([]);
  readonly enrolledCourseIds = signal<number[]>([]);
  readonly currentRole = computed(() => this.authService.currentUser()?.role ?? null);
  readonly isPrivilegedUser = computed(
    () => this.currentRole() === 'teacher' || this.currentRole() === 'admin'
  );

  ngOnInit(): void {
    this.loadCourses();
  }

  trackByCourseId(_: number, course: CourseCard): number {
    return course.id;
  }

  difficultyLabel(course: CourseCard): string {
    return `${course.difficulty}/10`;
  }

  isEnrolled(courseId: number): boolean {
    return this.enrolledCourseIds().includes(courseId);
  }

  actionLabel(course: CourseCard): string {
    if (this.isPrivilegedUser()) {
      return 'Открыть курс';
    }
    if (this.isEnrolled(course.id)) {
      return 'Продолжить курс';
    }
    if (course.is_open) {
      return 'Пройти курс';
    }
    return this.authService.isAuthenticated() ? 'Доступ по приглашению' : 'Войти, чтобы пройти';
  }

  statusLabel(course: CourseCard): string {
    if (course.is_open) {
      return this.isEnrolled(course.id) ? 'Вы уже записаны' : 'Открытая запись';
    }
    return this.isPrivilegedUser() ? 'Закрытый курс' : 'Доступ через преподавателя';
  }

  progressHint(course: CourseCard): string {
    if (this.isPrivilegedUser()) {
      return course.is_open
        ? 'Откройте курс или управляйте доступом для студентов.'
        : 'Назначьте студентов на курс через управление доступом.';
    }

    if (!this.authService.isAuthenticated()) {
      return 'Войдите в аккаунт, чтобы начать обучение и сохранить прогресс.';
    }

    if (this.isEnrolled(course.id)) {
      return 'Курс уже доступен вам. Можно продолжить обучение с того места, где вы остановились.';
    }

    if (course.is_open) {
      return 'Запишитесь в один клик и сразу переходите к материалам курса.';
    }

    return 'Этот курс открывается преподавателем или администратором.';
  }

  startCourse(course: CourseCard): void {
    this.errorMessage.set('');
    this.infoMessage.set('');

    if (!this.authService.isAuthenticated()) {
      void this.router.navigate(['/login']);
      return;
    }

    if (this.isPrivilegedUser()) {
      void this.router.navigate(['/courses', course.id]);
      return;
    }

    if (this.isEnrolled(course.id)) {
      void this.router.navigate(['/courses', course.id]);
      return;
    }

    if (!course.is_open) {
      this.infoMessage.set('Этот курс пока доступен только по назначению преподавателя или администратора.');
      return;
    }

    this.isEnrolling.update((state) => ({ ...state, [course.id]: true }));
    this.courseService.enrollMyself(course.id).subscribe({
      next: () => {
        this.enrolledCourseIds.update((ids) => (ids.includes(course.id) ? ids : [...ids, course.id]));
        this.isEnrolling.update((state) => ({ ...state, [course.id]: false }));
        void this.router.navigate(['/courses', course.id]);
      },
      error: (error: HttpErrorResponse) => {
        this.errorMessage.set(error.error?.detail || 'Не удалось записаться на курс.');
        this.isEnrolling.update((state) => ({ ...state, [course.id]: false }));
      }
    });
  }

  openManagement(courseId: number): void {
    void this.router.navigate(['/courses', courseId, 'manage']);
  }

  private loadCourses(): void {
    this.isLoading.set(true);
    this.errorMessage.set('');
    this.infoMessage.set('');

    const courses$ = this.courseService.getCourses();
    const enrollments$ = this.authService.isAuthenticated()
      ? this.courseService.getMyEnrollments().pipe(catchError(() => of([])))
      : of([]);

    forkJoin({
      courses: courses$,
      enrollments: enrollments$
    }).subscribe({
      next: ({ courses, enrollments }) => {
        this.courses.set(courses);
        this.enrolledCourseIds.set(enrollments.map((item) => item.course_id));
        this.isLoading.set(false);
      },
      error: (error: HttpErrorResponse) => {
        this.errorMessage.set(error.error?.detail || 'Не удалось загрузить список курсов.');
        this.isLoading.set(false);
      }
    });
  }
}
