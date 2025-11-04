from flask import Flask, request, jsonify
import sqlite3
from datetime import datetime

# NOME DA VARIÁVEL: app
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
        c.execute("INSERT INTO licencas VALUES ('12345678900', 'João Silva', '2026-12-31', 'a1b2c3d4e5f6g7h8')")
        c.execute("INSERT INTO licencas VALUES ('98765432100', 'Maria', '2025-11-30', 'x9y8z7w6v5u4t3s2')")
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
        return jsonify({"status": "negado", "motivo": "Dados faltando"}), 400
    conn = sqlite3.connect('licencas.db')
    c = conn.cursor()
    c.execute("SELECT nome, validade, hwid FROM licencas WHERE cpf = ?", (cpf,))
    row = c.fetchone()
    conn.close()
    if not row:
        return jsonify({"status": "negado", "motivo": "CPF não encontrado"}), 403
    nome, validade, hwid_db = row
    hoje = datetime.now().strftime('%Y-%m-%d')
    if validade < hoje:
        return jsonify({"status": "negado", "motivo": "Licença expirada"}), 403
    if hwid != hwid_db:
        return jsonify({"status": "negado", "motivo": "HWID não autorizado"}), 403
    return jsonify({"status": "ativo", "nome": nome})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
