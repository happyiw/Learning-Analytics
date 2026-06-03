import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { CourseCard } from '../models/dashboard.models';
import { CourseEnrollment, EnrolledCourse, StudentDirectoryItem } from '../models/course.models';

@Injectable({
  providedIn: 'root'
})
export class CourseService {
  private readonly http = inject(HttpClient);

  getCourses(): Observable<CourseCard[]> {
    return this.http.get<CourseCard[]>('/api/courses/');
  }

  getMyEnrollments(): Observable<EnrolledCourse[]> {
    return this.http.get<EnrolledCourse[]>('/api/courses/my/enrollments/');
  }

  enrollMyself(courseId: number): Observable<CourseEnrollment> {
    return this.http.post<CourseEnrollment>(`/api/courses/${courseId}/enroll/my/`, {});
  }

  getCourseEnrollments(courseId: number): Observable<CourseEnrollment[]> {
    return this.http.get<CourseEnrollment[]>(`/api/courses/${courseId}/enrollments/`);
  }

  searchStudents(query: string): Observable<StudentDirectoryItem[]> {
    const encodedQuery = encodeURIComponent(query.trim());
    return this.http.get<StudentDirectoryItem[]>(`/api/courses/students/search/?q=${encodedQuery}`);
  }

  addStudentToCourse(courseId: number, userId: number): Observable<CourseEnrollment> {
    return this.http.post<CourseEnrollment>(`/api/courses/${courseId}/enrollments/`, {
      user_id: userId
    });
  }
}
