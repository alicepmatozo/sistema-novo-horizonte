import os
import random
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from supabase import create_client, Client

app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.secret_key = os.environ.get('SECRET_KEY', 'novo_horizonte_secret_key_prod')

SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

def get_supabase() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("SUPABASE_URL e SUPABASE_KEY não estão configuradas nas variáveis de ambiente da Vercel.")
    return create_client(SUPABASE_URL, SUPABASE_KEY)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/unidades', methods=['GET'])
def get_unidades():
    try:
        supabase = get_supabase()
        res = supabase.table('unidades').select('id, nome').eq('ativa', True).order('nome').execute()
        return jsonify(res.data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/solicitacoes', methods=['POST'])
def criar_solicitacao():
    try:
        supabase = get_supabase()
        dados = request.get_json()
        unidade_id = dados.get('unidade_id')
        responsavel = dados.get('responsavel')
        itens = dados.get('itens', [])
        obs_gerais = dados.get('observacoes_gerais', '')

        if not unidade_id or not responsavel or not itens:
            return jsonify({'error': 'Unidade, responsável e itens são obrigatórios.'}), 400

        u_res = supabase.table('unidades').select('nome').eq('id', unidade_id).execute()
        if not u_res.data:
            return jsonify({'error': 'Unidade inválida.'}), 400
        
        unidade_nome = u_res.data[0]['nome']
        protocolo = f"NH-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"

        sol_res = supabase.table('solicitacoes').insert({
            'protocolo': protocolo,
            'unidade_id': unidade_id,
            'unidade_nome': unidade_nome,
            'responsavel': responsavel,
            'observacoes_gerais': obs_gerais
        }).execute()

        sol_id = sol_res.data[0]['id']

        itens_payload = [{
            'solicitacao_id': sol_id,
            'categoria': item['categoria'],
            'produto': item['produto'],
            'quantidade': item['quantidade'],
            'unidade_medida': item['unidade_medida'],
            'observacao': item.get('observacao', '')
        } for item in itens]

        supabase.table('solicitacao_itens').insert(itens_payload).execute()

        return jsonify({'message': 'Solicitação enviada com sucesso!', 'protocolo': protocolo}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    try:
        supabase = get_supabase()
        dados = request.get_json()
        usuario = dados.get('usuario')
        senha = dados.get('senha')

        res = supabase.table('usuarios').select('*').eq('usuario', usuario).eq('bloqueado', False).execute()
        if res.data:
            user = res.data[0]
            if check_password_hash(user['senha_hash'], senha):
                session['user_id'] = user['id']
                session['user_name'] = user['nome']
                return jsonify({'message': 'Login realizado com sucesso', 'usuario': user['nome']})

        return jsonify({'error': 'Usuário ou senha inválidos.'}), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/solicitacoes', methods=['GET'])
def get_solicitacoes_admin():
    try:
        supabase = get_supabase()
        sols = supabase.table('solicitacoes').select('*').order('data_solicitacao', desc=True).execute().data
        for sol in sols:
            itens = supabase.table('solicitacao_itens').select('*').eq('solicitacao_id', sol['id']).execute().data
            sol['itens'] = itens
        return jsonify(sols)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/solicitacoes/<int:id>/status', methods=['PUT'])
def atualizar_status(id):
    try:
        supabase = get_supabase()
        dados = request.get_json()
        novo_status = dados.get('status')
        obs_admin = dados.get('observacao_admin', '')

        supabase.table('solicitacoes').update({
            'status': novo_status,
            'observacoes_admin': obs_admin
        }).eq('id', id).execute()

        return jsonify({'message': 'Status atualizado com sucesso!'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500