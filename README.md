# 🤖 PAY APP BOT

Telegram арқылы Kaspi төлем жүйесімен жұмыс жасайтын бот. Қолданушылар кілттер (key) сатып алып, арнайы апп алуға мүмкіндік береді.

---

## 📁 Жоба құрылымы

```
PAY APP BOT/
├── main.py                # Бот іске қосу нүктесі
├── config.py              # Конфигурация (.env оқиды)
├── requirements.txt       # Python тәуелділіктер
├── migrate.py             # Дерекқор миграциясы
├── seed.py                # Тест деректерін толтыру
├── .env.example           # Конфигурация мысалы
├── database/
│   ├── engine.py          # SQLAlchemy engine
│   ├── models.py          # Дерекқор модельдері
│   └── crud.py            # CRUD операциялары
├── handlers/
│   ├── common.py          # /start, /help командалары
│   ├── user.py            # Қолданушы функциялары
│   ├── payment.py         # Төлем өңдеу
│   └── admin/
│       ├── panel.py       # Админ панелі
│       ├── moderation.py  # Пайдаланушы басқару
│       ├── keys.py        # Кілт басқару
│       └── users.py       # Пайдаланушы ақпараты
├── keyboards/
│   ├── user_kb.py         # Пайдаланушы батырмалары
│   └── admin_kb.py        # Админ батырмалары
├── middlewares/
│   ├── auth.py            # Аутентификация
│   └── rate_limit.py      # Сұраныс шектеу
└── services/
    └── key_allocator.py   # Кілт беру сервисі
```

---

## 🚀 Орнату және іске қосу

### 1. Тәуелділіктерді орнату

```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Конфигурацияны баптау

```bash
cp .env.example .env
```

`.env` файлын ашып, мәліметтерді толтырыңыз:

```env
BOT_TOKEN=your_telegram_bot_token
ADMIN_IDS=[123456789]
KASPI_PHONE=+77XXXXXXXXX
KASPI_RECEIVER=Аты Жөні
```

### 3. Дерекқорды инициализациялау

```bash
python migrate.py
```

### 4. Ботты іске қосу

```bash
python main.py
```

---

## ☁️ Серверге орналастыру (Ubuntu/Debian VPS)

### Systemd сервисі ретінде іске қосу

1. Файлдарды серверге жіберіңіз:
```bash
scp -r "PAY APP BOT/" user@your_server_ip:/home/user/pay-app-bot/
```

2. Серверде орнатыңыз:
```bash
cd /home/user/pay-app-bot
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env  # мәндерді толтырыңыз
python migrate.py
```

3. Systemd сервисін орнатыңыз (`pay-app-bot.service` файлын қараңыз):
```bash
sudo cp pay-app-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable pay-app-bot
sudo systemctl start pay-app-bot
sudo systemctl status pay-app-bot
```

### Логтарды қарау
```bash
sudo journalctl -u pay-app-bot -f
```

---

## 🐳 Docker арқылы іске қосу

```bash
docker build -t pay-app-bot .
docker run -d --env-file .env --name pay-app-bot pay-app-bot
```

---

## 🌐 Railway / Render / Heroku-ға орналастыру

### Railway.app (Тегін хостинг)

1. [Railway.app](https://railway.app) сайтына кіріңіз
2. "New Project" → "Deploy from GitHub repo" таңдаңыз
3. Environment Variables бөлімінде `.env` мәндерін қосыңыз
4. `Procfile` файлы бар болғандықтан автоматты деплой болады

### Render.com

1. [Render.com](https://render.com) сайтына кіріңіз
2. "New Web Service" → GitHub репозиторийін таңдаңыз
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `python main.py`
5. Environment Variables қосыңыз

---

## 📋 Талаптар

- Python 3.10+
- aiogram >= 3.4.1
- SQLAlchemy >= 2.0.29
- aiosqlite >= 0.20.0
- pydantic-settings >= 2.2.1

---

## 🔐 Маңызды ескерту

> ⚠️ `.env` файлын немесе `BOT_TOKEN` мәнін GitHub-қа жүктемеңіз!  
> `.gitignore` файлы `.env` файлдарды автоматты түрде алып тастайды.

---

## 📞 Байланыс

Сұрақтар болса, adminге хабарласыңыз.
