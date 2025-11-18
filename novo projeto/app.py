# app.py (organizado e pronto)
from flask import Flask, render_template, request, redirect, url_for, session, send_file, jsonify, flash, g
import sqlite3
import io
import matplotlib.pyplot as plt
import numpy as np
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from flask_mail import Mail, Message
from io import BytesIO
from PIL import Image as PILImage
import base64
import secrets
import datetime
from functools import wraps
import pandas as pd
import os

# ---------------------------
# Config
# ---------------------------
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "chave_segura_local")

DATABASE = os.environ.get("DATABASE_FILE", "database.db")

# Mail (use variáveis de ambiente em produção)
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True') == 'True'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'jookenedy88@gmail.com')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'crnadwfswfkaorxn')  # troque por var env
app.config['MAIL_DEFAULT_SENDER'] = (os.environ.get('MAIL_SENDER_NAME', 'Dra. Isabel Martins'),
                                    os.environ.get('MAIL_SENDER_EMAIL', app.config['MAIL_USERNAME']))
mail = Mail(app)

# Admin credenciais (troque em produção!)
ADMIN_USER = os.environ.get('ADMIN_USER', 'joaokenedy')
ADMIN_PASS = os.environ.get('ADMIN_PASS', 'adm321')


# ---------------------------
# Database helpers
# ---------------------------
def get_db():
    if 'db' not in g:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        g.db = conn
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()


# ---------------------------
# Init DB (create tables + seed perguntas if empty)
# ---------------------------
def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    # users and answers and tokens and perguntas
    c.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            empresa TEXT,
            email TEXT,
            idade INTEGER
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS respostas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            grupo TEXT,
            pergunta TEXT,
            valor INTEGER,
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT UNIQUE,
            criado_em TEXT,
            expirado INTEGER DEFAULT 0
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS perguntas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grupo TEXT NOT NULL,
            texto TEXT NOT NULL
        )
    ''')

    # seed example: only insert if table empty
    c.execute('SELECT COUNT(*) FROM perguntas')
    count = c.fetchone()[0]
    if count == 0:
        # exemplo reduzido — substitua ou expanda conforme precisa
        seed = [
            ("Atendimento", "O funcionário foi educado?"),
            ("Atendimento", "O atendimento foi rápido?"),
            ("Produto", "O produto atendeu às suas expectativas?"),
            ("Entrega", "A entrega foi dentro do prazo?"),
            ("Suporte", "O suporte respondeu rapidamente?"),
            ("Recomendação", "Você recomendaria nossa loja?")
        ]
        c.executemany("INSERT INTO perguntas (grupo, texto) VALUES (?, ?)", seed)

    conn.commit()
    conn.close()


# ---------------------------
# Utilitários
# ---------------------------
def gerar_token_unico():
    return secrets.token_hex(8)  # 16 chars

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated


# ---------------------------
# Geração de PDF (retorna BytesIO)
# ---------------------------
def gerar_pdf_bytes(usuario_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Buscar usuário
    c.execute('SELECT nome, empresa, email, idade FROM usuarios WHERE id = ?', (usuario_id,))
    usuario = c.fetchone()

    # Buscar respostas
    c.execute('SELECT grupo, AVG(valor) FROM respostas WHERE usuario_id = ? GROUP BY grupo', (usuario_id,))
    dados = c.fetchall()
    conn.close()

    if not usuario or not dados:
        raise ValueError("Usuário ou dados não encontrados.")

    nome, empresa, email, idade = usuario

    labels = [d[0] for d in dados]
    medias = [d[1] * 100 for d in dados]  # transforma em percentual

    import numpy as np
    import matplotlib.pyplot as plt

    # Cenários
    cenario_perfeito = [100] * len(labels)
    cenario_ideal = [80] * len(labels)

    # Radar chart – ajuste
    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()

    medias += medias[:1]
    cenario_perfeito += cenario_perfeito[:1]
    cenario_ideal += cenario_ideal[:1]
    angles += angles[:1]

    # Gráfico
    fig, ax = plt.subplots(figsize=(6,6), subplot_kw=dict(polar=True))
    ax.plot(angles, cenario_perfeito, linewidth=2, label='Cenário Perfeito (100%)')
    ax.plot(angles, cenario_ideal, linestyle='--', linewidth=2, label='Cenário Ideal (80%)')
    ax.plot(angles, medias, linewidth=2, label='Resultado')
    ax.fill(angles, medias, alpha=0.25)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    ax.set_yticks([0,20,40,60,80,100])
    ax.legend(loc='upper right', bbox_to_anchor=(1.3,1.1))

    img_buf = io.BytesIO()
    plt.savefig(img_buf, format='png', bbox_inches='tight')
    plt.close(fig)
    img_buf.seek(0)

    # Criar PDF
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=A4)
    styles = getSampleStyleSheet()

    story = [
        Paragraph("<b>Relatório de Avaliação</b>", styles["Title"]),
        Spacer(1, 15),
        Paragraph(f"<b>Nome:</b> {nome}", styles["Normal"]),
        Paragraph(f"<b>Empresa:</b> {empresa}", styles["Normal"]),
        Paragraph(f"<b>Email:</b> {email}", styles["Normal"]),
        Paragraph(f"<b>Idade:</b> {idade}", styles["Normal"]),
        Spacer(1, 20),

        # ✅ Aqui a correção principal:
        RLImage(img_buf, width=400, height=400),


        Spacer(1, 20),
        Paragraph("Comparativo entre o cenário ideal, perfeito e resultado obtido.", styles["Italic"])
    ]

    doc.build(story)
    pdf_buffer.seek(0)
    return pdf_buffer


# ---------------------------
# ROTAS PÚBLICAS
# ---------------------------
@app.route('/')
def index():
    # limpar sessão para novo fluxo
    session.pop('usuario_id', None)
    session.pop('usuario', None)
    session.pop('acesso_autorizado', None)
    return render_template('index.html')


@app.route('/dados')
def inicio():
    # exige token validado previamente
    if not session.get("acesso_autorizado"):
        return redirect(url_for("login_token"))
    return render_template('dados.html')


@app.route('/salvar_dados', methods=['POST'])
def salvar_dados():
    if not session.get("acesso_autorizado"):
        return redirect(url_for("login_token"))
    nome = request.form.get('nome')
    empresa = request.form.get('empresa')
    email = request.form.get('email')
    idade = request.form.get('idade')

    if not nome or not email:
        flash("Nome e email são obrigatórios.", "error")
        return redirect(url_for('inicio'))

    db = get_db()
    cur = db.cursor()
    cur.execute("INSERT INTO usuarios (nome, empresa, email, idade) VALUES (?, ?, ?, ?)",
                (nome, empresa, email, idade))
    db.commit()
    usuario_id = cur.lastrowid

    # salvar na sessão
    session['usuario_id'] = usuario_id
    session['usuario'] = {'nome': nome, 'empresa': empresa, 'email': email, 'idade': idade}

    return redirect(url_for('perguntas', grupo_index=0))


# Token pages
@app.route('/admin/gerar_token', methods=['GET', 'POST'])
def gerar_token():
    token = None
    if request.method == 'POST':
        novo = gerar_token_unico()
        agora = datetime.datetime.now().isoformat()
        db = get_db()
        db.execute("INSERT INTO tokens (token, criado_em) VALUES (?, ?)", (novo, agora))
        db.commit()
        token = novo
    return render_template('admin/gerar_token.html', token=token)


@app.route('/login_token', methods=['GET', 'POST'])
def login_token():
    if request.method == 'POST':
        token_digitado = request.form.get('token')
        db = get_db()
        cur = db.execute("SELECT id, token, criado_em, expirado FROM tokens WHERE token = ?", (token_digitado,))
        token_row = cur.fetchone()
        if not token_row:
            flash("Token inválido.", "error")
            return redirect(url_for('login_token'))

        token_id = token_row['id']
        criado_em = token_row['criado_em']
        expirado = token_row['expirado']

        if expirado == 1:
            flash("Esse token já foi usado.", "error")
            return redirect(url_for('login_token'))

        # checar validade 24h
        try:
            criado_dt = datetime.datetime.fromisoformat(criado_em)
        except Exception:
            criado_dt = datetime.datetime.now()  # fallback
        if datetime.datetime.now() - criado_dt > datetime.timedelta(hours=24):
            flash("Token expirado (24h).", "error")
            return redirect(url_for('login_token'))

        # consumir token
        db.execute("UPDATE tokens SET expirado = 1 WHERE id = ?", (token_id,))
        db.commit()

        session['acesso_autorizado'] = True
        flash("Acesso autorizado. Preencha seus dados.", "success")
        return redirect(url_for('inicio'))

    return render_template('login_token.html')


# Perguntas por grupo (rota revisada)
@app.route('/perguntas/<int:grupo_index>', methods=['GET', 'POST'])
def perguntas(grupo_index):
    # precisa ter iniciado dados (usuario_id)
    if 'usuario_id' not in session:
        flash("Complete seus dados antes de responder.", "error")
        return redirect(url_for('inicio'))

    usuario_id = session['usuario_id']
    db = get_db()

    # obter grupos existentes
    grupos_rows = db.execute("SELECT DISTINCT grupo FROM perguntas ORDER BY grupo").fetchall()
    grupos_nomes = [r['grupo'] for r in grupos_rows]

    if not grupos_nomes:
        return "Nenhuma pergunta cadastrada.", 500

    if grupo_index >= len(grupos_nomes):
        return redirect(url_for('pagina_pdf', usuario_id=usuario_id))

    grupo_atual = grupos_nomes[grupo_index]
    perguntas_rows = db.execute("SELECT texto FROM perguntas WHERE grupo = ? ORDER BY id", (grupo_atual,)).fetchall()
    perguntas_lista = [r['texto'] for r in perguntas_rows]

    if request.method == 'POST':
        for pergunta in perguntas_lista:
            resposta = request.form.get(pergunta)
            if resposta is None:
                continue
            valor = 1 if resposta.lower() == "sim" else 0
            db.execute("INSERT INTO respostas (usuario_id, grupo, pergunta, valor) VALUES (?, ?, ?, ?)",
                       (usuario_id, grupo_atual, pergunta, valor))
        db.commit()
        return redirect(url_for('perguntas', grupo_index=grupo_index + 1))

    return render_template('form.html', grupo=grupo_atual, perguntas=perguntas_lista,
                           grupo_index=grupo_index, total=len(grupos_nomes))


@app.route('/pagina_pdf/<int:usuario_id>')
def pagina_pdf(usuario_id):
    return render_template('finalizar.html', usuario_id=usuario_id)


@app.route('/pdf/<int:usuario_id>')
def pdf_download(usuario_id):
    try:
        pdf_buffer = gerar_pdf_bytes(usuario_id)
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=f"relatorio_{usuario_id}.pdf",
            mimetype='application/pdf'
        )
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@app.route('/enviar_email_pdf/<int:usuario_id>', methods=['POST'])
def enviar_email_pdf(usuario_id):
    try:
        pdf_buffer = gerar_pdf_bytes(usuario_id)

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT nome, email FROM usuarios WHERE id = ?", (usuario_id,))
        usuario = c.fetchone()
        conn.close()

        if not usuario:
            return jsonify({"erro": "Usuário não encontrado"}), 404

        nome, email = usuario

        msg = Message(
            subject="Relatório de Avaliação",
            recipients=[email],
            body=(
                f"Olá {nome},\n\n"
                "Aqui está o seu relatório em PDF.\n\n"
                "Atenciosamente,\n"
                "Dra. Isabel Martins"
            )
        )

        msg.attach(
            f"relatorio_{usuario_id}.pdf",
            "application/pdf",
            pdf_buffer.getvalue()
        )

        mail.send(msg)

        return jsonify({"status": "ok", "mensagem": "E-mail enviado com sucesso!"})

    except Exception as e:
        print("Erro ao enviar email:", e)
        return jsonify({"erro": str(e)}), 500



# ---------------------------
# ADMIN
# ---------------------------
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        user = request.form.get('user')
        pwd = request.form.get('password')
        if user == ADMIN_USER and pwd == ADMIN_PASS:
            session['admin_logged'] = True
            return redirect(url_for('admin_dashboard'))
        return render_template('admin/login.html', erro='Usuário ou senha incorretos')
    return render_template('admin/login.html')

@app.route('/admin/logout')
@admin_required
def admin_logout():
    session.pop('admin_logged', None)
    return redirect(url_for('admin_login'))

@app.route('/admin')
@admin_required
def admin_dashboard():
    db = get_db()
    usuarios = db.execute("SELECT id, nome, email, empresa, idade FROM usuarios ORDER BY id DESC").fetchall()
    return render_template('admin/dashboard.html', usuarios=usuarios)

@app.route('/admin/pdf/<int:usuario_id>')
@admin_required
def admin_pdf_download(usuario_id):
    # reaproveita gerar_pdf_bytes
    try:
        buf = gerar_pdf_bytes(usuario_id)
        return send_file(buf, as_attachment=True, download_name=f"relatorio_{usuario_id}.pdf",
                         mimetype='application/pdf')
    except Exception as e:
        flash("Erro ao gerar PDF: " + str(e), "error")
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/email/<int:usuario_id>', methods=['POST'])
@admin_required
def admin_email_pdf(usuario_id):
    # reutiliza enviar_email_pdf
    return enviar_email_pdf(usuario_id)

@app.route('/admin/excel')
@admin_required
def admin_excel():
    db = get_db()
    df_users = pd.read_sql_query("SELECT * FROM usuarios", db)
    df_resps = pd.read_sql_query("SELECT * FROM respostas", db)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_users.to_excel(writer, sheet_name='usuarios', index=False)
        df_resps.to_excel(writer, sheet_name='respostas', index=False)
    output.seek(0)
    return send_file(output, as_attachment=True, download_name='dados_completos.xlsx',
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


# Perguntas CRUD + listar grupos
@app.route('/admin/perguntas')
@admin_required
def admin_perguntas():
    db = get_db()
    perguntas = db.execute("SELECT * FROM perguntas ORDER BY grupo, id").fetchall()
    grupos = db.execute("SELECT grupo, COUNT(*) as total FROM perguntas GROUP BY grupo ORDER BY grupo").fetchall()
    return render_template('admin/perguntas.html', perguntas=perguntas, grupos=grupos)

@app.route('/admin/perguntas/add', methods=['POST'])
@admin_required
def admin_pergunta_add():
    grupo = request.form.get('grupo')
    texto = request.form.get('texto')
    if not grupo or not texto:
        flash('Grupo e texto são obrigatórios', 'error')
        return redirect(url_for('admin_perguntas'))
    db = get_db()
    db.execute("INSERT INTO perguntas (grupo, texto) VALUES (?, ?)", (grupo, texto))
    db.commit()
    flash('Pergunta adicionada.', 'success')
    return redirect(url_for('admin_perguntas'))

@app.route('/admin/perguntas/edit/<int:id>', methods=['POST'])
@admin_required
def admin_pergunta_edit(id):
    texto = request.form.get('texto')
    db = get_db()
    db.execute("UPDATE perguntas SET texto = ? WHERE id = ?", (texto, id))
    db.commit()
    flash('Pergunta atualizada.', 'success')
    return redirect(url_for('admin_perguntas'))

@app.route('/admin/perguntas/delete/<int:id>', methods=['POST'])
@admin_required
def admin_pergunta_delete(id):
    db = get_db()
    db.execute("DELETE FROM perguntas WHERE id = ?", (id,))
    db.commit()
    flash('Pergunta excluída.', 'success')
    return redirect(url_for('admin_perguntas'))

@app.route('/admin/grupos/excluir/<grupo>', methods=['POST'])
@admin_required
def admin_excluir_grupo(grupo):
    try:
        db = get_db()
        db.execute("DELETE FROM perguntas WHERE grupo = ?", (grupo,))
        db.commit()
        flash(f"Grupo '{grupo}' excluído com sucesso.", "success")
    except Exception as e:
        print("Erro ao excluir grupo:", e)
        flash("Erro ao excluir grupo.", "error")
    return redirect(url_for('admin_perguntas'))


# ---------------------------
# Sobre
# ---------------------------
@app.route('/sobre')
def sobre():
    return render_template('sobre.html')


# ---------------------------
# Main
# ---------------------------
if __name__ == '__main__':
    # cria o DB e seeds se necessário
    init_db()
  
    app.run(host="0.0.0.0", port=8080)

