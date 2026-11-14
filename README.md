# Запуск проекта

## Требования

- Установленный `Docker`
- Установленный `Docker Compose`

## Запуск

1. При необходимости создайте `.env` на основе `.env.example`.
2. Из корня проекта выполните:

```powershell
docker compose up --build -d
```

При запуске backend автоматически применяет Alembic-миграции, загружает demo seed в пустую БД
и создаёт начальный аналитический read-model.

## Доступные сервисы

- Frontend: `http://localhost:4200`
- Backend API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- PostgreSQL: `localhost:5432`
- Health: `http://localhost:8000/health/ready`
- Prometheus metrics: `http://localhost:8000/metrics`

## Проверки backend

```powershell
pip install -r requirements-dev.txt
pytest --cov=analytics --cov=backend.services
ruff check backend analytics tests
```

Полный пересчёт аналитического read-model:

```powershell
docker compose exec backend python -m backend.rebuild_analytics
```

Экспорт признаков для будущего offline ML-контура:

```powershell
docker compose exec backend python -m backend.ml_features --output /tmp/ml_features.csv
```

Архитектурное решение по ETL и условия перехода к Kafka описаны в `docs/etl-architecture.md`.

## Нагрузочный профиль Medium

Загрузить в PostgreSQL воспроизводимый набор из 5 000 студентов, 20 курсов по
информационной безопасности, 500 000 попыток и 2 млн событий:

```powershell
docker compose exec backend python -m backend.generate_load_dataset
docker compose exec backend python -m backend.rebuild_analytics
node scripts/mixed_load_test.mjs
```

При повторной генерации используйте `--replace`. Сводка фактического прогона находится в
`docs/load-testing-medium.md`, предметная структура курсов — в
`docs/cybersecurity-curriculum.md`, ML-стратегия рекомендаций — в
`docs/ml-recommendation-strategy.md`.

## Полезные команды

Проверить статус контейнеров:

```powershell
docker compose ps
```

Остановить проект:

```powershell
docker compose down
```

Остановить проект и удалить volume с данными PostgreSQL:

```powershell
docker compose down -v
```
