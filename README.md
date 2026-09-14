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

