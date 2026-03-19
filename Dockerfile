FROM python:3.11-slim

# Жұмыс директориясы
WORKDIR /app

# Тәуелділіктерді алдымен орнату (кэш үшін)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Жоба файлдарын көшіру
COPY . .

# .env файлын іске қосу кезінде берген дұрыс (–env-file немесе ENV)
CMD ["python", "main.py"]
