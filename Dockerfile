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

# Comando final (CMD): Usa 'python -m gunicorn' para garantir que o Gunicorn seja encontrado
# e utiliza a sintaxe de shell dentro do bind para expandir a variável $PORT.
# O Gunicorn agora será iniciado pelo Python, resolvendo o problema de PATH.
CMD ["/bin/sh", "-c", "python -m gunicorn --bind 0.0.0.0:$PORT app:app"]


