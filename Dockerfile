<<<<<<< HEAD
# 1. Usamos una imagen de Python ligera
FROM python:3.11-slim

# 2. Evitamos que Python genere archivos .pyc y que el buffer se llene
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 3. Directorio de trabajo dentro del contenedor
WORKDIR /app

# 4. Instalamos dependencias del sistema (necesarias para algunos paquetes)
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# 5. Copiamos el archivo de requerimientos e instalamos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copiamos todo el código del backend a la maleta
COPY . .

# 7. Puerto que usa tu aplicación (ajústalo si usas otro, ej: 8000 para FastAPI)
EXPOSE 8000

# 8. Comando para arrancar el backend
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
=======
FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port","8000"]
>>>>>>> e11366450dc900be412f7c6cfe72ffffb0b3c07a
