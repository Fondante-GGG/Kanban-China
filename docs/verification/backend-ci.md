# Исправление backend CI: Python 3.12 test discovery

Дата: 31.10.2026. Базовый commit: `dd7aa80`.

## Наблюдение GitHub Actions

В запуске [41187980136](https://github.com/Fondante-GGG/Kanban-China/actions/runs/41187980136)
backend dependency install, ephemeral environment и Django System Checks прошли,
а Run Backend Unit Tests завершился с exit 1. Frontend прошёл; Docker job был
пропущен из-за зависимости от backend. Подробный job log без авторизации
недоступен (API возвращает 403); вывод ниже получен локальным воспроизведением,
не выдаётся за скачанный лог CI.

## Причина и исправление

В чистом окружении Python 3.12 команда `python backend/manage.py test backend.tests`
падала до выполнения тестов:

```text
unittest.loader._get_directory_containing_module
os.path.abspath(module.__file__)
TypeError: expected str, bytes or os.PathLike object, not NoneType
```

`backend/` не содержал `__init__.py` и импортировался как namespace package с
`backend.__file__ = None`. Добавлен `backend/__init__.py` только с docstring:
это обычный Python package, доступный Django/unittest discovery на версии CI.
Команда CI, assertions, исключения безопасности и настройки test skips не менялись.
Поведение namespace discovery между версиями Python отличается; локальный запуск
на 3.14 не заменяет проверку на 3.12. См. [Python 3.14 unittest changes](https://docs.python.org/3.14/whatsnew/3.14.html#unittest)
и [Python 3.12 discovery](https://docs.python.org/3.12/library/unittest.html#test-discovery).

## Выполненные проверки

Создан отдельный worktree от исходного commit без пользовательского `.env`,
виртуальная среда CPython 3.12.13 и установлены `backend/requirements.txt`.
Фактические версии включают Django 6.1.2, channels 4.3.2, daphne 4.2.3,
Pillow 13.0.0 и websockets 17.4. Переданы `DJANGO_DEBUG=True` и временный
случайный ключ через окружение без вывода самого ключа.

- До исправления команда тестов — exit 1 на discovery, тесты не запускались.
- После исправления:
  `python backend/manage.py test backend.tests --noinput --verbosity 2`
  — **113 тестов, OK (skipped=3), 131,765 с, exit 0**.
  Выполнены 110 тестов; три существующих сценария PostgreSQL-конкурентности
  пропущены при SQLite. Новых skip/xfail не добавлено.
- В основном рабочем дереве Python 3.12 обнаруживает те же 113 тестов.
- `python backend/manage.py check` — 0 замечаний.
- `git diff --check` — успешно.
- `docker build --iidfile /tmp/yrys-backend-ci-image.id -f backend/Dockerfile .`
  — exit 0; backend image успешно собран из исправленного worktree.
- Временный контейнер этого образа без сети, host volumes и ports:
  `python backend/manage.py check` при `DJANGO_DEBUG=False` и явно переданном
  случайном ключе — exit 0, 0 замечаний. Entrypoint переопределён только на
  эту read-only проверку; migrate/seed/server не запускались.

Локальные журналы воспроизведения: `/tmp/yrys-backend-ci-test.log` (до),
`/tmp/yrys-backend-ci-test-fixed.log` (после).

Повторный удалённый запуск GitHub Actions не выполнялся: изменение должно
попасть в опубликованный commit. Commit/push не выполняются без разрешения.
Рабочая БД, данные, API и бизнес-логика не изменялись.

Независимое ревью package marker и этого отчёта: APPROVED; обязательных замечаний нет.
