## Режимы работы

Бот поддерживает два режима работы:

### 1. Polling режим (bot.py)
Для локального запуска и тестирования:
```bash
python3 bot.py
```

### 2. Webhook режим (bot_webhook.py)
Для развёртывания на веб-сервисах (Railway, Render, Heroku и др.):
```bash
gunicorn bot_webhook:app
```

**Для развёртывания на облачных платформах см. [DEPLOYMENT.md](DEPLOYMENT.md)**

---

## Быстрое развёртывание на Railway

1. Fork этот репозиторий
2. Зарегистрируйтесь на [Railway.app](https://railway.app)
3. New Project → Deploy from GitHub
4. Выберите форкнутый репозиторий
5. Добавьте переменные окружения:
   - `TELEGRAM_BOT_TOKEN`
   - `OPENAI_API_KEY`
   - `WEBHOOK_URL` (URL вашего Railway проекта)
6. Railway автоматически развернёт бота

Подробная инструкция: [DEPLOYMENT.md](DEPLOYMENT.md)
