# gunicorn.conf.py
import multiprocessing

# Слушаем unix-сокет — быстрее и безопаснее, чем TCP
bind = "unix:/run/gunicorn/gunicorn.sock"

# Воркеры: 2*CPU + 1 — стандартная рекомендация
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
threads = 2
timeout = 120
graceful_timeout = 30
keepalive = 5

# Логи в stdout/stderr — их подхватит journald
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Перезагружать воркеры при изменении кода (полезно при деплое)
max_requests = 1000
max_requests_jitter = 100

# Чтобы сокет не оставался от прошлого запуска
def on_starting(server):
    import os
    try:
        os.unlink("/run/gunicorn/gunicorn.sock")
    except FileNotFoundError:
        pass