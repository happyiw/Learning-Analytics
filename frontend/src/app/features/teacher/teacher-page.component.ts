import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { TeacherService } from '../../core/services/teacher.service';
import { CourseCard } from '../../core/models/dashboard.models';
import {
  TeacherCourseDashboard,
  TeacherGroupSummary,
  TeacherStudentSummary,
  TopicResultAggregate
} from '../../core/models/teacher.models';

@Component({
  selector: 'app-teacher-page',
  imports: [CommonModule, FormsModule],
  templateUrl: './teacher-page.component.html',
  styleUrl: './teacher-page.component.css'
})
export class TeacherPageComponent implements OnInit {
  private readonly authService = inject(AuthService);
  private readonly teacherService = inject(TeacherService);
  private readonly router = inject(Router);

  readonly currentUser = this.authService.currentUser;
  readonly courses = signal<CourseCard[]>([]);
  readonly dashboard = signal<TeacherCourseDashboard | null>(null);
  readonly selectedCourseId = signal<number | null>(null);
  readonly selectedGroupId = signal<string>('__all__');
  readonly groupTopicResults = signal<TopicResultAggregate[]>([]);
  readonly isLoadingCourses = signal(false);
  readonly isLoadingDashboard = signal(false);
  readonly isLoadingGroup = signal(false);
  readonly errorMessage = signal('');
  readonly allGroupsValue = '__all__';

  readonly canViewTeacherPanel = computed(() => {
    const role = this.currentUser()?.role;
    return role === 'teacher' || role === 'admin';
  });

  readonly selectedGroup = computed<TeacherGroupSummary | null>(() => {
    const groupId = this.selectedGroupId();
    if (groupId === this.allGroupsValue) {
      return null;
    }

    return this.dashboard()?.groups.find((item) => item.group_id === groupId) ?? null;
  });

  readonly filteredStudents = computed<TeacherStudentSummary[]>(() => {
    const students = this.dashboard()?.students || [];
    const groupId = this.selectedGroupId();
    if (groupId === this.allGroupsValue) {
      return students;
    }

    return students.filter((item) => item.group === groupId);
  });

  readonly displayedGroupResults = computed<TopicResultAggregate[]>(() => {
    const scoped = this.groupTopicResults();
    if (scoped.length) {
      return scoped;
    }

    return this.dashboard()?.module_topic_results || [];
  });

  ngOnInit(): void {
    if (!this.canViewTeacherPanel()) {
      this.errorMessage.set('Панель преподавателя доступна только преподавателям и администраторам.');
      return;
    }

    this.loadCourses();
  }

  fullName(item: { first_name: string | null; last_name: string | null; username: string }): string {
    const value = [item.first_name, item.last_name].filter(Boolean).join(' ').trim();
    return value || item.username;
  }

  selectCourse(courseId: number | null): void {
    if (!courseId) {
      return;
    }

    this.selectedCourseId.set(courseId);
    this.loadDashboard(courseId);
  }

  selectGroup(groupId: string | null): void {
    const normalizedGroupId = groupId || this.allGroupsValue;
    const courseId = this.selectedCourseId();
    this.selectedGroupId.set(normalizedGroupId);

    if (!courseId || normalizedGroupId === this.allGroupsValue) {
      this.groupTopicResults.set([]);
      return;
    }

    this.isLoadingGroup.set(true);
    this.teacherService.getGroupTopicResults(courseId, normalizedGroupId).subscribe({
      next: (results) => {
        this.groupTopicResults.set(results);
        this.isLoadingGroup.set(false);
      },
      error: (error: HttpErrorResponse) => {
        this.errorMessage.set(error.error?.detail || 'Не удалось загрузить аналитику по группе.');
        this.groupTopicResults.set([]);
        this.isLoadingGroup.set(false);
      }
    });
  }

  openStudent(studentId: number): void {
    const courseId = this.selectedCourseId();
    if (!courseId) {
      return;
    }

    void this.router.navigate(['/teacher', 'courses', courseId, 'students', studentId]);
  }

  trackByStudentId(_: number, item: TeacherStudentSummary): number {
    return item.id;
  }

  trackByGroupId(_: number, item: TeacherGroupSummary): string {
    return item.group_id;
  }

  trackByModuleId(_: number, item: TopicResultAggregate): number {
    return item.module_id;
  }

  private loadCourses(): void {
    this.isLoadingCourses.set(true);
    this.errorMessage.set('');

    this.teacherService.listCourses().subscribe({
      next: (courses) => {
        this.courses.set(courses);
        this.isLoadingCourses.set(false);

        if (!courses.length) {
          return;
        }

        const selected = this.selectedCourseId() && courses.some((item) => item.id === this.selectedCourseId())
          ? this.selectedCourseId()
          : courses[0].id;
        this.selectedCourseId.set(selected);
        if (selected) {
          this.loadDashboard(selected);
        }
      },
      error: (error: HttpErrorResponse) => {
        this.errorMessage.set(error.error?.detail || 'Не удалось загрузить список курсов.');
        this.isLoadingCourses.set(false);
      }
    });
  }

  private loadDashboard(courseId: number): void {
    this.isLoadingDashboard.set(true);
    this.errorMessage.set('');
    this.groupTopicResults.set([]);

    this.teacherService.getCourseDashboard(courseId).subscribe({
      next: (dashboard) => {
        this.dashboard.set(dashboard);
        this.isLoadingDashboard.set(false);

        const groupId = this.selectedGroupId();
        const nextGroup =
          groupId === this.allGroupsValue || dashboard.groups.some((item) => item.group_id === groupId)
            ? groupId
            : this.allGroupsValue;
        this.selectGroup(nextGroup);
      },
      error: (error: HttpErrorResponse) => {
        this.errorMessage.set(error.error?.detail || 'Не удалось загрузить сводку преподавателя.');
        this.dashboard.set(null);
        this.isLoadingDashboard.set(false);
      }
    });
  }
}
