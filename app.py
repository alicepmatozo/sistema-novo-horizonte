import sqlite3
import random
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'novo_horizonte_secret_key_prod'

DATABASE = 'banco.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# Inicializar o banco de dados e criar tabelas automaticamente
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Criar tabelas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS unidades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            ativa BOOLEAN DEFAULT 1,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            usuario TEXT NOT NULL UNIQUE,
            senha_hash TEXT NOT NULL,
            cargo TEXT DEFAULT 'Administrador',
            bloqueado BOOLEAN DEFAULT 0,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS solicitacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            protocolo TEXT NOT NULL UNIQUE,
            unidade_id INTEGER NOT NULL,
            unidade_nome TEXT NOT NULL,
            responsavel TEXT NOT NULL,
            data_solicitacao DATETIME DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'Pendente',
            observacoes_gerais TEXT,
            observacoes_admin TEXT,
            FOREIGN KEY (unidade_id) REFERENCES unidades(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS solicitacao_itens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            solicitacao_id INTEGER NOT NULL,
            categoria TEXT NOT NULL,
            produto TEXT NOT NULL,
            quantidade REAL NOT NULL,
            unidade_medida TEXT NOT NULL,
            observacao TEXT,
            FOREIGN KEY (solicitacao_id) REFERENCES solicitacoes(id) ON DELETE CASCADE
        )
    ''')

    # Inserir unidades e admin padrão se não existirem
    cursor.execute("INSERT OR IGNORE INTO unidades (id, nome) VALUES (1, 'Unidade 1 - Central')")
    cursor.execute("INSERT OR IGNORE INTO unidades (id, nome) VALUES (2, 'Unidade 2 - Casa Lar')")
    cursor.execute("INSERT OR IGNORE INTO unidades (id, nome) VALUES (3, 'Unidade 3 - Centro Dia')")

    senha_admin_hash = generate_password_hash('admin123')
    cursor.execute("""
        INSERT OR IGNORE INTO usuarios (id, nome, usuario, senha_hash, cargo) 
        VALUES (1, 'Administrador Geral', 'admin', ?, 'Administrador')
    """, (senha_admin_hash,))

    conn.commit()
    conn.close()

# Executa a inicialização do banco
init_db()

# --- ROTAS DA APLICAÇÃO ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/unidades', methods=['GET'])
def get_unidades():
    conn = get_db_connection()
    unidades = conn.execute("SELECT id, nome FROM unidades WHERE ativa = 1 ORDER BY nome ASC").fetchall()
    conn.close()
    return jsonify([dict(u) for u in unidades])

@app.route('/api/solicitacoes', methods=['POST'])
def criar_solicitacao():
    dados = request.get_json()
    unidade_id = dados.get('unidade_id')
    responsavel = dados.get('responsavel')
    itens = dados.get('itens', [])
    obs_gerais = dados.get('observacoes_gerais', '')
    
    if not unidade_id or not responsavel or not itens:
        return jsonify({'error': 'Unidade, responsável e itens são obrigatórios.'}), 400
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    unidade = cursor.execute("SELECT nome FROM unidades WHERE id = ?", (unidade_id,)).fetchone()
    if not unidade:
        conn.close()
        return jsonify({'error': 'Unidade inválida.'}), 400
    
    protocolo = f"NH-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
    
    cursor.execute("""
        INSERT INTO solicitacoes (protocolo, unidade_id, unidade_nome, responsavel, observacoes_gerais)
        VALUES (?, ?, ?, ?, ?)
    """, (protocolo, unidade_id, unidade['nome'], responsavel, obs_gerais))
    
    solicitacao_id = cursor.lastrowid
    
    for item in itens:
        cursor.execute("""
            INSERT INTO solicitacao_itens (solicitacao_id, categoria, produto, quantidade, unidade_medida, observacao)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (solicitacao_id, item['categoria'], item['produto'], item['quantidade'], item['unidade_medida'], item.get('observacao', '')))
        
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Solicitação enviada com sucesso!', 'protocolo': protocolo}), 201

@app.route('/api/login', methods=['POST'])
def login():
    dados = request.get_json()
    usuario = dados.get('usuario')
    senha = dados.get('senha')
    
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM usuarios WHERE usuario = ? AND bloqueado = 0", (usuario,)).fetchone()
    conn.close()
    
    if user and check_password_hash(user['senha_hash'], senha):
        session['user_id'] = user['id']
        session['user_name'] = user['nome']
        return jsonify({'message': 'Login realizado com sucesso', 'usuario': user['nome']})
    
    return jsonify({'error': 'Usuário ou senha inválidos.'}), 401

if __name__ == '__main__':
    app.run(debug=True, port=5000)