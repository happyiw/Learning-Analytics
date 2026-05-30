import { HttpErrorResponse } from '@angular/common/http';
import { DatePipe } from '@angular/common';
import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-profile-page',
  imports: [DatePipe],
  templateUrl: './profile-page.component.html',
  styleUrl: './profile-page.component.css'
})
export class ProfilePageComponent implements OnInit {
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);

  readonly isLoading = signal(false);
  readonly errorMessage = signal('');
  readonly user = this.authService.currentUser;
  readonly fullName = computed(() => {
    const currentUser = this.user();
    if (!currentUser) {
      return 'Пользователь';
    }

    return [currentUser.last_name, currentUser.first_name].filter(Boolean).join(' ') || 'Не указано';
  });

  ngOnInit(): void {
    if (this.user()) {
      return;
    }

    this.isLoading.set(true);
    this.authService.fetchCurrentUser().subscribe({
      next: () => this.isLoading.set(false),
      error: (error: HttpErrorResponse) => {
        this.isLoading.set(false);
        this.errorMessage.set(
          error.error?.detail || 'Не удалось загрузить профиль. Войдите снова.'
        );
        this.authService.logout();
        void this.router.navigateByUrl('/login');
      }
    });
  }

  logout(): void {
    this.authService.logout();
    void this.router.navigateByUrl('/login');
  }
}
