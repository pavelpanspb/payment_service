# Payment Processing Service

Асинхронный микросервис для обработки платежей.

## Стек

- FastAPI + Pydantic v2
- SQLAlchemy 2.0 (async)
- PostgreSQL
- RabbitMQ (FastStream + aio-pika)
- Alembic
- Docker

## Архитектура

```
POST /api/v1/payments
        │
        ▼
   ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
   │   API    │────▶│  Outbox  │────▶│ RabbitMQ │────▶│Consumer  │────▶ Webhook
   │ (router) │     │ Publisher│     │          │     │(FastStream)│
   └──────────┘     └──────────┘     └──────────┘     └──────────┘
        │                                                │
        ▼                                                ▼
   ┌──────────┐                                     ┌──────────┐
   │PostgreSQL│                                     │PostgreSQL│
   │ payments + │                                    │ payments │
   │ outbox   │                                     │ status   │
   └──────────┘                                     └──────────┘
```

### Слои

| Слой | Описание |
|------|----------|
| `router.py` | Тонкие эндпоинты, вызывают сервис |
| `services/payment.py` | Бизнес-логика: создание платежа + outbox |
| `services/webhook.py` | Отправка вебхуков с retry |
| `repositories/payment.py` | Работа с таблицей `payments` |
| `repositories/outbox.py` | Работа с таблицей `outbox` (с `FOR UPDATE SKIP LOCKED`) |
| `unit_of_work.py` | Централизованное управление транзакцией |

### Ключевые решения

- **Idempotency**: `INSERT ... ON CONFLICT DO NOTHING` — атомарная защита от дублей
- **Outbox Publisher**: постоянное соединение с RabbitMQ, `SELECT ... FOR UPDATE SKIP LOCKED` для безопасной параллельной работы
- **Webhook retry**: persist-счётчик попыток в `payments.webhook_retry_count`
- **DLQ**: `x-dead-letter-exchange: payments.dlx` + очередь `payments.dead`

## Запуск

```bash
docker compose up --build
```

Сервис будет доступен на `http://localhost:8000`.

Миграции применяются автоматически через `entrypoint.sh`.

## API

### Создание платежа

```bash
curl -X POST http://localhost:8000/api/v1/payments \
  -H "X-API-Key: secret-key-123" \
  -H "Idempotency-Key: unique-key-456" \
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

## Переменные окружения

| Переменная | Значение по умолчанию |
|------------|----------------------|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/payments` |
| `RABBITMQ_URL` | `amqp://guest:guest@localhost:5672/` |
| `API_KEY` | `secret-key-123` |
| `OUTBOX_POLL_INTERVAL` | `1.0` |
| `OUTBOX_BATCH_SIZE` | `50` |
