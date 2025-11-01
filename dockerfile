# Base Python com acesso root
FROM python:3.10-slim

# Instalar dependências do sistema (poppler e tesseract)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Copiar os arquivos do projeto
WORKDIR /app
COPY . /app

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Porta padrão para Render
EXPOSE 10000

# Rodar o servidor com Gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:10000", "app:app"]
