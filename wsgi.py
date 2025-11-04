from flask import Flask, request, jsonify
import sqlite3
from datetime import datetime
import os  # <-- ADICIONADO

app = Flask(__name__)

# --- BANCO ---
def init_db():
    conn = sqlite3.connect('licencas.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS licencas (
            cpf TEXT PRIMARY KEY,
            nome TEXT,
            validade TEXT,
            hwid TEXT
        )
    ''')
    c.execute("SELECT COUNT(*) FROM licencas")
    if c.fetchone()[0] == 0:
        # HWID = 'qualquer' para aceitar qualquer máquina
        c.execute("INSERT INTO licencas VALUES ('12345678900', 'Wallace Teste', '2026-12-31', 'qualquer')")
        c.execute("INSERT INTO licencas VALUES ('98765432100', 'Maria', '2025-11-30', 'qualquer')")
    conn.commit()
    conn.close()

init_db()

# --- ROTAS ---
@app.route('/')
def home():
    return "SERVIDOR DE LICENÇAS PROFIT ONLINE!"

@app.route('/status')
def status():
    conn = sqlite3.connect('licencas.db')
    c = conn.cursor()
    c.execute("SELECT nome, cpf, validade FROM licencas")
    rows = c.fetchall()
    conn.close()
    hoje = datetime.now().strftime('%Y-%m-%d')
    licencas = []
    for nome, cpf, validade in rows:
        status = "Ativo" if validade >= hoje else "Expirado"
        licencas.append({"nome": nome, "cpf": cpf, "validade": validade, "status": status})
    return jsonify({"servidor": "Online", "total": len(licencas), "licencas": licencas})

@app.route('/validar', methods=['POST'])
def validar():
    data = request.get_json()
    cpf = data.get('cpf')
    hwid = data.get('hwid')

    if not cpf or not hwid:
        return jsonify({"valido": False, "motivo": "Dados faltando"}), 400

    conn = sqlite3.connect('licencas.db')
    c = conn.cursor()
    c.execute("SELECT nome, validade, hwid FROM licencas WHERE cpf = ?", (cpf,))
    row = c.fetchone()
    conn.close()

    if not row:
        return jsonify({"valido": False, "motivo": "CPF não encontrado"}), 403

    nome, validade, hwid_db = row
    hoje = datetime.now().strftime('%Y-%m-%d')

    if validade < hoje:
        return jsonify({"valido": False, "motivo": "Licença expirada"}), 403

    # ACEITA QUALQUER HWID SE FOR 'qualquer'
    if hwid_db != 'qualquer' and hwid != hwid_db:
        return jsonify({"valido": False, "motivo": "HWID não autorizado"}), 403

    return jsonify({"valido": True, "nome": nome})  # <-- FORMATO QUE O BOT ESPERA

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))  # <-- USA PORTA DO RENDER
    app.run(host='0.0.0.0', port=port, debug=False)
