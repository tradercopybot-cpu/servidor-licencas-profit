from flask import Flask, request, jsonify
import sqlite3
from datetime import datetime
import os
import re

app = Flask(__name__)

# --- BANCO DE DADOS E TABELAS ---
def init_db():
    conn = sqlite3.connect('licencas.db')
    c = conn.cursor()
    
    # Tabela 1: LICENÇAS DOS RECEPTORES (Clientes)
    c.execute('''
        CREATE TABLE IF NOT EXISTS licencas (
            cpf TEXT PRIMARY KEY,
            nome TEXT,
            validade TEXT,
            hwid TEXT
        )
    ''')
    
    # Tabela 2: LICENÇAS DOS EMISSORES (Administradores)
    c.execute('''
        CREATE TABLE IF NOT EXISTS emissores (
            chave_mestra TEXT PRIMARY KEY,
            nome TEXT,
            validade TEXT
        )
    ''')
    
    # --- INSERÇÃO DE DADOS INICIAIS ---
    
    # Clientes de Teste (Receptores)
    c.execute("SELECT COUNT(*) FROM licencas")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO licencas VALUES ('12345678900', 'Wallace Teste', '2026-12-31', 'qualquer')")
        c.execute("INSERT INTO licencas VALUES ('98765432100', 'Maria', '2025-11-30', 'qualquer')")
    
    # Emissor de Teste (Administrador)
    c.execute("SELECT COUNT(*) FROM emissores")
    if c.fetchone()[0] == 0:
        # ATENÇÃO: Esta chave 'CHAVE_ADMIN_MESTRA_DEFAULT' deve ser usada no seu emissor.py
        c.execute("INSERT INTO emissores VALUES ('CHAVE_ADMIN_MESTRA_DEFAULT', 'Admin Master', '2030-01-01')")
        
    conn.commit()
    conn.close()

init_db()

# --- ROTAS GERAIS ---
@app.route('/')
def home():
    return "SERVIDOR DE LICENÇAS PROFIT ONLINE!"

@app.route('/status')
def status():
    conn = sqlite3.connect('licencas.db')
    c = conn.cursor()
    
    hoje = datetime.now().strftime('%Y-%m-%d')
    
    # Lista licenças de Receptores
    c.execute("SELECT nome, cpf, validade FROM licencas")
    licencas_receptores = [{"nome": n, "cpf": c, "validade": v, "status": "Ativo" if v >= hoje else "Expirado"} 
                           for n, c, v in c.fetchall()]

    # Lista licenças de Emissores
    c.execute("SELECT nome, chave_mestra, validade FROM emissores")
    licencas_emissores = [{"nome": n, "chave": c, "validade": v, "status": "Ativo" if v >= hoje else "Expirado"} 
                          for n, c, v in c.fetchall()]
    
    conn.close()
    
    return jsonify({
        "servidor": "Online", 
        "total_receptores": len(licencas_receptores), 
        "licencas_receptores": licencas_receptores,
        "total_emissores": len(licencas_emissores), 
        "licencas_emissores": licencas_emissores
    })

# --- ROTA 1: VALIDAÇÃO DO RECEPTOR (CLIENTE) ---
@app.route('/validar_receptor', methods=['POST']) # ROTA CORRIGIDA
def validar_receptor():
    data = request.get_json()
    cpf = data.get('cpf')
    hwid = data.get('hwid')

    # Validação de dados de entrada
    if not cpf or not hwid:
        return jsonify({"status": "erro", "motivo": "Dados de autenticação faltando (CPF/HWID)."}), 400

    # Normaliza o CPF (remove pontuação, apenas números)
    cpf = re.sub(r'[^0-9]', '', cpf)

    conn = sqlite3.connect('licencas.db')
    c = conn.cursor()
    c.execute("SELECT nome, validade, hwid FROM licencas WHERE cpf = ?", (cpf,))
    row = c.fetchone()
    conn.close()

    if not row:
        return jsonify({"status": "erro", "motivo": "CPF não encontrado ou não cadastrado."}), 403

    nome, validade, hwid_db = row
    hoje = datetime.now().strftime('%Y-%m-%d')

    # Validação de Validade
    if validade < hoje:
        return jsonify({"status": "erro", "motivo": "Licença expirada. Contate o suporte."}), 403

    # Validação de HWID (Se for 'qualquer', aceita. Senão, deve bater.)
    if hwid_db != 'qualquer' and hwid != hwid_db:
        return jsonify({"status": "erro", "motivo": "HWID não autorizado. Licença vinculada a outra máquina."}), 403
    
    # Se o HWID no banco for 'qualquer', o Receptor está tentando o primeiro acesso.
    # Neste ponto, você pode salvar o HWID enviado na primeira vez que o cliente se conecta.
    # Exemplo de lógica para salvar o HWID:
    if hwid_db == 'qualquer':
        conn = sqlite3.connect('licencas.db')
        c = conn.cursor()
        c.execute("UPDATE licencas SET hwid = ? WHERE cpf = ?", (hwid, cpf))
        conn.commit()
        conn.close()

    # Retorno de SUCESSO (Status OK)
    return jsonify({"status": "ok", "nome": nome}), 200

# --- ROTA 2: VALIDAÇÃO DO EMISSOR (ADMINISTRADOR) ---
@app.route('/validar_emissor', methods=['POST'])
def validar_emissor():
    data = request.get_json()
    chave_mestra = data.get('chave_mestra')
    
    if not chave_mestra:
        return jsonify({"status": "erro", "motivo": "Chave Mestra faltando"}), 400

    conn = sqlite3.connect('licencas.db')
    c = conn.cursor()
    c.execute("SELECT nome, validade FROM emissores WHERE chave_mestra = ?", (chave_mestra,))
    row = c.fetchone()
    conn.close()

    if not row:
        return jsonify({"status": "erro", "motivo": "Chave Mestra não encontrada"}), 403

    nome, validade = row
    hoje = datetime.now().strftime('%Y-%m-%d')

    if validade < hoje:
        return jsonify({"status": "erro", "motivo": "Licença do Emissor Expirada"}), 403

    # Retorna OK, permitindo que o emissor inicie
    return jsonify({"status": "ok", "nome": nome}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
