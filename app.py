import os
import json
from flask import Flask, request, jsonify, render_template_string
import requests

# ----------------------------------------------------
# Configuração do Ambiente e Serviços
# ----------------------------------------------------

# Tenta importar e conectar ao Redis (torna o cache opcional)
# Removida a chamada cache.ping() para evitar bloqueios na inicialização
try:
    import redis
    # Usa a variável de ambiente REDIS_HOST ou 'redis' (padrão do Docker Compose)
    cache_host = os.getenv('REDIS_HOST', 'redis')
    cache = redis.Redis(host=cache_host, port=6379, db=0, decode_responses=True)
    
    # Tentamos apenas uma operação simples para confirmar a conexão sem ser bloqueante
    cache.set('startup_test', '1') 
    cache.delete('startup_test')
    
    CACHE_ATIVO = True
    print("✅ Redis: Cache ativo e conectado.")
except (ImportError, redis.exceptions.ConnectionError, AttributeError):
    # Se falhar, desativa o cache e permite que a API continue funcionando
    cache = None
    CACHE_ATIVO = False
    print("⚠️ Redis: Cache desativado. Redis não encontrado ou inacessível. O app continuará funcionando.")
    
app = Flask(__name__)

# SEGURANÇA: Carrega a API_KEY de uma variável de ambiente 'EXCHANGE_RATE_API_KEY'.
# Use a chave hardcoded apenas como fallback DE TESTE, mas NUNCA em produção.
API_KEY = os.getenv('EXCHANGE_RATE_API_KEY', '2da6e97f5ff1cdf4b2e4f612') 

# ----------------------------------------------------
# Funções de Suporte
# ----------------------------------------------------

def get_url(moeda_origem):
    """Gera a URL da API externa de taxa de câmbio."""
    return f'https://v6.exchangerate-api.com/v6/{API_KEY}/latest/{moeda_origem}'

# ----------------------------------------------------
# Endpoint JSON (/converter)
# ----------------------------------------------------

@app.route('/')
def index():
    return jsonify({
        'mensagem': 'API Conversor de Moedas funcionando! 🚀', 
        'cache_status': 'ativo' if CACHE_ATIVO else 'inativo'
    })

@app.route('/converter', methods=['GET'])
def converter():
    valor = request.args.get('valor', type=float)
    origem = request.args.get('origem', type=str)
    destino = request.args.get('destino', type=str)

    # Verifica se todos os parâmetros necessários foram fornecidos
    if not all([valor, origem, destino]):
        return jsonify({'erro': 'Informe valor, origem e destino nos parâmetros da query (ex: /converter?valor=100&origem=USD&destino=BRL)'}), 400

    origem = origem.upper()
    destino = destino.upper()

    # ESTRATÉGIA OTIMIZADA: Chave de cache baseada apenas nas moedas,
    # para armazenar a taxa de câmbio, não o resultado final.
    chave_cache = f"taxa_{origem}_{destino}"
    taxa_cambio = None
    cached = False
    
    # Tenta buscar a taxa de câmbio no cache primeiro
    if CACHE_ATIVO:
        try:
            taxa_cambio_str = cache.get(chave_cache)
            if taxa_cambio_str:
                taxa_cambio = float(taxa_cambio_str)
                cached = True
        except Exception as e:
            print(f"Erro ao buscar cache: {e}")
            
    # Se a taxa de câmbio não foi encontrada no cache, busca na API externa
    if taxa_cambio is None:
        try:
            resposta = requests.get(get_url(origem), timeout=8)
            resposta.raise_for_status() # Lança exceção para status 4xx/5xx
            dados = resposta.json()
        except requests.RequestException as e:
            print(f"Erro na requisição à API externa: {e}")
            return jsonify({'erro': 'Não foi possível consultar a cotação. Verifique a moeda de origem ou conexão de rede.'}), 500

        if dados.get('result') != 'success':
            return jsonify({'erro': 'Erro na resposta da API externa. Verifique se a moeda de origem é válida.'}), 500

        taxas = dados.get('conversion_rates', {})

        if destino not in taxas:
            return jsonify({'erro': 'Moeda de destino inválida. Use códigos válidos (ex: USD, EUR, BRL)'}), 400
        
        taxa_cambio = taxas[destino]

        # Salva a taxa de câmbio no cache por 1 hora (3600 segundos)
        if CACHE_ATIVO:
            try:
                cache.setex(chave_cache, 3600, str(taxa_cambio)) 
            except Exception as e:
                print(f"Erro ao salvar cache: {e}")

    # Converter valor
    valor_convertido = valor * taxa_cambio

    resultado = {
        'valor_original': valor,
        'moeda_origem': origem,
        'moeda_destino': destino,
        'taxa_cambio': taxa_cambio,
        'valor_convertido': round(valor_convertido, 2),
        'cached': cached
    }

    return jsonify(resultado)

# ----------------------------------------------------
# Endpoint HTML (/converter_html)
# ----------------------------------------------------

# Template HTML com Tailwind CSS para melhor estética
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Conversor de Moedas</title>
    <!-- Usa Tailwind CSS para styling moderno e responsivo -->
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
        body { font-family: 'Inter', sans-serif; background: #1f2937; color: #f3f4f6; padding: 40px; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
    </style>
</head>
<body>
    <!-- Card de resultado centralizado -->
    <div class="bg-gray-800 p-8 rounded-xl shadow-2xl max-w-sm w-full border border-gray-700 text-center">
        <h1 class="text-3xl font-bold text-yellow-400 mb-8 flex items-center justify-center">
            <span class="mr-2">💱</span> Conversão de Moeda
        </h1>
        
        <div class="text-left space-y-3 p-4 bg-gray-700 rounded-lg">
            <p class="text-lg font-medium text-gray-300">Valor de Partida:</p>
            <p class="text-3xl font-bold text-white">
                {{ valor_original }} <span class="text-yellow-400">{{ moeda_origem }}</span>
            </p>
            <p class="text-sm text-gray-400 border-t border-gray-600 pt-3">Taxa (1 {{ moeda_origem }}): {{ taxa_cambio }} {{ moeda_destino }}</p>
        </div>
        
        <div class="mt-8">
            <p class="text-2xl text-gray-300 font-light">Resultado da Conversão:</p>
            <p class="text-6xl font-extrabold text-green-400 mt-2 tracking-tight">
                {{ valor_convertido }}
            </p>
            <p class="text-2xl font-semibold text-green-400 mt-1">{{ moeda_destino }}</p>
        </div>
        
        <p class="text-xs text-gray-500 mt-8">
            Cotação {{ 'armazenada em cache' if cached else 'obtida em tempo real' }}.
        </p>
    </div>
</body>
</html>
"""

@app.route('/converter_html', methods=['GET'])
def converter_html():
    valor = request.args.get('valor', type=float)
    origem = request.args.get('origem', type=str)
    destino = request.args.get('destino', type=str)

    # Função de template para erros
    def html_error(status_code, message):
        return render_template_string(
            f"""
            <div class="text-center p-8 bg-red-100 text-red-800 rounded-lg">
                <h1 class="text-3xl font-bold mb-4">Erro {status_code}</h1>
                <p class="text-lg">{message}</p>
            </div>
            """
        ), status_code

    if not all([valor, origem, destino]):
        return html_error(400, "Informe valor, origem e destino nos parâmetros da query."), 400

    origem = origem.upper()
    destino = destino.upper()
    
    chave_cache = f"taxa_{origem}_{destino}"
    taxa_cambio = None
    cached = False
    
    # Tenta buscar do cache
    if CACHE_ATIVO:
        try:
            taxa_cambio_str = cache.get(chave_cache)
            if taxa_cambio_str:
                taxa_cambio = float(taxa_cambio_str)
                cached = True
        except Exception:
            pass # Ignora erros de cache

    # Se não houver taxa no cache, busca na API externa
    if taxa_cambio is None:
        try:
            resposta = requests.get(get_url(origem), timeout=8)
            resposta.raise_for_status()
            dados = resposta.json()
        except requests.RequestException:
            return html_error(500, "Não foi possível consultar a cotação. Erro de rede ou servidor."), 500

        if dados.get('result') != 'success':
            return html_error(500, "Erro na resposta da API externa. Moeda de origem inválida?"), 500

        taxas = dados.get('conversion_rates', {})
        if destino not in taxas:
            return html_error(400, "Moeda de destino inválida. Use códigos válidos (ex: USD, EUR, BRL)"), 400
        
        taxa_cambio = taxas[destino]

        # Salva no cache
        if CACHE_ATIVO:
            try:
                cache.setex(chave_cache, 3600, str(taxa_cambio)) 
            except Exception:
                pass # Ignora erros de cache
            
    valor_convertido = round(valor * taxa_cambio, 2)

    return render_template_string(
        HTML_TEMPLATE,
        moeda_origem=origem,
        moeda_destino=destino,
        valor_original=valor,
        valor_convertido=valor_convertido,
        taxa_cambio=round(taxa_cambio, 4),
        cached=cached
    )

if __name__ == '__main__':
    # Define a porta de execução. Em produção, use a variável de ambiente, se necessário.
    port = int(os.environ.get('PORT', 5000))
    host = '0.0.0.0'
    print(f"🚀 Iniciando servidor Flask em http://{host}:{port}")
    app.run(host=host, port=port, debug=True)
