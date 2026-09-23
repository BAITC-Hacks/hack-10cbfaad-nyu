# Module 3 — Web + Cart

Next.js-приложение с чатом EKT AI, карточками товаров, загрузкой вложений и подтверждением предложения добавить товар в корзину. Подробный запуск Product Service, AI Service и Gemini API описан в [основном README](../README.md).

## Установка и запуск

Сначала запустите Product Service и AI Service и настройте ключ модели в `ai-service/.env`. Затем в каталоге `web`:

```powershell
if (-not (Test-Path .env.local)) { Copy-Item .env.example .env.local }
npm ci
npm run dev
```

Приложение будет доступно по адресу `http://localhost:3000`. Для локального запуска в `.env.local` используйте `AI_SERVICE_URL=http://127.0.0.1:8002` и `PRODUCT_SERVICE_URL=http://127.0.0.1:8001`. `INTERNAL_SERVICE_TOKEN` должен совпадать с токеном Product Service.

Проверка production-сборки:

```powershell
npm run lint
npm run build
```

## Подключение AI Service

При заданном `AI_SERVICE_URL` серверный маршрут проксирует сообщения в `POST /internal/v1/chat/messages` с `Authorization` и `X-Request-ID`. AI Service обращается к настроенному API модели и Product Service; ключ модели хранится в `ai-service/.env`, а не в браузере.

Вложения передаются через `POST /api/v1/files` в AI Service. Поддерживаются PDF, XLSX, DOCX и JPEG размером до 15 MiB.

## Подтверждение корзины

Подтверждение вызывает `POST /api/v1/cart/proposals/{proposal_id}/confirm` с UUID v4 в `Idempotency-Key`. При `CART_ADAPTER_MODE=live` перед подтверждением запрашивается актуальный остаток в Product Service.

Внешний Cart API ekt.kz пока не подключён: подтверждение не изменяет реальную корзину. Повтор того же `Idempotency-Key` возвращает сохранённый результат. Предложения привязаны к cookie-сессии и действуют 15 минут.

## Переменные окружения

Локальный образец находится в `.env.example`. Секреты в репозиторий не добавляются.

- `AI_SERVICE_URL` — адрес AI Service.
- `PRODUCT_SERVICE_URL` — адрес Product Service для проверки наличия.
- `INTERNAL_SERVICE_TOKEN` — внутренний bearer token.
- `CART_PROPOSAL_TTL_SECONDS` — срок действия предложения, по умолчанию 900 секунд.
- `CART_ADAPTER_MODE=live` — проверка наличия через Product Service.
- `EKT_CART_URL` — ссылка на страницу корзины, возвращаемая текущим адаптером.

Для подключения реальной корзины требуется реализовать вызов Cart API ekt.kz в `lib/server/cart-adapter.ts` после получения его контракта и способа авторизации.

Текущий контракт чата использует обычный JSON-ответ без потоковой выдачи.
