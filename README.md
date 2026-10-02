# ODPO — учёт расписания и педагогической нагрузки

Веб-приложение для организации дополнительного профессионального
образования. Ведёт справочники, расписание занятий, считает нагрузку
преподавателей и формирует отчёты.

Разработано под конкретный учебный центр: циклы повышения квалификации
и профессиональной переподготовки, занятия на нескольких базах,
несколько преподавателей с лимитами нагрузки.


## Возможности

- **Справочники** — должности, сотрудники, базы, виды финансирования,
  названия циклов, типы занятий. Полный обмен через XLSX.
- **Циклы и занятия** — цикл как период обучения с датами, базой,
  видом финансирования и списком занятий.
- **Расписание** — сетка «преподаватели × дни» с фильтрами по базе,
  циклу, преподавателю и периоду. Проверка превышения лимитов нагрузки.
- **Импорт цикла из XLSX** — файл с двумя листами («Цикл» и «Занятия»)
  создаёт новый цикл целиком. Шаблон генерируется программно.
- **PDF-выгрузки цикла** — три документа: расписание занятий,
  распределение часов, табель (расчасовка по месяцам).
- **Отчёт «Педагогические часы»** — распределение часов по циклам
  за выбранный месяц, итоги по заведующим. Выгрузка в XLSX.


## Требования

- Python 3.14+
- Django 6.1+
- Системные библиотеки для WeasyPrint:
  - Debian/Ubuntu: `libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b`
  - Fedora/RHEL: `pango harfbuzz`
  - Windows: GTK3 runtime, см. документацию WeasyPrint

Всё остальное — см. `requirements.txt`.


## Быстрый старт (разработка)

```bash
git clone https://github.com/jdoe058/odpo.git
cd odpo

python -m venv venv
source venv/bin/activate          # Linux
# venv\Scripts\activate           # Windows

pip install -r requirements.txt

cp .env.example .env              # и заполнить
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Открыть http://127.0.0.1:8000/


## Переменные окружения

Хранятся в `.env`, читаются через `python-dotenv`.

| Переменная | Обяз. | По умолчанию | Описание |
|---|---|---|---|
| `DJANGO_SECRET_KEY` | да (прод) | `unsafe-default-change-me` | Секретный ключ Django |
| `DJANGO_DEBUG` | нет | `False` | `True` — режим разработки |
| `DJANGO_ALLOWED_HOSTS` | нет | `127.0.0.1,localhost` | Хосты через запятую |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | нет | `http://127.0.0.1,http://localhost` | Origin-адреса |


## Основные URL

| URL | Имя | Назначение |
|---|---|---|
| `/` | `schedule_grid` | Расписание |
| `/lessons/<pk>/edit/` | `lesson_edit` | Редактирование занятия |
| `/cycle/import/` | `cycle_import` | Импорт цикла из XLSX |
| `/cycle/import/template/` | `cycle_import_template` | Шаблон XLSX |
| `/cycle/<id>/export/xlsx/` | `cycle_export_xlsx` | Цикл в XLSX |
| `/cycle/<id>/export/<kind>/` | `cycle_export` | PDF-выгрузки (schedule / teacher_load / timesheet) |
| `/references/` | `references_exchange` | Обмен справочниками |
| `/references/export/` | `references_export` | Выгрузка справочников |
| `/reports/ped-hours/` | `ped_hours` | Отчёт «Педагогические часы» |
| `/reports/ped-hours/export/` | `ped_hours_export` | Выгрузка отчёта в XLSX |


## Структура проекта

```
config/                     — настройки Django
timetable/                  — единственное приложение
  models.py                 — модели (Cycle, Lesson, Employee, ...)
  views.py                  — основные view
  urls.py                   — маршруты
  cycle_xlsx_import.py      — импорт цикла из XLSX
  xlsx_cycle_format.py      — формат листов «Цикл» / «Занятия»
  xlsx_utils.py             — нормализация ячеек XLSX

  services/                 — расчётная логика, без HTTP
    grid.py                 — сетка «преподаватели × дни»
    limits.py               — лимиты нагрузки, переработки
    periods.py              — неделя / месяц / год / произвольный
    cycle_hours.py          — часы цикла по типам занятий
    teacher_load.py         — распределение часов по категориям
    timesheet.py            — расчасовка по дням месяца
    ped_hours.py            — отчёт «Педагогические часы»
    approvers.py            — поиск утверждающего

  references/               — справочники
    registry.py             — реестр: единый источник истины
    xlsx_export.py          — выгрузка в XLSX
    xlsx_importer.py        — импорт из XLSX

  exports/                  — выгрузки
    kinds.py                — реестр видов выгрузок
    cycle_xlsx_export.py    — цикл в XLSX
    ped_hours_xlsx.py       — отчёт по пед. часам в XLSX
    pdf/
      render.py             — HTML → PDF через WeasyPrint
      pdf_views.py          — view для PDF
      css/                  — стили PDF (base + по видам)

  templates/timetable/      — шаблоны
  tests/                    — тесты

static/timetable/css/       — стили веб-интерфейса
deploy.sh                   — скрипт развёртывания
gunicorn.conf.py            — конфиг gunicorn
```


## Ключевые подсистемы

### Справочники

Все шесть справочников описаны в `references/registry.py`:
slug, заголовки колонок, тип поля, порядок импорта. Реестр используется
и для меню, и для URL, и для XLSX-обмена.

Обмен — через XLSX: один лист на справочник, две строки шапки
(русские названия и латиница), данные с третьей строки. Порядок листов
не важен. Импорт двухшаговый: «Проверить» (dry-run) и «Применить».

Ограничения (см. «Технический долг»): записи не создаются — только
обновляются, ссылки на другие справочники по имени.

### Циклы и занятия

`Cycle` — период обучения с датами, базой, видом финансирования
и составителем. `Lesson` — занятие с датой, временем начала, часами,
типом, темой, преподавателем и опциональной базой.

Академический час — 45 минут (`MINUTES_PER_HOUR`). Поле
`Lesson.available_from` — момент, с которого можно начать следующее
занятие (окончание + перемена).

### PDF-выгрузки

Рендер — WeasyPrint. Шаблоны — HTML в
`templates/timetable/exports/pdf/`, стили — CSS в
`exports/pdf/css/`. Реестр видов — `exports/kinds.py`.

Чтобы добавить новый вид выгрузки:

1. Создать `exports/<kind>.py` с `build_own_context(cycle)` и
   `build_filename(cycle)`, зарегистрировать через `register(...)`.
2. Создать `templates/timetable/exports/pdf/<kind>.html`.
3. Создать `exports/pdf/css/<kind>.css`.
4. Добавить код вида в `PDF_KINDS` в `exports/pdf/pdf_views.py`.

### Отчёт «Педагогические часы»

`services/ped_hours.py::calculate_ped_hours(year, month)` возвращает
циклы, чей период пересекается с месяцем, с суммой часов всех занятий.
Флаг `counts_in_hours` игнорируется — считаются все занятия, включая
экзамены и консультации.

Доступен из шапки через пункт «Отчёты».


## Развёртывание

Прод — Linux + gunicorn + systemd. См. `deploy.sh`, `gunicorn.conf.py`
и пример unit-файла в документации systemd.

```bash
./deploy.sh
```

Скрипт делает: `git pull`, установку зависимостей, миграции,
`collectstatic`, перезапуск gunicorn.

Nginx (или whitenoise) раздаёт `/static/` и `/media/` — в зависимости
от окружения.


## Технический долг

Осознанно отложенные улучшения. Порядок — не приоритет.

**Справочники**
- Импорт не создаёт отсутствующие записи — только обновляет.
  Опечатка в фамилии даёт ошибку, а не нового сотрудника.
- Ссылки на другие справочники — по имени. Переименование должности
  ломает сохранённый файл.
- Warnings не блокируют импорт — можно молча потерять строки, если
  не читать отчёт.
- Права — только `@login_required`. Любой залогиненный может
  перезаписать справочники.
- Нет кнопки «Восстановить эталон» из `reference_data`.

**PDF и XLSX**
- PDF рендерится на каждый запрос, без кэша. Для больших циклов —
  секунды.
- Шрифты на Linux не проверены. Если Times New Roman не окажется,
  положить Liberation Serif в `static/` и подключить через `@font-face`.
- В XLSX-выгрузке цикла нет merge-ячеек для повторяющихся дат —
  только пустые ячейки.

**Инфраструктура**
- В `settings.py` опасный дефолт `SECRET_KEY` — надо падать,
  если `DJANGO_DEBUG=False` и ключ не задан.
- SQLite в проде. В планах — PostgreSQL.
- `deploy.sh` переустанавливает все зависимости каждый раз.

**Тесты**
- Покрытие неполное. Основные сервисы (`limits`, `periods`, `grid`)
  покрыты, view-слой и PDF-вёрстка — почти нет.


## Лицензия

Внутренний проект.
