import { Routes } from '@angular/router';
import { authGuard, guestGuard } from './core/guards/auth.guard';
import { AnalyticsPageComponent } from './features/analytics/analytics-page.component';
import { UnfinishedAttemptsPageComponent } from './features/attempts/unfinished-attempts-page.component';
import { LoginPageComponent } from './features/auth/login-page.component';
import { RegisterPageComponent } from './features/auth/register-page.component';
import { CourseAccessPageComponent } from './features/course-access/course-access-page.component';
import { CoursePageComponent } from './features/course/course-page.component';
import { CoursesPageComponent } from './features/courses/courses-page.component';
import { DashboardPageComponent } from './features/dashboard/dashboard-page.component';
import { LessonPageComponent } from './features/lesson/lesson-page.component';
import { ModulePageComponent } from './features/module/module-page.component';
import { ProfilePageComponent } from './features/profile/profile-page.component';
import { RecommendationsPageComponent } from './features/recommendations/recommendations-page.component';
import { TaskPageComponent } from './features/task/task-page.component';
import { TestAttemptPageComponent } from './features/test-attempt/test-attempt-page.component';
import { TestAttemptResultPageComponent } from './features/test-attempt-result/test-attempt-result-page.component';
import { TestPageComponent } from './features/test/test-page.component';

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
    path: 'courses/:courseId',
    component: CoursePageComponent,
    canActivate: [authGuard]
  },
  {
    path: 'courses/:courseId/manage',
    component: CourseAccessPageComponent,
    canActivate: [authGuard]
  },
  {
    path: 'modules/:moduleId',
    component: ModulePageComponent,
    canActivate: [authGuard]
  },
  {
    path: 'lessons/:lessonId',
    component: LessonPageComponent,
    canActivate: [authGuard]
  },
  {
    path: 'tasks/:taskId',
    component: TaskPageComponent,
    canActivate: [authGuard]
  },
  {
    path: 'tests/:testId',
    component: TestPageComponent,
    canActivate: [authGuard]
  },
  {
    path: 'tests/:testId/attempt/:attemptId/result',
    component: TestAttemptResultPageComponent,
    canActivate: [authGuard]
  },
  {
    path: 'tests/:testId/attempt/:attemptId',
    component: TestAttemptPageComponent,
    canActivate: [authGuard]
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
    path: 'attempts',
    component: UnfinishedAttemptsPageComponent,
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
