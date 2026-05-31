import { Component, computed, inject, OnInit } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { AuthService } from './core/services/auth.service';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App implements OnInit {
  readonly authService = inject(AuthService);
  readonly profileLabel = computed(() => {
    const user = this.authService.currentUser();
    return user?.first_name?.trim() || user?.username || 'Профиль';
  });
  readonly profileInitials = computed(() => {
    const user = this.authService.currentUser();

    if (!user) {
      return 'U';
    }

    const initials = `${user.first_name?.[0] || ''}${user.last_name?.[0] || ''}`.trim();
    return initials || user.username.slice(0, 2).toUpperCase();
  });

  ngOnInit(): void {
    this.authService.initialize().subscribe({
      error: () => {
        // Invalid token should not break app bootstrap; session is cleared in service.
      }
    });
  }
}
