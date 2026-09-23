# EKT AI — консультант по электротоварам

Хакатонный MVP чат-ассистента для каталога ekt.kz. Пользователь может искать электротовары, смотреть карточки и сведения о наличии, прикладывать спецификации и подтверждать предложение добавить товар в корзину. Проект разделён на веб-приложение, AI Service и Product Service. Для локального просмотра интерфейса предусмотрен режим с демонстрационными данными.

## Состав проекта

| Каталог | Назначение |
| --- | --- |
| `web/` | Интерфейс чата, загрузка файлов, карточки товаров, подтверждение корзины и серверные API-маршруты Next.js. |
| `ai-service/` | Обработка сообщений и вложений, вызов LLM и инструментов поиска товаров. |
| `services/product-service/` | Получение и нормализация каталога ekt.kz, поиск, аналоги, проверка деталей и остатков. |
| `services/product-service/fixtures/` | Один пример товара для локального заполнения каталога без доступа к ekt.kz. |

Поток запросов: браузер → `web` → AI Service → Product Service → PostgreSQL / API ekt.kz. Предложение добавить товар в корзину возвращается в `web` и выполняется только после подтверждения пользователя.

## Технологический стек

| Компонент | Технологии |
| --- | --- |
| Веб-интерфейс и BFF | Node.js 20, Next.js 14.2.15, React 18.3.1, TypeScript 5.7.2, Tailwind CSS 3.4.17 |
| AI Service | Python 3.12, FastAPI, Uvicorn, Pydantic, httpx; OpenAI-совместимый HTTP API для OpenAI/DeepSeek или локальный mock-провайдер |
| Каталог | Python 3.12, FastAPI, SQLAlchemy 2, Pydantic, PostgreSQL 16, psycopg 3, httpx |
| История чата | Redis при заданном `REDIS_URL`; без него — память процесса AI Service |
| Вложения | `openpyxl` для XLSX, `python-docx` для DOCX, `pypdf` для PDF; JPEG принимается без распознавания текста |
| Запуск и проверки | Docker Compose для Product Service и PostgreSQL; npm, pip, pytest |

Внутренние сервисы обмениваются JSON через HTTP, файлы передаются как `multipart/form-data`. Потоковая выдача ответа не реализована.

## Быстрый запуск интерфейса

Нужны Node.js 20 и npm. Команды ниже рассчитаны на PowerShell и выполняются из корня этого репозитория:

```powershell
cd .\web
npm ci
npm run dev
```

Откройте `http://localhost:3000`. Без `web/.env.local` приложение использует встроенный mock AI и mock-корзину. Например, сообщение `добавь 2` создаёт предложение, которое можно подтвердить в интерфейсе; результат ведёт на `/mock-cart`. Для этого режима Python, PostgreSQL и ключ LLM не нужны.

## Запуск всех трёх модулей локально

Нужны Docker Desktop с `docker compose`, Python 3.12, Node.js 20 и npm. Порты `3000`, `8001` и `8002` должны быть свободны. Используйте три окна PowerShell; в каждом начните из корня репозитория.

### 1. Product Service и PostgreSQL

```powershell
cd .\services\product-service
Copy-Item .env.example .env
docker compose -f compose.yml up -d --build product-service
docker compose -f compose.yml exec product-service python -m app.load_fixture
Invoke-RestMethod http://localhost:8001/health
```

Compose запускает PostgreSQL и Product Service. Команда `app.load_fixture` добавляет тестовый товар `515291` в каталог; логин к ekt.kz для этого не требуется. Ожидаемый ответ `/health` — `status: healthy`. База сохраняется в Docker volume после остановки контейнеров.

Для проверки поиска напрямую:

```powershell
$headers = @{ Authorization = 'Bearer change-me' }
$body = @{ query = '027228'; limit = 5; filters = @{} } | ConvertTo-Json -Depth 3
Invoke-RestMethod -Method Post -Uri http://localhost:8001/internal/v1/products/search -Headers $headers -ContentType 'application/json' -Body $body
```

### 2. AI Service

```powershell
cd .\ai-service
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:PRODUCT_SERVICE_URL = 'http://127.0.0.1:8001'
$env:INTERNAL_SERVICE_TOKEN = 'change-me'
$env:LLM_PROVIDER = 'mock'
$env:REDIS_URL = ''
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8002
```

AI Service доступен на `http://localhost:8002/docs`. Его `.env.example` служит образцом: текущая реализация читает переменные окружения процесса, но не загружает `.env` автоматически. Встроенный LLM mock позволяет запустить сервис без API-ключа, однако поддерживает только базовые ответы и поиск; полноценное поведение модели и предложение корзины зависят от настроенного внешнего LLM.

### 3. Веб-приложение

```powershell
cd .\web
@(
  'AI_SERVICE_URL=http://127.0.0.1:8002'
  'PRODUCT_SERVICE_URL=http://127.0.0.1:8001'
  'INTERNAL_SERVICE_TOKEN=change-me'
  'CART_ADAPTER_MODE=mock'
) | Set-Content -Encoding utf8 .env.local
npm ci
npm run dev
```

Откройте `http://localhost:3000`. Адреса `127.0.0.1` используются потому, что AI Service и Next.js запущены на компьютере, а Product Service опубликован контейнером на порт `8001`. Адреса вида `http://product-service:8001` и `http://ai-service:8002` из файлов `.env.example` рассчитаны на общую Docker-сеть и при таком способе запуска не подойдут. После изменения `.env.local` перезапустите `npm run dev`.

Остановка: `Ctrl+C` в окнах AI Service и Next.js, затем в каталоге `services/product-service` выполните `docker compose -f compose.yml down`. Эта команда оставляет данные PostgreSQL в volume.

## Реальный каталог, LLM и Redis

- Для загрузки каталога ekt.kz задайте `EKT_API_USERNAME` и `EKT_API_PASSWORD` в `services/product-service/.env`, перезапустите Compose и выполните из этого каталога `docker compose -f compose.yml exec product-service python -m app.sync_catalog`. Каталог не синхронизируется при старте. Для короткой пробной загрузки доступно `--max-pages 1`; для импорта без запросов деталей — `--no-enrich`.
- Для внешней модели задайте в окне AI Service `LLM_PROVIDER` (`openai` или `deepseek`), `LLM_API_KEY`, `LLM_BASE_URL` (базовый URL OpenAI-совместимого API без `/chat/completions`) и `LLM_MODEL`, затем перезапустите сервис. Секреты храните вне Git.
- Для Redis запустите доступный Redis-сервер и задайте `REDIS_URL`, например `redis://127.0.0.1:6379/0`, **до** запуска AI Service. Без Redis история чата хранится только до перезапуска процесса.

`INTERNAL_SERVICE_TOKEN` должен совпадать у Product Service, AI Service и `web`. Если меняете значение `change-me`, обновите `services/product-service/.env`, переменную в окне AI Service и `web/.env.local`.

## Основные настройки

| Переменная | Где используется | Назначение |
| --- | --- | --- |
| `AI_SERVICE_URL` | `web` | Адрес AI Service; пустое значение включает встроенный mock веб-приложения. |
| `PRODUCT_SERVICE_URL` | `ai-service`, `web` | Адрес Product Service. |
| `INTERNAL_SERVICE_TOKEN` | все модули | Токен внутренних запросов к Product Service. |
| `PRODUCT_DATABASE_URL` | Product Service | Подключение к PostgreSQL; в Compose уже задано. |
| `EKT_API_USERNAME`, `EKT_API_PASSWORD` | Product Service | Basic Auth для запросов к API ekt.kz. |
| `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` | AI Service | Выбор и параметры внешней LLM; по умолчанию используется `mock`. |
| `REDIS_URL` | AI Service | Хранилище истории чатов; пустое значение включает память процесса. |
| `CART_ADAPTER_MODE` | `web` | При `mock` проверка наличия демонстрационная. |
| `CART_PROPOSAL_TTL_SECONDS` | `web` | Срок действия предложения корзины; по умолчанию 900 секунд. |
| `EKT_CART_URL` | `web` | Ссылка, которую возвращает mock-корзина; по умолчанию `/mock-cart`. |

Примеры всех переменных находятся в `web/.env.example`, `ai-service/.env.example` и `services/product-service/.env.example`.

## Текущие ограничения MVP

- Интеграция с реальным Cart API ekt.kz ещё не реализована: `web` всегда использует `MockEktCartAdapter`. Предложения и ключи идемпотентности хранятся в памяти процесса Next.js; при перезапуске они теряются.
- В режиме `CART_ADAPTER_MODE=mock` наличие при подтверждении корзины тоже демонстрационное. Другие значения включают запрос наличия в Product Service, но не превращают адаптер корзины в реальный.
- AI mock и веб mock отличаются: веб mock показывает готовую карточку и сценарий корзины, AI mock проверяет базовую интеграцию с Product Service. Для полноценного диалога и вызова инструмента `propose_cart_add` нужен настроенный внешний LLM.
- В автономном режиме `web` загрузка файла только имитируется. AI Service извлекает текст из PDF и DOCX, а также данные XLSX; JPEG принимается без OCR или анализа изображения. Информация об условиях покупки пока не настроена. Цена и остаток из поиска по локальной БД являются кешированными; live-запрос деталей и наличия требует доступного API ekt.kz.

## Проверки

В каталоге `web`:

```powershell
npm run lint
npm run build
```

В каталоге `services/product-service` тесты запускаются в отдельном профиле Compose:

```powershell
docker compose -f compose.yml --profile test build tests
docker compose -f compose.yml --profile test run --rm tests
```

В каталоге `ai-service` после создания виртуального окружения:

```powershell
.\.venv\Scripts\python.exe -m pip install pytest
.\.venv\Scripts\python.exe -m pytest -q
```
