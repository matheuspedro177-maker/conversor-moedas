# Dockerfile
FROM python:3.13-slim

# Define o diretório de trabalho
WORKDIR /app

# Copia os arquivos da API
COPY requirements.txt .
COPY app.py .

# Instala dependências
RUN pip install --no-cache-dir -r requirements.txt

# Exponha a porta da API
EXPOSE 5000

# Comando para rodar a API
CMD ["python", "app.py"]