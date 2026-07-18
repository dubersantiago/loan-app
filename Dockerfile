FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Carpeta donde vivirá la base de datos SQLite (se monta como volumen)
RUN mkdir -p /app/data
ENV DB_PATH=/app/data/prestamo.db

EXPOSE 8000

CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:8000", "app:app"]
