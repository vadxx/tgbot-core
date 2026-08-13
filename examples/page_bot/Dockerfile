FROM python:3.12-slim
WORKDIR /app
# Shared Telegram bot package — the build context is the repo root (../..)
COPY pyproject.toml .
COPY lib/ lib/
RUN pip install --no-cache-dir .
COPY examples/page_bot/ examples/page_bot/
CMD ["python", "-u", "examples/page_bot/bot.py"]
