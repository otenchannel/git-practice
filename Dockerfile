FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 PORT=8000 DB_PATH=/data/orders.db
WORKDIR /app
COPY store/ ./store/
RUN useradd -r app && mkdir /data && chown app /data
USER app
EXPOSE 8000
CMD ["python3", "store/app.py"]
