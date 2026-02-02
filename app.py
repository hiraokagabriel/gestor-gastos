from flask import Flask, render_template
from database import db, init_db
from routes import register_routes
import os

# Importa models ANTES de criar o app/banco para garantir que o SQLAlchemy
# tenha todas as tabelas registradas no metadata antes do create_all().
# (Caso contrário, o SQLite fica sem tabelas e qualquer migração/ALTER falha.)
import models  # noqa: F401

app = Flask(__name__)

# Configurações
app.config['SECRET_KEY'] = 'sua-chave-secreta-aqui-mude-em-producao'

# Usar caminho absoluto para evitar "dois sqlite diferentes" dependendo do diretório onde o app roda.
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'gestor_gastos.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializar banco de dados
init_db(app)

# Registrar rotas
register_routes(app)

@app.route('/')
def index():
    """Página inicial (Agenda)."""
    return render_template('agenda.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
