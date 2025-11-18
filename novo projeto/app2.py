from flask import Flask, render_template, request, redirect, url_for, session, send_file, jsonify
import sqlite3
import io
import matplotlib.pyplot as plt
import numpy as np
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from flask_mail import Mail, Message
from io import BytesIO
from PIL import Image as PILImage
import base64
import secrets
import datetime
from functools import wraps
import pandas as pd
import os

# credenciais (mude para variáveis de ambiente em produção)
ADMIN_USER = os.environ.get('ADMIN_USER', 'joaokenedy')
ADMIN_PASS = os.environ.get('ADMIN_PASS', 'adm321')

def gerar_token_unico():
    return secrets.token_hex(8)  # 16 caracteres seguros


app = Flask(__name__)
app.secret_key = "chave_segura"

# ========================
# CONFIGURAÇÃO DE E-MAIL
# ========================
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'jookenedy88@gmail.com'
app.config['MAIL_PASSWORD'] = 'crnadwfswfkaorxn'  # senha de app do Gmail
app.config['MAIL_DEFAULT_SENDER'] = ('Dra. Isabel Martins', 'jookenedy88@gmail.com')
mail = Mail(app)


# ========================
# BANCO DE DADOS
# ========================
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT,
                    empresa TEXT,
                    email TEXT,
                    idade INTEGER
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS respostas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario_id INTEGER,
                    grupo TEXT,
                    pergunta TEXT,
                    valor INTEGER,
                    FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
                )''')
    
    c.execute('''
                CREATE TABLE IF NOT EXISTS tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    token TEXT UNIQUE,
                    criado_em TIMESTAMP,
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
    
    conn.commit()
    conn.close()


# ========================
# PERGUNTAS
# ========================
perguntas_por_grupo = {
    "Atrair e Selecionar Talentos → Constrói uma equipe homologada e motivada.": [
    "Define claramente o perfil da vaga, especificando conhecimento, comportamento e habilidade",
 	"Alinha a vaga a estratégia da já vigente equipe, pensando no todo",
	"Divulga diretamente as vagas em área e plataformas específicas, se engajando no processo",
	"Avalia assertivamente conhecimentos técnicos necessária ao cargo",
	"Avalia assertivamente comportamento adequado ao cargo",
	"Avalia assertivamente as habilidade necessárias ao cargo",
	"Avalia e identifica traços de alinhamento cultural nos candidatos	Utiliza e compreende análise de 	ferramentas como DISC",
	"Envolve a equipe nas etapas de entrevista, e considera suas opiniões",
	"Avalia e identifica potencial além das experiências já vividas pelo candidato",
 	"Garante  a complementariedade de perfis na equipe, considerando seleção e time vigente",
	"Busca, intencionalmente, perfis diferentes, promovendo a D&I em sua área"

    ],
    "Integrar e Engajar→ Cria conexões rigorosas com a cultura.": [
    "Realiza momento individual,  apresentando pessoalmente a cultura, valores e objetivos da empresa",	"Promove encontros dinâmicos para facilitar a integraçã (almoço, café)	Permite e incetiva a 		 	  participação em treinamentos formais de integração ofertado pela empresa",
 	"Apresentar a estrutura física e todos os que trabalharão diretamente",
 	"Considera o talento natural da pessoa para designar tarefas",
	"Apresenta ao time quais serão suas responsabilidades, deixando todos alinhados",
 	"Realiza reuniões semanais nos primeiros meses para acompanhar o colaborador",
 	"Dá feedback e comemora pequenos avanços dos novatos",
 	"Deixa claro, desde o ingresso, papéis, responsabilidade e metas",
 	"Garante a disponibilidade de  Mentor para acelerar o desenvolvimento",
	"Trata com equidade os novos colaboradores, entendendo e respeitando situações específicas",
	"Adequa seu estilo de liderança a maturidade do colaborador" 

    ],
    "Desenvolver Potenciais → Maximiza os pontos fortes da equipe.": [
    "Realizar Av de Desempenho com todos da equipe.	Dá feedback assertivamente",
	"Constroem, junto com cada colaborador, PDI",
	"Garante o alinhamento do PDI aos desafios e metas dos colaboradores",
 	"Oferta desafios de acordo com o perfil e potencial das pessoas",
 	"Proporciona desafios que tira o time da zona de conforto e acompanha, dando feedback",
 	"Proporciona momentos como cumbuca para desenvolver e garantir o constante desenvolvimento do time",	"Incentiva e acompanha o engajamento da equipe nos treinamentos ofertados pela empresa",
 	"Estimula e patrocina desenvolvimento externo com parceria educacionais",
 	"Usa indicadores claros para avaliar autodesenvolvimento do time",
 	"Insere colaboradores com potencial em reuniões com nível mais elevado, desenvolve-os",
 	"Identifica e desenvo,lve habilidades específicas de acordo com necessidade "
    ],

    "Definir e Acompanhar Resultados → Garantir clareza e entrega.": [
    "Define resultados/metas específicas para todos os cargos",
	"Utiliza planos dde ação com tarefas desdobradas, atribuindo responsáveis",
 	"Define e comunica claramente ao time  prioridades",
 	"Alinha metas individuais com organizacionais, mostrando como a contribuição individual impacta no 	todo",	
	"Usa ferramentas de acompanhamento como sistema ou dashboards",
	"Realiza reuniões regulares de acompanhamento de atividades e metas",
	"Identifica e remove barreiras, resolvendo problemas que facilitarão a entrega de metas pelo time",
    "Fornece orientação ao time, dado feedback positivo e negativo constantemente",
 	"Adapta as metas ao contexto, revisando-as se necessário",
	"Fomenta a responsabilidade individual, trabalhando o protagonismo de cada um com o resultado final",
 	"Celebra com o time conquistas alcançadas",
 	"Robustece metas ano após ano, elevando a entrega do time"

    ],
    "Comunicar com Propósito → Alinha e inspirar com foco.": [
    "Compartilha informações de forma clara, sem ambiguidade e garante que o time saiba primeiro por ele",	"Pede feedback a todos do time em cada RI, demonstrando uma escuta aberta e ativa",
 	"Alinha os comunicados a culta da empresa, sempre fomentando missão e valores",
 	"Adapta sua linguagem ao grupo, preocupando-se com a compreensão",
 	"Comunica expectativas de forma clara, garantindo que todos saibam exatamente o que é esperado de cada 	um",
 	"Proporciona momento de partilha de histórias, conhecendo a equipe e associando e fortalecendo a 	cultura",
 	"Possui um rotina fixa para Reuniões Individuais com cada colaborador, para proporcionar feedback",	"Possui rotina de reuniões sistemáticas com todos os colaboradores para acompanhar projetos e alinhar 	expectativas",
 	"Usa ferramentas como intranet para otimizar comunicação sempre que necessário",
 	"Possui e aplica habilidade em gestão de conflitos",
 	"Proporciona momentos informais com foco em inspirar o time, sempre alinhado a cultura",
 	"Associa todas as suas falas e comportamentos a cultura e propósito da empresa" 

    ],
	"Reconhecer e Impulsionar → Motivar e acelerar o desempenho.": [
    "Sempre reconhece de forma verbal, escrita ou reuniões conquistas do time ",
	 "Ajusta a abordagem do reconhecimento ao perfil de cada colaborador ",
	 "Possui rituais de celebração na área para comemorar resultados ",
 	 "Proporciona recompensas homologas ao desempenho sempre que possível (Bônus, folgas)	Compartilha conquista do time com pares e empresa, proporcionando visibilidade ",
 	 "Reconhece erros como parte do processo, dando feedback e acompanhando. 	Garante que os desafios estão sempre alinhados a estratégia organizacional ",
 	 "Propõe metas ambiciosas com suporte necessário ",
 	 "Seguindo normas interna, adequa benefícios as particularidades dos colaboradores ",
 	 "Demonstra publicamente gratidão ao time sempre que possível ",
 	 "Reconhece e fomenta produtividade através do equilíbrio entre vida pessoal e profisisonal ",
 	 "Possui pessoas encarreiradas na empresa formadas por ele. " 

    ]

}





# ========================
# FUNÇÃO AUXILIAR: GERA PDF (para download e e-mail)
# ========================
def gerar_pdf_bytes(usuario_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT nome, empresa, email, idade FROM usuarios WHERE id = ?', (usuario_id,))
    usuario = c.fetchone()

    c.execute('SELECT grupo, AVG(valor) FROM respostas WHERE usuario_id = ? GROUP BY grupo', (usuario_id,))
    dados = c.fetchall()
    conn.close()

    if not usuario or not dados:
        raise ValueError("Usuário ou dados não encontrados.")

    nome, empresa, email, idade = usuario
    labels = [d[0] for d in dados]
    medias = [d[1] for d in dados]

    # Cenários
    cenario_perfeito = [100] * len(labels)
    cenario_ideal = [80] * len(labels)

    # Configurações do gráfico radar
    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    medias += medias[:1]
    cenario_perfeito += cenario_perfeito[:1]
    cenario_ideal += cenario_ideal[:1]
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(6,6), subplot_kw=dict(polar=True))
    ax.plot(angles, cenario_perfeito, 'g-', linewidth=2, label='Cenário Perfeito (100%)')
    ax.plot(angles, cenario_ideal, 'orange', linestyle='--', linewidth=2, label='Cenário Ideal (80%)')
    ax.plot(angles, medias, 'b-', linewidth=2, label='Respostas Reais')
    ax.fill(angles, medias, 'b', alpha=0.25)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))

    # Salvar o gráfico em memória
    img_buf = io.BytesIO()
    plt.savefig(img_buf, format='png', bbox_inches='tight')
    plt.close(fig)
    img_buf.seek(0)

    # Criar o PDF
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("<b>Relatório de Avaliação</b>", styles["Title"]),
        Spacer(1, 20),
        Paragraph(f"<b>Nome:</b> {nome}", styles["Normal"]),
        Paragraph(f"<b>Empresa:</b> {empresa}", styles["Normal"]),
        Paragraph(f"<b>Email:</b> {email}", styles["Normal"]),
        Paragraph(f"<b>Idade:</b> {idade}", styles["Normal"]),
        Spacer(1, 20),
        Image(img_buf, width=400, height=400),
        Spacer(1, 20),
        Paragraph("Comparativo entre cenários e resultados reais.", styles["Italic"])
    ]

    doc.build(story)
    pdf_buffer.seek(0)
    return pdf_buffer


# ========================
# ROTAS
# ========================




@app.route('/')
def index():
    session.clear()
    return render_template('index.html')

@app.route('/dados')
def inicio():
    if not session.get("acesso_autorizado"):
        return redirect(url_for("login_token"))

    session.clear()
    return render_template('dados.html')

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# ---------- ADMIN LOGIN ----------
@app.route('/admin/login', methods=['GET','POST'])
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


# ---------- ADMIN DASHBOARD ----------
@app.route('/admin')
@admin_required
def admin_dashboard():
    conn = get_db_connection()
    usuarios = conn.execute("SELECT id, nome, email, empresa, idade FROM usuarios ORDER BY id DESC").fetchall()
    conn.close()
    return render_template('admin/dashboard.html', usuarios=usuarios)


# ---------- BAIXAR/ENVIAR PDF (reaproveita suas funções existentes) ----------
@app.route('/admin/pdf/<int:usuario_id>')
@admin_required
def admin_pdf_download(usuario_id):
    # Se você tem pdf_download() reutilize:
    return pdf_download(usuario_id)

@app.route('/admin/email/<int:usuario_id>', methods=['POST'])
@admin_required
def admin_email_pdf(usuario_id):
    # Reaproveita sua função de envio por e-mail
    # pode enviar para o email cadastrado do usuário
    return enviar_email_pdf(usuario_id)


# ---------- EXPORTAR EXCEL ----------
@app.route('/admin/excel')
@admin_required
def admin_excel():
    conn = get_db_connection()
    # pega usuarios + respostas (exemplo simples)
    df_users = pd.read_sql_query("SELECT * FROM usuarios", conn)
    df_resps = pd.read_sql_query("SELECT * FROM respostas", conn)
    conn.close()

    # junta em um excel com duas abas
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_users.to_excel(writer, sheet_name='usuarios', index=False)
        df_resps.to_excel(writer, sheet_name='respostas', index=False)
    output.seek(0)

    return send_file(output,
                     as_attachment=True,
                     download_name='dados_completos.xlsx',
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


# ---------- CRUD DE PERGUNTAS ----------
@app.route('/admin/perguntas')
@admin_required
def admin_perguntas():
    conn = get_db_connection()
    perguntas = conn.execute("SELECT * FROM perguntas ORDER BY grupo, id").fetchall()
    conn.close()
    return render_template('admin/perguntas.html', perguntas=perguntas)

@app.route('/admin/perguntas/add', methods=['POST'])
@admin_required
def admin_pergunta_add():
    grupo = request.form.get('grupo')
    texto = request.form.get('texto')
    if not grupo or not texto:
        flash('Grupo e texto são obrigatórios', 'error')
        return redirect(url_for('admin_perguntas'))
    conn = get_db_connection()
    conn.execute("INSERT INTO perguntas (grupo, texto) VALUES (?, ?)", (grupo, texto))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_perguntas'))

@app.route('/admin/perguntas/edit/<int:id>', methods=['POST'])
@admin_required
def admin_pergunta_edit(id):
    texto = request.form.get('texto')
    conn = get_db_connection()
    conn.execute("UPDATE perguntas SET texto = ? WHERE id = ?", (texto, id))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_perguntas'))

@app.route('/admin/perguntas/delete/<int:id>', methods=['POST'])
@admin_required
def admin_pergunta_delete(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM perguntas WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_perguntas'))
@app.route("/admin/grupos/excluir/<grupo>", methods=["POST"])
def admin_excluir_grupo(grupo):
    try:
        conn = get_db_connection()

        # Apaga todas as perguntas do grupo
        conn.execute("DELETE FROM perguntas WHERE grupo = ?", (grupo,))

        # Opcional: também excluir respostas associadas ao grupo
        # conn.execute("DELETE FROM respostas WHERE grupo = ?", (grupo,))

        conn.commit()
        conn.close()

        flash(f"Grupo '{grupo}' excluído com sucesso.", "success")
        return redirect(url_for("admin_perguntas"))

    except Exception as e:
        print("Erro ao excluir grupo:", e)
        flash("Erro ao excluir grupo.", "error")
        return redirect(url_for("admin_perguntas"))

@app.route('/sobre')
def sobre():
    return render_template('sobre.html')

@app.route('/salvar_dados', methods=['POST'])
def salvar_dados():
    nome = request.form['nome']
    empresa = request.form['empresa']
    email = request.form['email']
    idade = request.form['idade']

    # ✅ criar usuário antes das perguntas
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("""
        INSERT INTO usuarios (nome, empresa, email, idade)
        VALUES (?, ?, ?, ?)
    """, (nome, empresa, email, idade))
    usuario_id = c.lastrowid
    conn.commit()
    conn.close()

    # ✅ salvar ID e dados na sessão
    session['usuario_id'] = usuario_id
    session['usuario'] = {
        'nome': nome,
        'empresa': empresa,
        'email': email,
        'idade': idade
    }

    # ✅ redirecionar para o grupo 0
    return redirect(url_for('perguntas', grupo_index=0))


@app.route("/gerar_token", methods=["GET", "POST"])
def gerar_token():
    token = None

    if request.method == "POST":
        novo_token = gerar_token_unico()
        agora = datetime.datetime.now()

        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("INSERT INTO tokens (token, criado_em) VALUES (?, ?)", (novo_token, agora))
        conn.commit()
        conn.close()

        token = novo_token

    return render_template("gerar_token.html", token=token)


@app.route("/login_token", methods=["GET", "POST"])
def login_token():
    if request.method == "POST":
        token_digitado = request.form.get("token")

        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("SELECT id, token, criado_em, expirado FROM tokens WHERE token = ?", (token_digitado,))
        token_data = c.fetchone()
        conn.close()

        if not token_data:
            flash("Token inválido.", "error")
            return redirect(url_for("login_token"))

        token_id, token_valor, criado_em, expirado = token_data

        # Verifica se já foi usado
        if expirado == 1:
            flash("Este token já foi utilizado.", "error")
            return redirect(url_for("login_token"))

        # Verifica validade de tempo (24h)
        criado_em = datetime.datetime.fromisoformat(criado_em)
        if datetime.datetime.now() - criado_em > datetime.timedelta(hours=24):
            flash("O token expirou (24h).", "error")
            return redirect(url_for("login_token"))

        # ✅ Token válido — marcar como consumido
        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("UPDATE tokens SET expirado = 1 WHERE id = ?", (token_id,))
        conn.commit()
        conn.close()

        # ✅ Permitir acesso ao formulário
        session["acesso_autorizado"] = True

        return redirect(url_for("inicio"))  # vai para os dados pessoais

    return render_template("login_token.html")
@app.route('/perguntas/<int:grupo_index>', methods=['GET', 'POST'])
def perguntas(grupo_index):

    # Garantir que o usuário existe na sessão
    if 'usuario_id' not in session:
        return redirect(url_for('inicio'))

    usuario_id = session['usuario_id']
    conn = get_db()

    # ✅ BUSCAR TODOS OS GRUPOS DISTINTOS
    grupos_db = conn.execute("""
        SELECT DISTINCT grupo FROM perguntas ORDER BY grupo
    """).fetchall()

    grupos_nomes = [g['grupo'] for g in grupos_db]

    # ✅ SE NÃO EXISTE NENHUM GRUPO → ERRO
    if not grupos_nomes:
        return "Nenhuma pergunta cadastrada.", 500

    # ✅ SE ACABARAM OS GRUPOS → IR PARA FINALIZAÇÃO
    if grupo_index >= len(grupos_nomes):
        return redirect(url_for('pagina_pdf', usuario_id=usuario_id))

    grupo_atual = grupos_nomes[grupo_index]

    # ✅ BUSCAR AS PERGUNTAS DO GRUPO ATUAL
    perguntas_db = conn.execute("""
        SELECT texto FROM perguntas
        WHERE grupo = ?
        ORDER BY id
    """, (grupo_atual,)).fetchall()

    perguntas_lista = [p["texto"] for p in perguntas_db]

    if request.method == 'POST':

        # ✅ SALVAR TODAS AS RESPOSTAS DO GRUPO ATUAL
        for pergunta in perguntas_lista:
            resposta = request.form.get(pergunta)

            # NÃO LANÇA ERRO SE FALTAR ALGUMA MARCAÇÃO
            if resposta is None:
                continue

            # Converter resposta para inteiro: sim = 1, não = 0
            valor = 1 if resposta.lower() == "sim" else 0

            conn.execute("""
                INSERT INTO respostas (usuario_id, grupo, pergunta, valor)
                VALUES (?, ?, ?, ?)
            """, (usuario_id, grupo_atual, pergunta, valor))

        conn.commit()

        # ✅ IR PARA O PRÓXIMO GRUPO
        return redirect(url_for('perguntas', grupo_index=grupo_index + 1))

    # ✅ RENDERIZAR O FORMULARIO DO GRUPO
    return render_template(
        'form.html',
        grupo=grupo_atual,
        perguntas=perguntas_lista,
        grupo_index=grupo_index,
        total=len(grupos_nomes)
    )

@app.route('/finalizar')
def finalizar():
    usuario = session.get('usuario')
    respostas = session.get('respostas')

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('INSERT INTO usuarios (nome, empresa, email, idade) VALUES (?, ?, ?, ?)',
              (usuario['nome'], usuario['empresa'], usuario['email'], usuario['idade']))
    usuario_id = c.lastrowid

    for grupo, perguntas in respostas.items():
        for pergunta, valor in perguntas.items():
            c.execute('INSERT INTO respostas (usuario_id, grupo, pergunta, valor) VALUES (?, ?, ?, ?)',
                      (usuario_id, grupo, pergunta, valor))
    conn.commit()
    conn.close()

    session.clear()
    return redirect(url_for('pagina_pdf', usuario_id=usuario_id))


@app.route('/pagina_pdf/<int:usuario_id>')
def pagina_pdf(usuario_id):
    return render_template('finalizar.html', usuario_id=usuario_id)


# ✅ PDF PARA DOWNLOAD
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



# ✅ ENVIO POR E-MAIL
@app.route('/enviar_email_pdf/<int:usuario_id>', methods=['POST'])
def enviar_email_pdf(usuario_id):
    try:
        pdf_buffer = gerar_pdf_bytes(usuario_id)
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute('SELECT nome, email FROM usuarios WHERE id = ?', (usuario_id,))
        usuario = c.fetchone()
        conn.close()

        if not usuario:
            return jsonify({"erro": "Usuário não encontrado"}), 404

        nome, email = usuario

        msg = Message(
            subject="Avaliação - Relatório em PDF",
            sender=app.config['MAIL_DEFAULT_SENDER'],
            recipients=[email],
            body=(
                f"Olá {nome},\n\n"
                "Sou a Dra. Isabel Martins e venho agradecer pela sua participação na nossa avaliação.\n"
                "Em anexo, você encontrará o seu Relatório de Avaliação, contendo o resumo das respostas e observações.\n\n"
                "Com carinho,\nDra. Isabel Martins"
            )
        )
        msg.attach(f"relatorio_{nome}.pdf", "application/pdf", pdf_buffer.getvalue())
        mail.send(msg)

        return jsonify({"status": "ok", "mensagem": "E-mail enviado com sucesso!"})
    except Exception as e:
        print("❌ Erro ao enviar:", e)
        return jsonify({"erro": str(e)}), 500


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
