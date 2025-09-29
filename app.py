from flask import Flask, request, jsonify, render_template_string
import requests
import redis
import json

app = Flask(__name__)

API_KEY = '2da6e97f5ff1cdf4b2e4f612'  # sua chave da API

# Função para gerar URL da API com base na moeda de origem
def get_url(moeda_origem):
    return f'https://v6.exchangerate-api.com/v6/{API_KEY}/latest/{moeda_origem}'

# Conectar ao Redis (nome do serviço no docker-compose é 'redis')
cache = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)

@app.route('/')
def index():
    return jsonify({'mensagem': 'API Conversor de Moedas funcionando com cotação real! 🚀'})

@app.route('/converter', methods=['GET'])
def converter():
    valor = request.args.get('valor', type=float)
    origem = request.args.get('origem', type=str)
    destino = request.args.get('destino', type=str)

    if valor is None or origem is None or destino is None:
        return jsonify({'erro': 'Informe valor, origem e destino'}), 400

    origem = origem.upper()
    destino = destino.upper()

    # Verifica cache primeiro
    chave_cache = f"{valor}_{origem}_{destino}"
    resultado_cache = cache.get(chave_cache)
    if resultado_cache:
        return jsonify(json.loads(resultado_cache))

    # Buscar as taxas atuais com base na moeda de origem
    try:
        resposta = requests.get(get_url(origem), timeout=5)
        resposta.raise_for_status()
        dados = resposta.json()
    except requests.RequestException:
        return jsonify({'erro': 'Não foi possível consultar a cotação'}), 500

    if dados.get('result') != 'success':
        return jsonify({'erro': 'Erro na resposta da API externa'}), 500

    taxas = dados['conversion_rates']

    if destino not in taxas:
        return jsonify({'erro': 'Moeda inválida. Use códigos válidos como USD, EUR, BRL'}), 400

    # Converter valor
    valor_convertido = valor * taxas[destino]

    resultado = {
        'valor_original': valor,
        'moeda_origem': origem,
        'moeda_destino': destino,
        'valor_convertido': round(valor_convertido, 2)
    }

    # Salvar no cache por 1 hora
    cache.setex(chave_cache, 3600, json.dumps(resultado))

    return jsonify(resultado)


# NOVO ENDPOINT COM HTML

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Conversor de Moedas</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f4f6f8; color: #333; text-align: center; padding: 40px; }
        .card { background: white; border-radius: 12px; box-shadow: 0px 4px 10px rgba(0,0,0,0.1); padding: 20px; display: inline-block; }
        h1 { color: #2c3e50; }
        .valor { font-size: 24px; font-weight: bold; margin: 20px 0; }
    </style>
</head>
<body>
    <div class="card">
        <h1>💱 Conversão de Moedas</h1>
        <p><b>Moeda Origem:</b> {{ moeda_origem }}</p>
        <p><b>Moeda Destino:</b> {{ moeda_destino }}</p>
        <p><b>Valor Original:</b> {{ valor_original }}</p>
        <p class="valor">➡ {{ valor_convertido }} {{ moeda_destino }}</p>
    </div>
</body>
</html>
"""

@app.route('/converter_html', methods=['GET'])
def converter_html():
    valor = request.args.get('valor', type=float)
    origem = request.args.get('origem', type=str)
    destino = request.args.get('destino', type=str)

    if valor is None or origem is None or destino is None:
        return "Informe valor, origem e destino", 400

    origem = origem.upper()
    destino = destino.upper()

    try:
        resposta = requests.get(get_url(origem), timeout=5)
        resposta.raise_for_status()
        dados = resposta.json()
    except requests.RequestException:
        return "Erro ao consultar cotação", 500

    if dados.get('result') != 'success':
        return "Erro na resposta da API externa", 500

    taxas = dados['conversion_rates']
    if destino not in taxas:
        return "Moeda inválida. Use USD, EUR, BRL", 400

    valor_convertido = round(valor * taxas[destino], 2)

    return render_template_string(
        HTML_TEMPLATE,
        moeda_origem=origem,
        moeda_destino=destino,
        valor_original=valor,
        valor_convertido=valor_convertido
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)