from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

db = SQLAlchemy()

def init_db(app):
    """Inicializa o banco de dados"""
    db.init_app(app)
    with app.app_context():
        db.create_all()
        _ensure_accounts_recurrence_columns()

def _table_exists(table_name: str) -> bool:
    row = db.session.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name=:name"),
        {"name": table_name}
    ).fetchone()
    return row is not None

def _ensure_accounts_recurrence_columns():
    """
    Garante colunas necessárias para recorrência em 'accounts' (SQLite).
    Idempotente: se já existir, não faz nada.
    """
    try:
        # Se as models ainda não foram carregadas, a tabela pode não existir.
        if not _table_exists('accounts'):
            return

        rows = db.session.execute(text("PRAGMA table_info(accounts)")).fetchall()
        cols = {row[1] for row in rows}

        changed = False
        if "parent_id" not in cols:
            db.session.execute(text("ALTER TABLE accounts ADD COLUMN parent_id INTEGER"))
            changed = True
            print("🛠️ Auto-migração: adicionada coluna accounts.parent_id")

        if "recurring_day" not in cols:
            db.session.execute(text("ALTER TABLE accounts ADD COLUMN recurring_day INTEGER"))
            changed = True
            print("🛠️ Auto-migração: adicionada coluna accounts.recurring_day")

        if changed:
            db.session.commit()

    except Exception as e:
        db.session.rollback()
        print(f"⚠️ Falha ao checar/aplicar auto-migração em accounts: {e}")
