# Timetable

## Требования

- Python 3.12+
- pip

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

### 6. Создать суперпользователя

```bash
python manage.py createsuperuser
```

### 7. Запустить сервер

```bash
python manage.py runserver
```

Открыть в браузере:

- Админка: http://127.0.0.1:8000/admin/
- Расписание: http://127.0.0.1:8000/