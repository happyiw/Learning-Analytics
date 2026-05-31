import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, OnInit, signal } from '@angular/core';
import {
  AnalyticsDynamicsPoint,
  PersonalAnalyticsSnapshot,
  TopicResult
} from '../../core/models/dashboard.models';
import { AnalyticsService } from '../../core/services/analytics.service';

interface ChartPoint {
  x: number;
  y: number;
  label: string;
  value: number;
}

@Component({
  selector: 'app-analytics-page',
  imports: [CommonModule],
  templateUrl: './analytics-page.component.html',
  styleUrl: './analytics-page.component.css'
})
export class AnalyticsPageComponent implements OnInit {
  private readonly analyticsService = inject(AnalyticsService);

  readonly isLoading = signal(false);
  readonly errorMessage = signal('');
  readonly snapshot = signal<PersonalAnalyticsSnapshot | null>(null);

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
    this.loadAnalytics();
  }

  trackByModuleId(_: number, item: TopicResult): number {
    return item.module_id;
  }

  private loadAnalytics(): void {
    this.isLoading.set(true);
    this.errorMessage.set('');

    this.analyticsService.getSnapshot().subscribe({
      next: (snapshot) => {
        this.snapshot.set(snapshot);
        this.isLoading.set(false);
      },
      error: (error: HttpErrorResponse) => {
        this.errorMessage.set(error.error?.detail || 'Не удалось загрузить персональную аналитику.');
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
