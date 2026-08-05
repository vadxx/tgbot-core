FROM python:3.12-slim
WORKDIR /app
# Shared Telegram bot package — the build context is the repo root (../..)
COPY pyproject.toml .
COPY lib/ lib/
RUN pip install --no-cache-dir .
COPY examples/echo_bot/ examples/echo_bot/
CMD ["python", "-u", "examples/echo_bot/bot.py"]
