# Быстрый старт — Моё пространство

Пошаговая инструкция для запуска бота за 5 минут.

## Шаг 1: Создайте бота в Telegram

1. Откройте Telegram и найдите [@BotFather](https://t.me/BotFather)
2. Отправьте команду `/newbot`
3. Введите имя: `Моё пространство`
4. Введите username (например): `moe_prostranstvo_bot`
5. **Скопируйте токен** — он выглядит так: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`

## Шаг 2: Установите зависимости

```bash
cd moe_prostranstvo
pip3 install -r requirements.txt
```

Или с sudo (если нужны права):

```bash
sudo pip3 install -r requirements.txt
```

## Шаг 3: Настройте токен

Вариант А — через переменную окружения (рекомендуется):

```bash
export TELEGRAM_BOT_TOKEN="ваш_токен_от_botfather"
```

Вариант Б — создайте файл `.env`:

```bash
echo 'TELEGRAM_BOT_TOKEN="ваш_токен_от_botfather"' > .env
```

## Шаг 4: Запустите бота

```bash
python3 bot.py
```

Вы увидите:
```
Bot started! Press Ctrl+C to stop.
```

## Шаг 5: Протестируйте бота

1. Откройте Telegram
2. Найдите вашего бота по username (например, `@moe_prostranstvo_bot`)
3. Нажмите **Start** или отправьте `/start`
4. Попробуйте функции:
   - ⭐ Энергия дня
   - 🃏 Таро
   - 📝 Дневник

## Готово! 🎉

Бот работает локально на вашем компьютере.

## Запуск на сервере (опционально)

Для постоянной работы бота используйте один из методов:

### Метод 1: Screen (самый простой)

```bash
screen -S bot
cd moe_prostranstvo
export TELEGRAM_BOT_TOKEN="ваш_токен"
python3 bot.py
# Нажмите Ctrl+A, затем D
```

Вернуться к боту: `screen -r bot`

### Метод 2: Systemd (профессиональный)

Создайте файл `/etc/systemd/system/moe-prostranstvo.service`:

```ini
[Unit]
Description=Moe Prostranstvo Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/moe_prostranstvo
Environment="TELEGRAM_BOT_TOKEN=ваш_токен"
Environment="OPENAI_API_KEY=ваш_openai_ключ"
ExecStart=/usr/bin/python3 bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Запустите:

```bash
sudo systemctl daemon-reload
sudo systemctl enable moe-prostranstvo
sudo systemctl start moe-prostranstvo
```

## Проблемы?

### Ошибка: "TELEGRAM_BOT_TOKEN environment variable not set"

**Решение**: Установите переменную окружения:
```bash
export TELEGRAM_BOT_TOKEN="ваш_токен"
```

### Ошибка: "No module named 'telegram'"

**Решение**: Установите зависимости:
```bash
pip3 install python-telegram-bot
```

### Бот не отвечает

**Проверьте**:
1. Бот запущен? (`python3 bot.py` должен работать)
2. Токен правильный?
3. Интернет работает?

## Дополнительная информация

Полная документация: см. `README.md`

---

**Удачи! 🤍**
