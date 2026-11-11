import os, secrets, hmac, requests
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, jsonify, session

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "")
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                  SESSION_COOKIE_SECURE=bool(os.environ.get("VERCEL")))

SB_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SB_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
STATUS = ["Pendente", "Em análise", "Aprovada", "Em separação", "Atendida", "Recusada"]


def sb(method, table, params=None, body=None, prefer=None):
    h = {"apikey": SB_KEY, "Authorization": f"Bearer {SB_KEY}", "Content-Type": "application/json"}
    if prefer:
        h["Prefer"] = prefer
    return requests.request(method, f"{SB_URL}/rest/v1/{table}", headers=h,
                            params=params, json=body, timeout=15)


def login_required(f):
    @wraps(f)
    def w(*a, **k):
        if not session.get("admin"):
            return jsonify(error="Não autorizado."), 401
        return f(*a, **k)
    return w


@app.errorhandler(requests.RequestException)
def erro_rede(e):
    return jsonify(error="Falha ao falar com o banco de dados."), 502


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/unidades")
def unidades():
    r = sb("GET", "unidades", {"select": "id,nome", "ativa": "eq.true", "order": "nome"})
    return (jsonify(r.json()), 200) if r.ok else (jsonify(error="Erro no banco."), 502)


@app.route("/api/solicitacoes", methods=["POST"])
def criar():
    d = request.get_json(silent=True) or {}
    resp = str(d.get("responsavel", "")).strip()[:100]
    itens_in = d.get("itens") or []
    try:
        uid = int(d.get("unidade_id"))
    except (TypeError, ValueError):
        return jsonify(error="Unidade inválida."), 400
    if not resp or not itens_in or len(itens_in) > 100:
        return jsonify(error="Informe responsável e ao menos um item."), 400

    itens = []
    for i in itens_in:
        try:
            q = float(i.get("quantidade"))
        except (TypeError, ValueError):
            return jsonify(error="Quantidade inválida."), 400
        cat, prod, um = (str(i.get(k, "")).strip() for k in ("categoria", "produto", "unidade_medida"))
        if q <= 0 or q > 99999999 or not (cat and prod and um):
            return jsonify(error="Preencha produto, quantidade e medida de todos os itens."), 400
        itens.append({"categoria": cat[:50], "produto": prod[:100], "quantidade": q,
                      "unidade_medida": um[:20], "observacao": str(i.get("observacao", ""))[:255]})

    u = sb("GET", "unidades", {"select": "nome", "id": f"eq.{uid}", "ativa": "eq.true"})
    if not u.ok or not u.json():
        return jsonify(error="Unidade inválida."), 400

    for _ in range(3):
        proto = f"NH-{datetime.now():%Y%m%d}-{secrets.token_hex(3).upper()}"
        r = sb("POST", "solicitacoes", body={
            "protocolo": proto, "unidade_id": uid, "unidade_nome": u.json()[0]["nome"],
            "responsavel": resp, "observacoes_gerais": str(d.get("observacoes_gerais", ""))[:1000]},
            prefer="return=representation")
        if r.status_code != 409:
            break
    if not r.ok:
        return jsonify(error="Não foi possível salvar."), 502
    sid = r.json()[0]["id"]
    ri = sb("POST", "solicitacao_itens", body=[dict(it, solicitacao_id=sid) for it in itens])
    if not ri.ok:
        sb("DELETE", "solicitacoes", {"id": f"eq.{sid}"})
        return jsonify(error="Não foi possível salvar os itens."), 502
    return jsonify(message="Solicitação enviada!", protocolo=proto), 201


@app.route("/api/login", methods=["POST"])
def login():
    d = request.get_json(silent=True) or {}
    ok_u = hmac.compare_digest(str(d.get("usuario", "")), os.environ.get("ADMIN_USER", "\0"))
    ok_s = hmac.compare_digest(str(d.get("senha", "")), os.environ.get("ADMIN_PASSWORD", "\0"))
    if ok_u and ok_s:
        session["admin"] = True
        return jsonify(message="ok")
    return jsonify(error="Usuário ou senha inválidos."), 401


@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify(message="ok")


@app.route("/api/admin/solicitacoes")
@login_required
def listar():
    r = sb("GET", "solicitacoes", {"select": "*,solicitacao_itens(*)",
                                   "order": "data_solicitacao.desc", "limit": "200"})
    return (jsonify(r.json()), 200) if r.ok else (jsonify(error="Erro no banco."), 502)


@app.route("/api/admin/solicitacoes/<int:sid>", methods=["PATCH"])
@login_required
def atualizar(sid):
    d = request.get_json(silent=True) or {}
    upd = {}
    if d.get("status") in STATUS:
        upd["status"] = d["status"]
    if "observacoes_admin" in d:
        upd["observacoes_admin"] = str(d["observacoes_admin"])[:1000]
    if not upd:
        return jsonify(error="Nada para atualizar."), 400
    r = sb("PATCH", "solicitacoes", {"id": f"eq.{sid}"}, upd)
    return (jsonify(message="ok"), 200) if r.ok else (jsonify(error="Erro no banco."), 502)


if __name__ == "__main__":
    app.run(debug=False, port=5000)
