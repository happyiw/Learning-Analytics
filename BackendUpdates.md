# Backend Updates

## Version `1.3.0`

## Main Changes

- Added open and closed course mode through `Course.is_open`
- Added course enrollment model `CourseEnrollment`
- Added self-enrollment endpoint for open courses
- Added teacher/admin endpoints for assigning students to closed courses
- Added student search endpoint for course access management
- Added backend access checks for course, module, lesson, task and test content
- Added standalone analytics module [analytics/progress_service.py](analytics/progress_service.py)
- Connected `build_progress(...)` to the new `ProgressService`
- Updated intro course and intro test defaults:
  - course is open
  - test has unlimited timer
  - test has one attempt
  - passing score is `0`
  - all answer options in the intro test are marked correct

## New / Updated Models

### `Course`

- `difficulty: int` in range `1..10`
- `is_published: bool`
- `is_open: bool`
- `created_at: datetime`
- `updated_at: datetime`

### `CourseEnrollment`

- `id: int`
- `user_id: int`
- `course_id: int`
- `assigned_by_id: int | None`
- `created_at: datetime`

### `ProgressService`

Location:

- [analytics/progress_service.py](analytics/progress_service.py)

Responsibilities:

- get overall user progress
- calculate completed lessons percentage
- calculate completed modules percentage
- calculate progress for a specific course
- calculate progress for a specific module
- limit global progress scopes to courses available to the current user

## API Changes

### Courses

- `GET /api/courses/`
- `GET /api/courses/my/enrollments/`
- `POST /api/courses/{course_id}/enroll/my/`
- `GET /api/courses/{course_id}/enrollments/`
- `POST /api/courses/{course_id}/enrollments/`
- `GET /api/courses/students/search/`

### Access Rules

- published open course:
  - student can self-enroll
  - after enrollment student can access course content
- published closed course:
  - student cannot self-enroll
  - `teacher` or `admin` can assign student manually
- `teacher` and `admin` can access course content directly

### Analytics

- Existing progress endpoints now use the dedicated `ProgressService`
- Global progress and related analytics are scoped to courses available to the user

## SQLite Bootstrap Notes

On startup backend keeps synchronizing `app.db`:

- adds missing `courses.is_open`
- keeps `Course.difficulty` in numeric format
- updates timestamps where needed
- keeps intro course and intro test in the current format

## Current Dependencies

- `fastapi>=0.115,<1.0`
- `uvicorn>=0.30,<1.0`
- `sqlalchemy>=2.0,<3.0`
- `PyJWT>=2.8,<3.0`
