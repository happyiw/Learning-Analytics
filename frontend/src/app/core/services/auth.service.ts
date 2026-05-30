import { inject, Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of, switchMap, tap, throwError, catchError } from 'rxjs';
import {
  LoginPayload,
  RegisterPayload,
  TokenResponse,
  UserProfile
} from '../models/auth.models';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly tokenStorageKey = 'access_token';
  private readonly accessToken = signal<string | null>(this.readStoredToken());

  readonly currentUser = signal<UserProfile | null>(null);
  readonly isAuthenticated = signal<boolean>(this.accessToken() !== null);

  initialize(): Observable<UserProfile | null> {
    if (!this.accessToken()) {
      this.currentUser.set(null);
      this.isAuthenticated.set(false);
      return of(null);
    }

    return this.fetchCurrentUser().pipe(
      catchError((error) => {
        this.clearSession();
        return throwError(() => error);
      })
    );
  }

  login(payload: LoginPayload): Observable<UserProfile> {
    return this.http.post<TokenResponse>('/api/auth/login/', payload).pipe(
      tap(({ access_token }) => this.storeToken(access_token)),
      switchMap(() => this.fetchCurrentUser())
    );
  }

  register(payload: RegisterPayload): Observable<UserProfile> {
    return this.http.post<UserProfile>('/api/auth/register/', payload).pipe(
      switchMap(() =>
        this.login({
          username: payload.username,
          password: payload.password
        })
      )
    );
  }

  fetchCurrentUser(): Observable<UserProfile> {
    return this.http.get<UserProfile>('/api/auth/me/').pipe(
      tap((user) => {
        this.currentUser.set(user);
        this.isAuthenticated.set(true);
      })
    );
  }

  logout(): void {
    this.clearSession();
  }

  getAccessToken(): string | null {
    return this.accessToken();
  }

  private storeToken(token: string): void {
    localStorage.setItem(this.tokenStorageKey, token);
    this.accessToken.set(token);
    this.isAuthenticated.set(true);
  }

  private clearSession(): void {
    localStorage.removeItem(this.tokenStorageKey);
    this.accessToken.set(null);
    this.currentUser.set(null);
    this.isAuthenticated.set(false);
  }

  private readStoredToken(): string | null {
    return localStorage.getItem(this.tokenStorageKey);
  }
}
