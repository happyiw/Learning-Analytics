import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-register-page',
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './register-page.component.html',
  styleUrl: './auth-pages.css'
})
export class RegisterPageComponent {
  private readonly formBuilder = inject(FormBuilder);
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);
  readonly courseYearOptions = [1, 2, 3, 4, 5, 6];

  readonly isSubmitting = signal(false);
  readonly errorMessage = signal('');
  readonly form = this.formBuilder.group({
    username: ['', [Validators.required]],
    password: ['', [Validators.required, Validators.minLength(6)]],
    email: ['', [Validators.email]],
    first_name: [''],
    last_name: [''],
    university: [''],
    group: [''],
    course_year: [null as number | null, [Validators.min(1), Validators.max(6)]]
  });

  submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    this.isSubmitting.set(true);
    this.errorMessage.set('');

    const rawValue = this.form.getRawValue();

    this.authService
      .register({
        username: rawValue.username?.trim() || '',
        password: rawValue.password?.trim() || '',
        email: this.normalizeText(rawValue.email),
        first_name: this.normalizeText(rawValue.first_name),
        last_name: this.normalizeText(rawValue.last_name),
        university: this.normalizeText(rawValue.university),
        group: this.normalizeText(rawValue.group),
        course_year: rawValue.course_year ?? null
      })
      .subscribe({
        next: () => {
          this.isSubmitting.set(false);
          void this.router.navigateByUrl('/');
        },
        error: (error: HttpErrorResponse) => {
          this.isSubmitting.set(false);
          this.errorMessage.set(
            error.error?.detail || 'Не удалось зарегистрироваться. Попробуйте ещё раз.'
          );
        }
      });
  }

  private normalizeText(value: string | null | undefined): string | null {
    const trimmedValue = value?.trim();
    return trimmedValue ? trimmedValue : null;
  }
}
