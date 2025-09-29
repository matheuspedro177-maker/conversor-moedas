# Dockerfile
# Usando uma versão estável do Python
FROM python:3.9-slim

# Define o diretório de trabalho
WORKDIR /app

# Copia e instala as dependências (AGORA INCLUI O GUNICORN)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia os arquivos da API
COPY app.py .

# Comando para rodar a API usando o Gunicorn (Servidor de Produção)
# Usando $PORT para maior compatibilidade com Render.
CMD ["gunicorn", "--bind", "0.0.0.0:$PORT", "app:app"]
