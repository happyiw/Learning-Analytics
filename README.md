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

## Доступные сервисы

- Frontend: `http://localhost:4200`
- Backend API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- PostgreSQL: `localhost:5432`

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
