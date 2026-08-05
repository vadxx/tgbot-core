FROM python:3.12-slim
WORKDIR /app
# Shared Telegram bot package, shipped inside the release tree as tgbot/
COPY tgbot/pyproject.toml /tgbot/pyproject.toml
COPY tgbot/lib/ /tgbot/lib/
RUN pip install --no-cache-dir /tgbot
# Explicit file list — a stray .env in the tree can never leak into the image
COPY bot.py .
COPY handlers.py .
CMD ["python", "-u", "bot.py"]
