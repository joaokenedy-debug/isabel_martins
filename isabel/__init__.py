# app.py (organizado e pronto)
from flask import Flask, render_template, request, redirect, url_for, session, send_file, jsonify, flash, g
import sqlite3
import io
from flask_mail import Mail, Message
import base64
import secrets
import datetime
from functools import wraps
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

from isabel import routes