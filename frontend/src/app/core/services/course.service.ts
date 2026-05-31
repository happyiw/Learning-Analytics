import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { CourseCard } from '../models/dashboard.models';

@Injectable({
  providedIn: 'root'
})
export class CourseService {
  private readonly http = inject(HttpClient);

  getCourses(): Observable<CourseCard[]> {
    return this.http.get<CourseCard[]>('/api/courses/');
  }
}
