FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
# The service writes its own line per request, so uvicorn's access log is off.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --no-access-log
