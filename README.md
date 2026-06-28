# Payment Processing Service

Асинхронный микросервис для обработки платежей.

## Стек

- FastAPI + Pydantic v2
- SQLAlchemy 2.0 (async)
- PostgreSQL
- RabbitMQ
- FastStream
- Alembic
- Docker

## Архитектура

```
POST /api/v1/payments → API (outbox) → RabbitMQ → Consumer → Webhook
```

1. **API** создаёт платеж и запись в outbox (в одной транзакции)
2. **Outbox Publisher** (фоновый процесс в API) читает outbox и публикует события в RabbitMQ
3. **Consumer** (FastStream) получает событие, эмулирует обработку (2-5 сек, 90% успех), обновляет статус и отправляет webhook

## Запуск

```bash
docker compose up --build
```

Сервис будет доступен на `http://localhost:8000`.

## Миграции

Применяются автоматически при старте через скрипт (или вручную):

```bash
docker compose exec api alembic upgrade head
```

## API

### Создание платежа

```bash
curl -X POST http://localhost:8000/api/v1/payments \
  -H "X-API-Key: secret-key-123" \
  -H "Idempotency-Key: unique-key-123" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 100.50,
    "currency": "USD",
    "description": "Test payment",
    "webhook_url": "https://webhook.site/your-webhook"
  }'
```

### Получение платежа

```bash
curl http://localhost:8000/api/v1/payments/{payment_id} \
  -H "X-API-Key: secret-key-123"
```
