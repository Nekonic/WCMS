FROM python:3.13.17-slim
COPY --from=ghcr.io/astral-sh/uv:0.13.3 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app/server
COPY server/pyproject.toml server/uv.lock server/.python-version ./
RUN uv sync --frozen --no-dev
COPY VERSION /app/VERSION
COPY server/ ./
RUN useradd --system --home /app wcms && mkdir /data && chown wcms /data
USER wcms
ENV PATH="/app/server/.venv/bin:$PATH" WCMS_DB_PATH=/data/wcms.sqlite3
EXPOSE 8888
# --ws-max-size: 화면 프레임(계획 06)을 /client/ws로 받으려면 이 값을 올려야 한다
CMD ["sh", "-c", "python manage.py migrate --noinput && exec uvicorn wcms.asgi:application --host 0.0.0.0 --port 8888 --ws-ping-interval 20 --ws-ping-timeout 20 --ws-max-size 1048576"]
