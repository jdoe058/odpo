## README.md

```markdown
# Timetable

## Требования

- Python 3.12+
- pip

## База данных

Проект использует **SQLite** — встроенную базу данных Python. 
Отдельный сервер БД (PostgreSQL, MySQL) устанавливать не нужно.

Файл базы создаётся автоматически при первой миграции:
`python manage.py migrate` → появится `db.sqlite3` в корне проекта.

Для резервной копии достаточно скопировать этот файл:
`cp db.sqlite3 db.backup.sqlite3`

Если в будущем потребуется PostgreSQL — измените блок `DATABASES` 
в `odpo/settings.py` и установите `psycopg2-binary`.

## Возможности

- Просмотр расписания занятий с фильтрами (группа, преподаватель, дата).
- **Экспорт документов в DOCX.** Виды выгрузок описаны в реестре
  `timetable.exports.kinds` и наполняются в `apps.ready()`:

  | Код              | Документ                                  |
  |------------------|-------------------------------------------|
  | `schedule`       | Расписание занятий                        |
  | `teacher_load`   | Распределение часов преподавателей        |
  | `timesheet`      | Табель                                    |

  Шаблоны `.docx` загружаются через админку (раздел
  «Шаблоны документов»); для каждого вида активен ровно один
  шаблон — это гарантируется `UniqueConstraint` на уровне БД.
- Разграничение доступа: расписание и экспорт доступны только после входа.
- **Контроль дневной нагрузки сотрудников.**
  У каждой должности есть лимит `max_hours_per_day`.
  На странице расписания выводится фактическая нагрузка по дням,
  а при превышении лимита — предупреждение.

### Демо-данные

`timetable/demo_data.py` — вымышленные базы, сотрудники, названия
циклов и занятия. Загружаются командой `seed_demo`. Все значения
не пересекаются с реальными: базы названы «УЧЕБНЫЙ КОРПУС №1» и т.п.,
сотрудники — условные ФИО, названия циклов — типовые программы ДПО.

## Запуск

### 1. Клонировать репозиторий

```bash
git clone https://github.com/jdoe058/odpo odpo
cd odpo
```

### 2. Создать и активировать виртуальное окружение

**Windows:**

```powershell
python -m venv venv
venv\Scripts\activate
```

если политика включена
```
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
```

**Linux / macOS:**

```bash
python -m venv venv
source venv/bin/activate
```

### 3. Установить зависимости

```bash
pip install -r requirements.txt
```

### 4. Создать `.env`

Скопируйте `.env.example` в `.env` и заполните:

```
SECRET_KEY=your-secret-key-here
DEBUG=True
```

### 5. Применить миграции

```bash
python manage.py migrate
```

### 6. Заполнить справочники

```bash
python manage.py seed_references
```

### 6a. (Опционально) Загрузить демо-данные

Для быстрого наполнения стенда вымышленными базами, сотрудниками,
циклами и занятиями:

```bash
python manage.py seed_demo

### 7. Создать суперпользователя

```bash
python manage.py createsuperuser
```

### 8. Запустить сервер

```bash
python manage.py runserver
```

Открыть в браузере:

- Админка: http://127.0.0.1:8000/admin/
- Расписание: http://127.0.0.1:8000/

## Шаблоны документов

Файлы шаблонов лежат в `templates_docx/<kind>/` и загружаются
через админку. Любой шаблон может рассчитывать на общий набор
переменных, который формируется в
`timetable.exports.kinds.build_common_context`:

- `cycle_name`, `funding`, `base`, `start`, `end`
- `signer`, `signer_position`
- `approver`, `approver_position`

Плюс поля, специфичные для конкретной выгрузки (см.
`build_own_context` в `timetable/exports/<kind>.py`).
```
