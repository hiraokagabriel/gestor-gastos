from flask import Flask, render_template
from database import db, init_db
from routes import register_routes
import os

app = Flask(__name__)

# Configurações
app.config['SECRET_KEY'] = 'sua-chave-secreta-aqui-mude-em-producao'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gestor_gastos.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializar banco de dados
init_db(app)

# Registrar rotas
register_routes(app)

@app.route('/')
def index():
    """Página inicial"""
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)