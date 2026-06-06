# Learning Analytics Platform

## Version

- Backend: `1.3.0`
- Frontend: `1.3.0`

## Current Features

- FastAPI backend with JWT authentication and roles: `student`, `teacher`, `admin`
- Angular frontend with dashboard, profile, courses, analytics, recommendations, lessons, tasks, and tests
- Structured lessons with `content_blocks`: text sections, callouts, checklists, tables, charts, stat cards, and images
- Open and closed published courses
- Self-enrollment for open courses
- Manual student assignment to closed courses for `teacher` and `admin`
- Personal analytics with progress, topic results, recommendations, test dynamics, and per-test attempt analytics
- Dedicated analytics module in `analytics/`:
  - [analytics/progress_service.py](analytics/progress_service.py)
  - [analytics/test_analytics_service.py](analytics/test_analytics_service.py)
  - [analytics/topic_result_service.py](analytics/topic_result_service.py)
- Test analytics tracks completion percentage, attempts count, best result, average result, last result, completion time, and status
- Topic results are aggregated per module and persisted in `topic_results`
- SQLite bootstrap on backend startup for schema synchronization and intro course updates

## Project Structure

- `backend/` - FastAPI app, API routers, models, schemas, bootstrap, and backend services
- `frontend/` - Angular application
- `analytics/` - reusable analytics services imported by the backend
- `app.db` - main SQLite database
- `requirements.txt` - backend dependencies
- `BackendUpdates.md` - backend change log and API notes

## Dependencies

### Backend

- `fastapi>=0.115,<1.0`
- `uvicorn>=0.30,<1.0`
- `sqlalchemy>=2.0,<3.0`
- `PyJWT>=2.8,<3.0`

No additional dependencies are required for the analytics integration.

### Frontend

- `@angular/common ^21.2.0`
- `@angular/compiler ^21.2.0`
- `@angular/core ^21.2.0`
- `@angular/forms ^21.2.0`
- `@angular/platform-browser ^21.2.0`
- `@angular/router ^21.2.0`
- `rxjs ~7.8.0`
- `tslib ^2.3.0`

## Run Backend

```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

API docs:

- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/redoc`

## Run Frontend

```powershell
cd frontend
npm install
npm start
```

Frontend URL:

- `http://localhost:4200`

## Run Analytics Module Separately

The analytics helpers are plain Python modules and can be imported independently inside backend services or scripts. The current backend already imports them for progress, test analytics, and aggregated topic results.

Examples:

```powershell
python -c "from analytics.progress_service import ProgressService; print(ProgressService)"
python -c "from analytics.test_analytics_service import TestAnalyticsService; print(TestAnalyticsService)"
python -c "from analytics.topic_result_service import TopicResultService; print(TopicResultService)"
```

## Analytics API Notes

- `GET /api/tests/{test_id}/analytics/my/` returns test attempt analytics for the current user
- `GET /api/topic-results/my/` returns aggregated topic results across accessible modules
- `GET /api/courses/{course_id}/topic-results/my/` returns aggregated topic results for one course
- `GET /api/modules/{module_id}/topic-results/my/` returns aggregated topic results for one module

## Database Notes

- Backend uses the root `app.db`
- On backend startup the application:
  - creates missing tables
  - adds missing SQLite columns for the current version
  - syncs the intro course and intro test settings
- The intro course is open for enrollment
- The intro test has:
  - unlimited timer
  - one attempt
  - passing score `0`
  - only correct answer options
