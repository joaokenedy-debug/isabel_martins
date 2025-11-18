from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, jsonify
import sqlite3
import io
import matplotlib.pyplot as plt
import numpy as np
from reportlab.lib.pagesizes import A4, letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from flask_mail import Mail, Message
from io import BytesIO
from reportlab.pdfgen import canvas
from PIL import Image as PILImage
import psycopg2
import base64    
    



app = Flask(__name__)
app.secret_key = "chave_segura"  # necessário para usar session

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
    conn.commit()
    conn.close()


# ========================
# GRUPOS DE PERGUNTAS
# ========================
grupos = {
    "Atendimento": [
        "O funcionário foi educado?",
        "O atendimento foi rápido?",
        "Você se sentiu bem atendido?",
        "O atendente resolveu seu problema?",
        "Você ficou satisfeito com o atendimento?"
    ],
    "Produto": [
        "O produto atendeu às suas expectativas?",
        "O produto chegou em boas condições?",
        "O produto é de boa qualidade?",
        "O produto tem um bom custo-benefício?",
        "Você compraria novamente este produto?"
    ],
    "Entrega": [
        "A entrega foi dentro do prazo?",
        "O pacote chegou em boas condições?",
        "O entregador foi cordial?",
        "Você foi informado sobre o status da entrega?",
        "Você ficou satisfeito com a entrega?"
    ],
    "Suporte": [
        "O suporte respondeu rapidamente?",
        "O suporte foi eficaz na solução?",
        "Você ficou satisfeito com o suporte?",
        "O suporte foi educado?",
        "Você recomendaria o suporte a outros?"
    ],
    "Recomendação": [
        "Você recomendaria nossa loja?",
        "Você voltaria a comprar conosco?",
        "Você acha nossos preços justos?",
        "Você confia na nossa marca?",
        "Você se considera um cliente fiel?"
    ]
}

ordem_grupos = list(grupos.keys())  # para navegação


# ========================
# ROTAS
# ========================



@app.route('/dados')
def inicio():
    session.clear()
    return render_template('dados.html')

@app.route('/')
def index():
    session.clear()
    return render_template('index.html')

@app.route('/salvar_dados', methods=['POST'])
def salvar_dados():
    session['usuario'] = {
        'nome': request.form['nome'],
        'empresa': request.form['empresa'],
        'email': request.form['email'],
        'idade': request.form['idade']
    }
    session['respostas'] = {}
    return redirect(url_for('perguntas', grupo_index=0))


@app.route('/perguntas/<int:grupo_index>', methods=['GET', 'POST'])
def perguntas(grupo_index):
    if 'usuario' not in session:
        return redirect(url_for('inicio'))

    grupo_nome = ordem_grupos[grupo_index]
    perguntas = grupos[grupo_nome]

    # salvar respostas do grupo anterior
    if request.method == 'POST':
        respostas = session['respostas']
        respostas[grupo_nome] = {}
        for pergunta in perguntas:
            valor = request.form.get(pergunta)
            respostas[grupo_nome][pergunta] = 100 if valor == "sim" else 0
        session['respostas'] = respostas

        if grupo_index + 1 < len(ordem_grupos):
            return redirect(url_for('perguntas', grupo_index=grupo_index + 1))
        else:
            return redirect(url_for('finalizar'))

    return render_template('grupo.html', grupo=grupo_nome, perguntas=perguntas, grupo_index=grupo_index, total=len(ordem_grupos))
@app.route("/sobre")
def sobre():
    return render_template("sobre.html")




@app.route('/pdf/<int:usuario_id>')
def gerar_pdf(usuario_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute('SELECT nome, empresa, email, idade FROM usuarios WHERE id = ?', (usuario_id,))
    usuario = c.fetchone()

    c.execute('SELECT grupo, AVG(valor) FROM respostas WHERE usuario_id = ? GROUP BY grupo', (usuario_id,))
    dados = c.fetchall()
    conn.close()

    labels = [d[0] for d in dados]
    medias = [d[1] for d in dados]
    cenario_perfeito = [100 for _ in labels]
    cenario_ideal = [80 for _ in labels]

    # gráfico radar
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
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))

    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)

    # criar pdf
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("<b>Relatório de Avaliação</b>", styles["Title"]))
    story.append(Spacer(1, 20))
    story.append(Paragraph(f"<b>Nome:</b> {usuario[0]}", styles["Normal"]))
    story.append(Paragraph(f"<b>Empresa:</b> {usuario[1]}", styles["Normal"]))
    story.append(Paragraph(f"<b>Email:</b> {usuario[2]}", styles["Normal"]))
    story.append(Paragraph(f"<b>Idade:</b> {usuario[3]}", styles["Normal"]))
    story.append(Spacer(1, 20))
    story.append(Image(buf, width=400, height=400))
    story.append(Spacer(1, 20))
    story.append(Paragraph("Comparativo entre cenários e resultados reais.", styles["Italic"]))

    doc.build(story)
    pdf_buffer.seek(0)

    return send_file(pdf_buffer, as_attachment=True,
                     download_name=f"relatorio_{usuario[0]}.pdf",
                     mimetype='application/pdf')

@app.route('/finalizar')
def finalizar():
    usuario = session.get('usuario')
    respostas = session.get('respostas')

    # salvar no banco
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

    # Gera o PDF (para já deixar pronto)
    gerar_pdf(usuario_id)

    # Limpa sessão
    session.clear()

    # Agora direciona para página de download/envio
    return redirect(url_for('pagina_pdf', usuario_id=usuario_id))
@app.route('/pagina_pdf/<int:usuario_id>')
def pagina_pdf(usuario_id):
    return render_template('finalizar.html', usuario_id=usuario_id)


@app.route('/enviar_email_pdf/<int:usuario_id>', methods=['POST'])
def enviar_email_pdf(usuario_id):
    try:
        # 1️⃣ Buscar dados do usuário no banco
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute('SELECT nome, email FROM usuarios WHERE id = ?', (usuario_id,))
        usuario = c.fetchone()
        conn.close()

        if not usuario:
            return jsonify({"erro": "Usuário não encontrado"}), 404

        nome, email = usuario

        # 2️⃣ Gera o gráfico (exemplo — use os valores reais que você calcula)
        img_buffer = BytesIO()
        categorias = ['Doutrina', 'Comunhão', 'Fé', 'Evangelismo', 'Oração']
        valores = [80, 90, 75, 85, 95]  # 🔹 aqui coloque os valores reais do banco

        fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
        ax.plot(categorias + [categorias[0]], valores + [valores[0]], 'o-', linewidth=2)
        ax.fill(categorias + [categorias[0]], valores + [valores[0]], alpha=0.25)
        plt.savefig(img_buffer, format='png')
        plt.close(fig)
        img_buffer.seek(0)

        # 3️⃣ Gera o PDF com o gráfico embutido
        pdf_buffer = BytesIO()
        pdf = canvas.Canvas(pdf_buffer)
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(100, 780, f"Relatório do Usuário: {nome}")
        pdf.drawInlineImage(PILImage.open(img_buffer), 80, 320, width=400, height=400)
        pdf.save()

        # 4️⃣ Anexa o PDF ao e-mail (em bytes, sem UTF-8)
        pdf_bytes = pdf_buffer.getvalue()
        pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')

        msg = Message(
            subject="Avaliação - Relatório em PDF",
            sender=app.config['MAIL_DEFAULT_SENDER'],
            recipients=[email],
            body=(
                f"Olá {nome},\n\n"
                    "Sou a Dra. Isabel Martins e venho agradecer pela sua participação na nossa avaliação.\n"
                    "Em anexo, você encontrará o seu Relatório de Avaliação, contendo o resumo das respostas e observações.\n\n"
                    "Espero que este material lhe seja útil para acompanhar seu progresso e desenvolvimento.\n\n"
                    "Com carinho,\n"
                    "Dra. Isabel Martins"
            )
        )

        msg.attach(
            "relatorio.pdf",
            "application/pdf",
            base64.b64decode(pdf_base64)
        )

        mail.send(msg)
        print(f"📨 E-mail enviado com sucesso para {email}")
        return jsonify({"status": "ok", "mensagem": "E-mail enviado com sucesso!"})

    except Exception as e:
        print("❌ Erro ao gerar ou enviar PDF:", e)
        return jsonify({"erro": str(e)}), 500
if __name__ == '__main__':
    init_db()
    app.run(debug=True)
