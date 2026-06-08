# go-api — Go-сайдкар для Photoshnaya

`go-api` — это HTTP-сервис на Go, поднимаемый рядом с Python-ботом и обслуживающий «горячие» операции голосования и приёма фото на конкурс. Бот общается с ним по HTTP и **деградирует обратно на старый Python+SQLAlchemy путь** при недоступности сервиса.

Цель миграции — постепенно перенести наиболее нагруженные синхронные операции на Go без переписывания всего бота, сохраняя один и тот же PostgreSQL как источник истины.

## Что мигрировано

| Операция бота | Эндпоинт `go-api` | Где зовётся в Python |
|---|---|---|
| Старт сессии голосования | `GET /vote/session` | `handlers/internal_logic/vote_start.py` |
| Следующее фото в голосовании | `GET /vote/photos/next` | `handlers/personal_vote_menu.py` |
| Предыдущее фото в голосовании | `GET /vote/photos/prev` | `handlers/personal_vote_menu.py` |
| Поставить лайк | `POST /vote/likes` | `handlers/personal_vote_menu.py` |
| Снять лайк | `DELETE /vote/likes` | `handlers/personal_vote_menu.py` |
| Закоммитить голос пользователя | `POST /vote/submit` | `handlers/personal_vote_menu.py` |
| Регистрация фото на конкурс | `POST /contest/submissions` | `handlers/user_action.py` (через `like_engine.register_contest_submission`) |
| Healthcheck | `GET /health` | docker `HEALTHCHECK` |

Не мигрировано (остаётся в Python): админ-панель, FSM-диалоги, напоминалки (`reminders.py`), регистрация группы, выбор победителя, выгрузка участников/лидеров.

## Архитектура

```
+---------------------+         HTTP (JSON)        +-----------------+
|    Python bot       | -------------------------> |    go-api       |
|    (aiogram v3)     |   GET/POST/DELETE          |  (net/http +    |
|                     | <------------------------- |   pgx/v5)       |
|  VoteBackend        |    200 / 4xx{code}         |                 |
|  + circuit breaker  |                            |                 |
+----------+----------+                            +--------+--------+
           |                                                |
           |        SQLAlchemy async (fallback)             |  pgx pool
           v                                                v
                       +-----------------------+
                       |    PostgreSQL 15      |
                       +-----------------------+
```

Один и тот же кластер Postgres; Go и Python пишут в одни и те же таблицы (`photo`, `group_photo`, `photo_like`, `tmp_photo_like`, `contest_user`, `contest_winner`, `"group"`, `user`, `contest`). Схему создаёт Python через `Base.metadata.create_all` при старте — миграций нет, Go её только использует.

### Layering внутри `go-api`

- `cmd/api/main.go` — точка входа: грузит конфиг, поднимает `pgxpool`, регистрирует роуты на `http.ServeMux`.
- `internal/config` — env-конфиг (`PS_URL` / legacy `ps_url`, `PORT`). Нормализует SQLAlchemy-схему `postgresql+psycopg://` → `postgresql://`, чтобы можно было переиспользовать тот же DSN, что у Python.
- `internal/handler` — HTTP-обработчики, парсинг query/body, маппинг доменных ошибок в HTTP-коды (`ErrNoPhotos → 404 no_photos`, `ErrAlreadyVoted → 409 already_voted`, и т.д.). Body ограничен 1 MB через `http.MaxBytesReader`.
- `internal/service` — бизнес-логика: проверка статуса голосования, выбор фото, постановка/снятие лайков, финальный коммит голоса. Не знает про HTTP.
- `internal/store` — SQL поверх `pgxpool`. Содержит ровно те запросы, которые раньше были в `LikeDB` / `VoteDB` / `RegisterDB` на SQLAlchemy.
- `internal/model` — структуры запросов/ответов и sentinel-ошибки.

### Со стороны Python: `app/services/vote_backend.py`

`VoteBackend` наследует `LikeDB` и для каждой операции делает следующее:

1. Если `GO_API_URL` пустой → сразу идёт по fallback-пути (как было до миграции).
2. Иначе: проверяет circuit breaker, шлёт HTTP-запрос через `aiohttp`.
3. На 4xx с известным `code` из `KNOWN_BUSINESS_ERROR_CODES` бросает `VoteBackendBusinessError` — это **бизнес-ответ**, не отказ сайдкара, наверх он летит как обычная ошибка домена.
4. На 5xx / таймаут / `aiohttp.ClientError` — логирует и **выполняет ту же операцию через Python+SQLAlchemy путь** (`_fallback_*`).
5. После N подряд сбоев (`CIRCUIT_FAILURE_THRESHOLD = 3`) circuit breaker открывается на `CIRCUIT_COOLDOWN_SEC = 15` секунд, в это время запросы к сайдкару не идут и сразу используется fallback. Затем — HALF_OPEN, проба одним запросом.

Это даёт «нулевую» поверхность риска: если Go упал, бот продолжает работать на старом коде.

## Конфигурация и развёртывание

### Локально (`docker-compose.dev.yml`)

Сервис `go-api` собирается из `./go-api`, читает `PS_URL=postgresql://postgres:postgres@db:5432/postgres`, бот получает `GO_API_URL=http://go-api:8080` и стартует только после healthcheck сайдкара (`depends_on.go-api.condition: service_healthy`).

### Прод (`docker-compose.yml`)

Оба контейнера в `network_mode: host`. Образы тянутся из Docker Hub:

- `${IMAGE_REPOSITORY}:${IMAGE_TAG}` — Python бот;
- `${GO_API_IMAGE_REPOSITORY:-aapq/photoshnaya_go_api}:${GO_API_IMAGE_TAG:-latest}` — Go.

`GO_API_URL` в проде задаётся через env и может быть пустым — тогда бот молча работает без сайдкара.

### CI (`.github/workflows/python-app.yml`)

- На каждый PR: `go vet` + `go test ./...` в директории `go-api/`.
- На push в default-ветку: сборка и пуш образа `go-api` в Docker Hub с тегами `:latest` и `:<sha>`, кэш `type=gha,scope=go-api`.
- Деплой: `scp docker-compose.yml` на удалённый хост и `docker compose pull && up -d` с переданными `GO_API_IMAGE_REPOSITORY` / `GO_API_IMAGE_TAG`.

## Контракт ошибок

`go-api` всегда возвращает JSON. На ошибку — `{"code": "<machine_code>", "message": "..."}`. Известные `code` (синхронизированы с `KNOWN_BUSINESS_ERROR_CODES` в Python):

| HTTP | code | Семантика |
|---|---|---|
| 404 | `no_photos` | В группе нет фото-кандидатов |
| 409 | `no_vote_yet` | Голосование ещё не запущено админом |
| 409 | `already_voted` | Пользователь уже отдал голос в этом конкурсе |
| 409 | `self_like` | Попытка лайкнуть собственное фото |
| 404 | `photo_not_found` | Текущее фото отсутствует в выборке |
| 404 | `group_not_found` | Группа не зарегистрирована |
| 404 | `user_not_found` | Пользователь отсутствует в БД |
| 4xx | `invalid_request` / `invalid_<field>` | Невалидный JSON или query-параметр |
| 413 | `request_too_large` | Тело > 1 MB |
| 405 | `method_not_allowed` | Неверный HTTP-метод |
| 500 | `internal_error` | Неожиданная ошибка (логируется на стороне Go) |

Любой другой статус Python трактует как **сбой сайдкара** и переключается на fallback.

## Локальный запуск только Go-сервиса

```bash
cd go-api
PS_URL='postgresql://postgres:postgres@localhost:5432/postgres' \
  go run ./cmd/api
# или
go build -o /tmp/go-api ./cmd/api && PS_URL=... /tmp/go-api
```

Тесты:

```bash
cd go-api
go vet ./...
go test ./...
```

Интеграционный тест в `internal/service/integration_test.go` ожидает живой Postgres — пропускается без `PS_URL` (см. сам файл).

## Граничные случаи и подводные камни

- **Схема DB-уникальна для Python.** Go не создаёт таблиц — он падает на старте если ждёт таблицу, а Python ещё не отработал `create_all`. В docker-compose это решено `depends_on db: service_healthy` + ретраи на стороне Python; в проде бот стартует первым.
- **`int64` vs Python `int`.** Telegram chat/user IDs могут не помещаться в 32 бита — в Go везде `int64`, в JSON-полях это просто число. Не менять на `int32`.
- **Транзакционность `submit_vote`.** В Go все три действия (перенос из `tmp_photo_like` в `photo_like`, очистка `tmp`, вставка в `contest_user`) делаются одной транзакцией `pgx.Tx`. В Python-fallback — одна `session.begin()`. Не разделять: повторный `submit_vote` упирается в уникальный ключ `contest_user` и должен ловиться как `already_voted`.
- **Имя таблицы `group`.** `group` — зарезервированное слово, в SQL всегда экранируется как `"group"`. См. `internal/store/vote.go`.
- **Конфликт с SQLAlchemy DSN.** Бот получает `ps_url=postgresql+psycopg://...`, Go его не понимает. `config.normalizeDatabaseURL` срезает префикс — если в проде задаётся `ps_url` (lowercase), сервис подхватит его и нормализует.
- **Self-like.** Проверка дублируется на двух сторонах: и в Go-store, и в Python-fallback. Это намеренно — если когда-нибудь бот пойдёт в Postgres напрямую (а не через сайдкар), правило сохранится.

## Что осталось / возможные следующие шаги

- Подсчёт лидеров и участников (сейчас Python, кандидат на перенос — это read-heavy).
- Завершение голосования и определение победителя (`finish-vote` flow).
- Метрики/трейсинг (сейчас только `slog` JSON в stdout).
- Перенос `Base.metadata.create_all` под управление миграциями (Alembic или goose) — текущая схема живёт в `app/db/db_classes.py` и Go её обязан знать наизусть.
