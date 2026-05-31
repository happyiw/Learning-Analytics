import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { DashboardService } from '../../core/services/dashboard.service';
import { DashboardSnapshot } from '../../core/models/dashboard.models';

@Component({
  selector: 'app-dashboard-page',
  imports: [CommonModule, RouterLink],
  templateUrl: './dashboard-page.component.html',
  styleUrl: './dashboard-page.component.css'
})
export class DashboardPageComponent implements OnInit {
  private readonly authService = inject(AuthService);
  private readonly dashboardService = inject(DashboardService);

  readonly isAuthenticated = this.authService.isAuthenticated;
  readonly currentUser = this.authService.currentUser;
  readonly isLoading = signal(false);
  readonly errorMessage = signal('');
  readonly snapshot = signal<DashboardSnapshot | null>(null);

  readonly greetingName = computed(() => {
    const user = this.currentUser();

    if (!user) {
      return 'студент';
    }

    return user.first_name?.trim() || user.username;
  });

  readonly completionRate = computed(() => {
    const progress = this.snapshot()?.progress;
    return progress ? Math.round(progress.completion_rate) : 0;
  });

  ngOnInit(): void {
    if (!this.isAuthenticated()) {
      return;
    }

    this.loadDashboard();
  }

  private loadDashboard(): void {
    this.isLoading.set(true);
    this.errorMessage.set('');

    this.dashboardService.getSnapshot().subscribe({
      next: (snapshot) => {
        this.snapshot.set(snapshot);
        this.isLoading.set(false);
      },
      error: (error: HttpErrorResponse) => {
        this.isLoading.set(false);
        this.errorMessage.set(
          error.error?.detail || 'Не удалось загрузить сводку по обучению.'
        );
      }
    });
  }
}
