import { Routes } from '@angular/router';
import { authGuard, guestGuard } from './core/guards/auth.guard';
import { AnalyticsPageComponent } from './features/analytics/analytics-page.component';
import { LoginPageComponent } from './features/auth/login-page.component';
import { RegisterPageComponent } from './features/auth/register-page.component';
import { CoursesPageComponent } from './features/courses/courses-page.component';
import { DashboardPageComponent } from './features/dashboard/dashboard-page.component';
import { ProfilePageComponent } from './features/profile/profile-page.component';
import { RecommendationsPageComponent } from './features/recommendations/recommendations-page.component';

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
    path: 'courses',
    component: CoursesPageComponent
  },
  {
    path: 'recommendations',
    component: RecommendationsPageComponent,
    canActivate: [authGuard]
  },
  {
    path: 'analytics',
    component: AnalyticsPageComponent,
    canActivate: [authGuard]
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
