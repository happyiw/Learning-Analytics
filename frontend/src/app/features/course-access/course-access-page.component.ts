import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';
import { CourseCard } from '../../core/models/dashboard.models';
import { CourseEnrollment, StudentDirectoryItem } from '../../core/models/course.models';
import { AuthService } from '../../core/services/auth.service';
import { CourseService } from '../../core/services/course.service';
import { LearningService } from '../../core/services/learning.service';

@Component({
  selector: 'app-course-access-page',
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './course-access-page.component.html',
  styleUrl: './course-access-page.component.css'
})
export class CourseAccessPageComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly courseService = inject(CourseService);
  private readonly learningService = inject(LearningService);
  private readonly authService = inject(AuthService);

  readonly isLoading = signal(false);
  readonly isSaving = signal<number | null>(null);
  readonly errorMessage = signal('');
  readonly successMessage = signal('');
  readonly searchQuery = signal('');
  readonly course = signal<CourseCard | null>(null);
  readonly enrollments = signal<CourseEnrollment[]>([]);
  readonly students = signal<StudentDirectoryItem[]>([]);
  readonly courseId = computed(() => Number(this.route.snapshot.paramMap.get('courseId')));
  readonly canManage = computed(() => {
    const role = this.authService.currentUser()?.role;
    return role === 'teacher' || role === 'admin';
  });
  readonly availableStudents = computed(() => {
    const enrolledIds = new Set(this.enrollments().map((item) => item.user_id));
    return this.students().filter((student) => !enrolledIds.has(student.id));
  });

  ngOnInit(): void {
    if (!this.canManage()) {
      this.errorMessage.set('Доступ к управлению курсом есть только у преподавателя или администратора.');
      return;
    }

    this.loadPage();
  }

  fullName(item: { first_name: string | null; last_name: string | null; username: string }): string {
    const fullName = [item.first_name, item.last_name].filter(Boolean).join(' ').trim();
    return fullName || item.username;
  }

  goBack(): void {
    void this.router.navigate(['/courses']);
  }

  searchStudents(): void {
    if (!this.canManage()) {
      return;
    }

    this.errorMessage.set('');
    this.courseService.searchStudents(this.searchQuery()).subscribe({
      next: (students) => {
        this.students.set(students);
      },
      error: (error: HttpErrorResponse) => {
        this.errorMessage.set(error.error?.detail || 'Не удалось загрузить список студентов.');
      }
    });
  }

  addStudent(student: StudentDirectoryItem): void {
    if (!this.course()) {
      return;
    }

    this.isSaving.set(student.id);
    this.errorMessage.set('');
    this.successMessage.set('');

    this.courseService.addStudentToCourse(this.courseId(), student.id).subscribe({
      next: (enrollment) => {
        this.enrollments.update((items) => [...items, enrollment]);
        this.students.update((items) => items.filter((item) => item.id !== student.id));
        this.isSaving.set(null);
        this.successMessage.set(`Студент ${this.fullName(student)} добавлен на курс.`);
      },
      error: (error: HttpErrorResponse) => {
        this.errorMessage.set(error.error?.detail || 'Не удалось добавить студента на курс.');
        this.isSaving.set(null);
      }
    });
  }

  private loadPage(): void {
    const courseId = this.courseId();
    if (!courseId) {
      this.errorMessage.set('Курс не найден.');
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set('');
    this.successMessage.set('');

    forkJoin({
      course: this.learningService.getCourse(courseId),
      enrollments: this.courseService.getCourseEnrollments(courseId),
      students: this.courseService.searchStudents('')
    }).subscribe({
      next: ({ course, enrollments, students }) => {
        this.course.set(course);
        this.enrollments.set(enrollments);
        this.students.set(students);
        this.isLoading.set(false);
      },
      error: (error: HttpErrorResponse) => {
        this.errorMessage.set(error.error?.detail || 'Не удалось открыть управление доступом к курсу.');
        this.isLoading.set(false);
      }
    });
  }
}
