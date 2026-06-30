import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../core/services/auth.service';
import { TeacherService } from '../../core/services/teacher.service';
import { CourseCard, PersonalAnalyticsSnapshot, PersonalRecommendation } from '../../core/models/dashboard.models';
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

  readonly currentUser = this.authService.currentUser;
  readonly courses = signal<CourseCard[]>([]);
  readonly dashboard = signal<TeacherCourseDashboard | null>(null);
  readonly selectedCourseId = signal<number | null>(null);
  readonly selectedGroupId = signal<string | null>(null);
  readonly selectedStudentId = signal<number | null>(null);
  readonly selectedStudentSnapshot = signal<PersonalAnalyticsSnapshot | null>(null);
  readonly selectedStudentRecommendations = signal<PersonalRecommendation[]>([]);
  readonly groupTopicResults = signal<TopicResultAggregate[]>([]);
  readonly isLoadingCourses = signal(false);
  readonly isLoadingDashboard = signal(false);
  readonly isLoadingStudent = signal(false);
  readonly isLoadingGroup = signal(false);
  readonly errorMessage = signal('');
  readonly studentErrorMessage = signal('');

  readonly canViewTeacherPanel = computed(() => {
    const role = this.currentUser()?.role;
    return role === 'teacher' || role === 'admin';
  });

  readonly selectedStudent = computed<TeacherStudentSummary | null>(() => {
    const studentId = this.selectedStudentId();
    const students = this.dashboard()?.students || [];
    return students.find((item) => item.id === studentId) ?? null;
  });

  readonly selectedGroup = computed<TeacherGroupSummary | null>(() => {
    const groupId = this.selectedGroupId();
    const groups = this.dashboard()?.groups || [];
    return groups.find((item) => item.group_id === groupId) ?? null;
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
    const courseId = this.selectedCourseId();
    this.selectedGroupId.set(groupId);

    if (!courseId || !groupId) {
      this.groupTopicResults.set([]);
      return;
    }

    this.isLoadingGroup.set(true);
    this.teacherService.getGroupTopicResults(courseId, groupId).subscribe({
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

  selectStudent(studentId: number | null): void {
    const courseId = this.selectedCourseId();
    this.selectedStudentId.set(studentId);
    this.selectedStudentSnapshot.set(null);
    this.selectedStudentRecommendations.set([]);
    this.studentErrorMessage.set('');

    if (!courseId || !studentId) {
      return;
    }

    this.isLoadingStudent.set(true);
    this.teacherService.getStudentDetail(courseId, studentId).subscribe({
      next: ({ snapshot, recommendations }) => {
        this.selectedStudentSnapshot.set(snapshot);
        this.selectedStudentRecommendations.set(recommendations);
        this.isLoadingStudent.set(false);
      },
      error: (error: HttpErrorResponse) => {
        this.studentErrorMessage.set(
          error.error?.detail || 'Не удалось загрузить аналитику и рекомендации по студенту.'
        );
        this.isLoadingStudent.set(false);
      }
    });
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

  trackByRecommendationId(_: number, item: PersonalRecommendation): number {
    return item.id;
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
    this.selectedStudentSnapshot.set(null);
    this.selectedStudentRecommendations.set([]);
    this.studentErrorMessage.set('');

    this.teacherService.getCourseDashboard(courseId).subscribe({
      next: (dashboard) => {
        this.dashboard.set(dashboard);
        this.isLoadingDashboard.set(false);

        const nextGroup =
          this.selectedGroupId() && dashboard.groups.some((item) => item.group_id === this.selectedGroupId())
            ? this.selectedGroupId()
            : dashboard.groups[0]?.group_id ?? null;
        this.selectGroup(nextGroup);

        const nextStudent =
          this.selectedStudentId() && dashboard.students.some((item) => item.id === this.selectedStudentId())
            ? this.selectedStudentId()
            : dashboard.students[0]?.id ?? null;
        this.selectStudent(nextStudent);
      },
      error: (error: HttpErrorResponse) => {
        this.errorMessage.set(error.error?.detail || 'Не удалось загрузить сводку преподавателя.');
        this.dashboard.set(null);
        this.isLoadingDashboard.set(false);
      }
    });
  }
}
