import { Routes } from '@angular/router';
import { authGuard, guestGuard } from './core/guards/auth.guard';
import { LoginPageComponent } from './features/auth/login-page.component';
import { RegisterPageComponent } from './features/auth/register-page.component';
import { DashboardPageComponent } from './features/dashboard/dashboard-page.component';
import { ProfilePageComponent } from './features/profile/profile-page.component';

export const routes: Routes = [
  {
    path: '',
    component: DashboardPageComponent
  },
  {
    path: 'dashboard',
    component: DashboardPageComponent
  },
  {
    path: 'login',
    component: LoginPageComponent,
    canActivate: [guestGuard]
  },
  {
    path: 'register',
    component: RegisterPageComponent,
    canActivate: [guestGuard]
  },
  {
    path: 'profile',
    component: ProfilePageComponent,
    canActivate: [authGuard]
  },
  {
    path: '**',
    redirectTo: '/'
  }
];
