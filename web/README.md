# Module 3 — Web + Cart

Это отдельное Next.js-приложение Module 3 из `ARCHITECTURE.md`: чат EKT AI, карточки товаров, вложения и безопасное подтверждение добавления в корзину.

## Установка и запуск

```bash
npm install
npm run dev
```

Приложение будет доступно по адресу `http://localhost:3000`.

Проверка production-сборки:

```bash
npm run lint
npm run build
```

## Mock AI

При `AI_SERVICE_MODE=mock` browser API использует локальный mock (это режим по умолчанию). Обычный запрос показывает товар `515291`; сообщение `добавь 2` создаёт action `PROPOSE_CART_ADD`, не изменяя корзину напрямую.

При `AI_SERVICE_MODE=real` и заданном `AI_SERVICE_URL` Module 3 проксирует запрос во внутренний `POST /internal/v1/chat/messages` с `Authorization` и `X-Request-ID`. Browser по-прежнему вызывает только `/api/v1/chat/messages`.

## Mock Cart

Подтверждение вызывает только `POST /api/v1/cart/proposals/{proposal_id}/confirm` с UUID v4 в `Idempotency-Key`. Перед mock-добавлением выполняется mock live availability check. `MockEktCartAdapter` возвращает `/mock-cart` или значение `EKT_CART_URL`.

Повтор того же `Idempotency-Key` возвращает сохранённый результат и не выполняет добавление повторно. Pending proposals принадлежат cookie-сессии и действуют 15 минут.

## Environment variables

Скопируйте `.env.example` в `.env.local` при необходимости. Реальные credentials и secrets в репозиторий не добавляются.

- `AI_SERVICE_MODE` — `mock` по умолчанию или `real` для внутреннего AI Service.
- `AI_SERVICE_URL` — внутренний AI Service; используется только в режиме `real`.
- `PRODUCT_SERVICE_URL` — внутренний Product Service для будущего live availability.
- `INTERNAL_SERVICE_TOKEN` — внутренний bearer token.
- `CART_PROPOSAL_TTL_SECONDS` — TTL proposal, по умолчанию 900.
- `CART_ADAPTER_MODE` — в MVP используется `mock`.
- `EKT_CART_URL` — URL корзины после подтверждённой интеграции; mock использует `/mock-cart`.

## Что пока mock

- AI Service, если `AI_SERVICE_URL` не задан.
- Product Service availability при `CART_ADAPTER_MODE=mock`.
- EKT Cart API: реальный endpoint, cookies/token и semantics в архитектуре требуют проверки.

## Что заменить после получения реальных API

Достаточно подключить реальный вызов в `lib/server/cart-adapter.ts` и live availability в `lib/server/availability.ts`. Browser endpoints, UI, proposal flow и idempotency-контракт менять не нужно.

Streaming/SSE намеренно не реализован: базовый контракт `v1` использует обычный JSON response, как указано в архитектуре.
