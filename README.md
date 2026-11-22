# Парсер цитат (Quotes Scraper)

Асинхронный парсер цитат с фронтендом на Vue и API/воркером на FastAPI.

```text
Vue (GitHub Pages) -> FastAPI + worker (Render) -> Supabase Postgres + pgmq
                                               \-> Cloudflare Browser Rendering
```

## Стек технологий

- **Фронтенд:** Vue 3, Vite, TypeScript, axios.
- **Бэкенд:** FastAPI, воркер на asyncio, Playwright, httpx, BeautifulSoup.
- **Хранилище:** Supabase Postgres для статусов и результатов, pgmq для очереди задач.
- **Браузер:** Playwright для `://toscrape.com`, Cloudflare Browser Rendering
  для произвольных URL.
- **Хостинг:** GitHub Pages (фронтенд), Render Free (бэкенд).

## Структура репозитория

```text
backend/
  src/            FastAPI-приложение, воркер, парсер, клиенты БД и очереди
  tests/          юнит-тесты
  pyproject.toml
  .env.example
frontend/
  src/            Vue-приложение, компоненты, композабл для поллинга (polling)
  .env.example
scripts/
  smoke_test.py   сквозная (end-to-end) проверка API
  setup_supabase.sql
docs/adr/         записи об архитектурных решениях (ADR)
Makefile
```

## Конфигурация

Создайте локальные файлы переменных окружения:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Переменные бэкенда:

| Переменная | Назначение |
| --- | --- |
| `SUPABASE_URL` | URL проекта Supabase |
| `SUPABASE_ANON_KEY` | Анонимный ключ (anon key) Supabase, используемый бэкендом |
| `CF_ACCOUNT_ID` | ID аккаунта Cloudflare |
| `CF_BROWSER_API_TOKEN` | Токен Cloudflare Browser Rendering |
| `INTERNAL_SECRET` | Bearer-секрет для эндпоинта `GET /health` |
| `PORT` | Порт бэкенда (Render задаёт его автоматически) |
| `CORS_ORIGINS` | Разрешённые домены фронтенда через запятую |

Переменная фронтенда:

| Переменная | Назначение |
| --- | --- |
| `VITE_API_URL` | Публичный URL развёрнутого бэкенда |

## Настройка Supabase

1. Создайте проект в Supabase.
2. Выполните скрипт `scripts/setup_supabase.sql` в SQL-редакторе.
3. Откройте **Integrations → Queues → Settings** и включите
   **Expose Queues via PostgREST**. Это создаст функции-обёртки `pgmq_public`,
   используемые бэкендом.
4. На той же странице настроек выдайте роли `anon` права на работу с очередью,
   необходимые бэкенду (`send`, `read`, `archive`), либо переведите бэкенд
   на ключ `service_role` и удалите политики для `anon` из SQL-скрипта.

> Включённый в репозиторий SQL-скрипт задаёт разрешающие политики для `anon`, так как
> бэкенд использует `SUPABASE_ANON_KEY`. Это удобно для демо на бесплатном тарифе,
> но в продакшене следует использовать серверный ключ `service_role`.

## Локальная разработка

Предварительные требования: Python 3.11+, Node.js 22+, проект Supabase и аккаунт
Cloudflare с включённым Browser Rendering.

```bash
make install          # зависимости бэкенда + Chromium + зависимости фронтенда
make dev              # FastAPI с автоперезагрузкой на порту :8000
cd frontend && npm run dev   # Vite на порту :5173
```

- Документация API: <http://localhost:8000/docs>
- Проверка работоспособности (Health check): `curl -H "Authorization: Bearer $INTERNAL_SECRET" http://localhost:8000/health`
- Фронтенд: <http://localhost:5173>

## Тестирование

```bash
make test             # юнит-тесты бэкенда
make lint             # ruff + mypy + vue-tsc
API_URL=http://localhost:8000 make smoke
```

Дымовой тест (smoke test) отправляет страницу со скроллом, ожидает статус `done`,
проверяет результат, а затем отправляет некорректный URL и ожидает задачу
со статусом `failed` и сообщением об ошибке.

## Деплой (развёртывание)

### Бэкенд на Render

- Команда сборки (Build command): `cd backend && pip install -e .`
- Команда запуска (Start command): `uvicorn src.api:app --host 0.0.0.0 --port $PORT`
  (или скрипт `quotes-api`)
- Задайте переменные окружения бэкенда в панели управления Render.
- Настройте cron-задачу в Supabase для регулярного пинга `/health` (keepalive),
  если бесплатный сервис не должен засыпать (см. конец файла `scripts/setup_supabase.sql`).

### Фронтенд на GitHub Pages

```bash
cd frontend
VITE_API_URL=https://onrender.com npm run build
```

Опубликуйте директорию `dist/` на GitHub Pages. Базовый путь (`base`) в Vite
установлен как `/` в соответствии с планом проекта; измените его, если сайт
размещается в поддиректории репозитория.

## Архитектурные решения

Информацию о выбранном облачном стеке, лимитах бесплатных тарифов и путях
миграции см. в [`docs/adr/0001-cloud-platform.md`](docs/adr/0001-cloud-platform.md).
