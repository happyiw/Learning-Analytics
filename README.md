# Learning Analytics Platform

## Version

- Backend: `1.4.0`
- Frontend: `1.4.0`

## What Changed

The backend schema was simplified to remove duplicated analytical fields.

- `topic_results` is now a lightweight cache with `id`, `user_id`, `module_id`, `last_attempt_at`, and `updated_at`
- `test_attempts` keeps only factual attempt data: `id`, `user_id`, `test_id`, `started_at`, `finished_at`, `score`, `max_score`
- `recommendations` no longer stores `trigger_score_threshold`; recommendation rules now live in `RecommendationService`
- `lessons` no longer stores a legacy `content` column; lesson text is derived from `content_blocks`
- `tasks` now keeps only `id`, `module_id`, `title`, `description`, `max_score`, and `order`

## Current Behavior

- `TopicResultService` calculates `attempts_count`, `average_percentage`, `best_percentage`, and `weakness_level` directly from finished `test_attempts`
- `RecommendationService` decides what to show from rule-based logic such as low average score, repeated failed attempts, and unfinished lessons
- `TestAnalyticsService` builds `percentage`, `is_passed`, and `status` in DTO responses instead of reading stored columns
- `ProgressService` counts progress only from enrollments, completed lessons, finished attempts, and passing rules

## Project Structure

- `backend/` - FastAPI app, ORM models, schemas, routers, bootstrap migrations
- `analytics/` - shared analytics services used by the backend
- `frontend/` - Angular application
- `data/` - seed JSON files aligned with the reduced schema
- `postman/` - API collection updated to the current contracts
- `app.db` - SQLite database

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

## Database Notes

- SQLite schema cleanup runs on backend startup in `backend/bootstrap.py`
- Existing databases are rebuilt in place for the affected tables so removed columns are physically dropped
- Legacy lesson plain text is migrated into `content_blocks` before the `lessons.content` column is removed

## Analytics Notes

- Topic analytics are aggregated per module from finished attempts
- Passing is computed from `score / max_score * 100 >= tests.passing_score`
- Recommendation rows store only content; selection rules are implemented in code
- Public lesson responses still include a summary `content` field, but it is derived from `content_blocks` and not stored in the database
