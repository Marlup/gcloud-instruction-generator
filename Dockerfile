FROM python:3.13-slim

# Instalar dependencias básicas
RUN apt-get update && apt-get install -y \
    curl gcc g++ git \
    && rm -rf /var/lib/apt/lists/*

# Instalar Google Cloud SDK
RUN curl -sSL https://sdk.cloud.google.com | bash -s -- --disable-prompts --install-dir=/usr/local/gcloud
ENV PATH=$PATH:/usr/local/gcloud/google-cloud-sdk/bin

# Instalar dependencias Python
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código de la app
COPY . /app

# Variables de entorno para credenciales
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/keys/service-account.json

CMD ["python", "app.py"]
