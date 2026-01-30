#!/usr/bin/env python3
"""Migração: colunas de recorrência em accounts.

Este projeto usa SQLite (vide uso de PRAGMA em migrações anteriores).

Execute uma vez após dar pull da branch:
  python migrate_accounts_recorrencia.py

O script é idempotente (se a coluna existir, ele pula).
"""

from app import app
from database import db
from sqlalchemy import text
import sys


def migrate():
    print("=" * 60)
    print("MIGRAÇÃO: Adicionar colunas de recorrência em accounts")
    print("=" * 60)

    with app.app_context():
        try:
            result = db.session.execute(text("PRAGMA table_info(accounts)"))
            rows = result.fetchall()
            columns = [row[1] for row in rows]

            print(f"\nColunas existentes: {columns}")

            # parent_id
            if 'parent_id' not in columns:
                print("\n[1/2] Adicionando coluna parent_id...")
                db.session.execute(text("ALTER TABLE accounts ADD COLUMN parent_id INTEGER"))
                db.session.commit()
                print("  ✓ parent_id adicionada")
            else:
                print("\n[1/2] parent_id já existe. Pulando...")

            # recurring_day
            if 'recurring_day' not in columns:
                print("\n[2/2] Adicionando coluna recurring_day...")
                db.session.execute(text("ALTER TABLE accounts ADD COLUMN recurring_day INTEGER"))
                db.session.commit()
                print("  ✓ recurring_day adicionada")
            else:
                print("\n[2/2] recurring_day já existe. Pulando...")

            print("\n✓ Migração concluída com sucesso.")

        except Exception as e:
            print(f"\n✗ ERRO durante a migração: {str(e)}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            sys.exit(1)


if __name__ == '__main__':
    migrate()
