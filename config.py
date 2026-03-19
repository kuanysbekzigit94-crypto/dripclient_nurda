import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ⚠️ Барлық мәндер .env файлында болуы КЕРЕК
    # ⚠️ All values MUST be set in .env file
    bot_token: str                          # BOT_TOKEN=...
    admin_ids: list[int] = []               # ADMIN_IDS=[123456789]
    admin_usernames: list[str] = []         # ADMIN_USERNAMES=["admin1", "admin2"]
    admin_phones: list[str] = []            # ADMIN_PHONES=["+77012345678"]
    admin_password: str = "AdminDrip2026"   # ADMIN_PASSWORD=Our Secret Password
    kaspi_phone: str = ""                   # KASPI_PHONE=+77...
    kaspi_receiver: str = ""                # KASPI_RECEIVER=Аты Жөні
    database_url: str = "sqlite+aiosqlite:///database.db"

    # Optional links
    official_website: str = "https://example.com"
    download_link: str = "https://example.com/download"
    telegram_channel: str = "https://t.me/your_channel"
    contact_admin: str = "https://t.me/your_admin"

    # GitHub sync (persistent storage for Render free plan)
    github_token: str = ""              # GITHUB_TOKEN=ghp_...
    github_repo: str = ""               # GITHUB_REPO=username/repo-name
    github_db_file: str = "database.json"  # path inside the repo

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

config = Settings()
