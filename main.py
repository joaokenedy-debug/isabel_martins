from isabel import app


if __name__ == '__main__':
    # cria o DB e seeds se necessário

    # rodar em debug para desenvolvimento
    app.run(debug=True)