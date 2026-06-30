import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { AnalyticsDynamicsPoint, PersonalRecommendation, TopicResult } from '../../core/models/dashboard.models';
import { TeacherStudentDetail, TeacherStudentSummary } from '../../core/models/teacher.models';
import { TeacherService } from '../../core/services/teacher.service';
import {
  translateLearningStateLabel,
  translateReasonCodeLabel,
  translateRecommendationPriorityLabel,
  translateRiskLevelLabel,
  translateTrendLabel
} from '../../core/utils/analytics-labels';

interface ChartPoint {
  x: number;
  y: number;
  label: string;
  value: number;
}

@Component({
  selector: 'app-teacher-student-detail-page',
  imports: [CommonModule, RouterLink],
  templateUrl: './teacher-student-detail-page.component.html',
  styleUrls: ['../analytics/analytics-page.component.css', './teacher-student-detail-page.component.css']
})
export class TeacherStudentDetailPageComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly teacherService = inject(TeacherService);

  readonly isLoading = signal(false);
  readonly errorMessage = signal('');
  readonly detail = signal<TeacherStudentDetail | null>(null);
  readonly courseId = signal<number | null>(null);
  readonly studentId = signal<number | null>(null);

  readonly student = computed<TeacherStudentSummary | null>(() => this.detail()?.summary ?? null);
  readonly snapshot = computed(() => this.detail()?.snapshot ?? null);
  readonly recommendations = computed<PersonalRecommendation[]>(() => this.detail()?.recommendations ?? []);

  readonly chartPoints = computed<ChartPoint[]>(() => this.buildChartPoints(this.snapshot()?.dynamics || []));
  readonly chartPolyline = computed(() =>
    this.chartPoints()
      .map((point) => `${point.x},${point.y}`)
      .join(' ')
  );
  readonly bestAverageResult = computed(() => {
    const topicResults = this.snapshot()?.topicResults || [];
    return topicResults.length ? Math.max(...topicResults.map((item) => item.best_percentage)) : 0;
  });

  ngOnInit(): void {
    const courseId = Number(this.route.snapshot.paramMap.get('courseId'));
    const studentId = Number(this.route.snapshot.paramMap.get('studentId'));

    if (!courseId || !studentId) {
      this.errorMessage.set('Не удалось определить курс или студента.');
      return;
    }

    this.courseId.set(courseId);
    this.studentId.set(studentId);
    this.loadStudentDetail(courseId, studentId);
  }

  fullName(item: { first_name: string | null; last_name: string | null; username: string }): string {
    const value = [item.first_name, item.last_name].filter(Boolean).join(' ').trim();
    return value || item.username;
  }

  trackByModuleId(_: number, item: TopicResult): number {
    return item.module_id;
  }

  trackByRecommendationId(_: number, item: PersonalRecommendation): number {
    return item.id;
  }

  translateTrend(value: string): string {
    return translateTrendLabel(value);
  }

  translateRiskLevel(value: string | null): string {
    return translateRiskLevelLabel(value);
  }

  translateLearningState(value: string | null): string {
    return translateLearningStateLabel(value);
  }

  translatePriority(value: string | null | undefined): string {
    return translateRecommendationPriorityLabel(value);
  }

  translateReason(reason: string | null | undefined, reasonCode: string | null | undefined): string {
    return reason || translateReasonCodeLabel(reasonCode);
  }

  private loadStudentDetail(courseId: number, studentId: number): void {
    this.isLoading.set(true);
    this.errorMessage.set('');

    this.teacherService.getStudentDetail(courseId, studentId).subscribe({
      next: (detail) => {
        this.detail.set(detail);
        this.isLoading.set(false);
      },
      error: (error: HttpErrorResponse) => {
        this.errorMessage.set(
          error.error?.detail || 'Не удалось загрузить аналитику и рекомендации по студенту.'
        );
        this.isLoading.set(false);
      }
    });
  }

  private buildChartPoints(dynamics: AnalyticsDynamicsPoint[]): ChartPoint[] {
    if (!dynamics.length) {
      return [];
    }

    const sorted = [...dynamics].sort((left, right) => left.date.localeCompare(right.date));

    return sorted.map((item, index) => {
      const x = sorted.length === 1 ? 280 : 24 + (index * 512) / (sorted.length - 1);
      const y = 184 - Math.min(100, Math.max(0, item.percentage)) * 1.5;

      return {
        x,
        y,
        label: new Date(item.date).toLocaleDateString('ru-RU'),
        value: item.percentage
      };
    });
  }
}
