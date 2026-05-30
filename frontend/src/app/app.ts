import { Component, inject, OnInit } from '@angular/core';
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

  ngOnInit(): void {
    this.authService.initialize().subscribe({
      error: () => {
        // Invalid token should not break app bootstrap; session is cleared in service.
      }
    });
  }
}
