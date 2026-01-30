#!/usr/bin/env python3
"""Migração: adicionar colunas de fatura (statement) e auditoria de antecipação em installments.

Execute uma vez após dar pull:
  python migrate_installments_statement_fields.py

Notas:
- Este script depende de as tabelas existirem (models carregadas + create_all).
- Para tornar mais robusto, ele garante db.create_all() antes de tentar ALTER.
"""

from datetime import datetime
from calendar import monthrange

from app import app
from database import db
from models import Transaction, CreditCard
from sqlalchemy import text
from dateutil.relativedelta import relativedelta
import sys


def _add_column_if_missing(table: str, col: str, col_type_sql: str, existing_cols: set[str]):
    if col in existing_cols:
        return False
    db.session.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type_sql}"))
    db.session.commit()
    print(f"  ✓ {table}.{col} adicionada")
    return True


def _compute_first_statement_for_transaction(card: CreditCard, tx_date: datetime):
    closing_day = min(card.closing_day, monthrange(tx_date.year, tx_date.month)[1])
    closing_date = datetime(tx_date.year, tx_date.month, closing_day)

    if tx_date >= closing_date:
        first = datetime(tx_date.year, tx_date.month, 1) + relativedelta(months=1)
    else:
        first = datetime(tx_date.year, tx_date.month, 1)

    return first.month, first.year


def _invoice_due_date(card: CreditCard, month: int, year: int) -> datetime:
    due_day = min(card.due_day, monthrange(year, month)[1])
    return datetime(year, month, due_day)


def migrate():
    print("=" * 60)
    print("MIGRAÇÃO: Colunas statement e auditoria em installments")
    print("=" * 60)

    with app.app_context():
        try:
            # Garante que as tabelas existam antes do ALTER TABLE.
            db.create_all()

            result = db.session.execute(text("PRAGMA table_info(installments)"))
            rows = result.fetchall()
            existing_cols = {row[1] for row in rows}

            print(f"\nColunas existentes: {sorted(existing_cols)}")

            if not existing_cols:
                return jsonify({'error': 'Tabela installments não encontrada. Verifique o banco e se models foram carregadas.'}), 500

            changed = False
            changed |= _add_column_if_missing('installments', 'statement_month', 'INTEGER', existing_cols)
            existing_cols.add('statement_month')
            changed |= _add_column_if_missing('installments', 'statement_year', 'INTEGER', existing_cols)
            existing_cols.add('statement_year')

            changed |= _add_column_if_missing('installments', 'original_statement_month', 'INTEGER', existing_cols)
            existing_cols.add('original_statement_month')
            changed |= _add_column_if_missing('installments', 'original_statement_year', 'INTEGER', existing_cols)
            existing_cols.add('original_statement_year')

            changed |= _add_column_if_missing('installments', 'anticipated_at', 'DATETIME', existing_cols)
            existing_cols.add('anticipated_at')
            changed |= _add_column_if_missing('installments', 'anticipated_from_month', 'INTEGER', existing_cols)
            existing_cols.add('anticipated_from_month')
            changed |= _add_column_if_missing('installments', 'anticipated_from_year', 'INTEGER', existing_cols)
            existing_cols.add('anticipated_from_year')

            if not changed:
                print("\nNenhuma coluna nova foi adicionada.")

            print("\nBackfill: preenchendo statement_month/year para parcelas antigas...")

            txs = Transaction.query.all()
            backfilled = 0

            for tx in txs:
                card = CreditCard.query.get(tx.card_id)
                if not card or not tx.date:
                    continue

                first_m, first_y = _compute_first_statement_for_transaction(card, tx.date)

                for inst in tx.installments:
                    if inst.statement_month and inst.statement_year:
                        continue

                    ref = datetime(first_y, first_m, 1) + relativedelta(months=(inst.installment_number - 1))
                    inst.statement_month = ref.month
                    inst.statement_year = ref.year

                    if not inst.original_statement_month:
                        inst.original_statement_month = inst.statement_month
                    if not inst.original_statement_year:
                        inst.original_statement_year = inst.statement_year

                    inst.due_date = _invoice_due_date(card, inst.statement_month, inst.statement_year)

                    backfilled += 1

            if backfilled:
                db.session.commit()

            print(f"\n✓ Backfill concluído. Parcelas atualizadas: {backfilled}.")
            print("\n✓ Migração concluída com sucesso.")

        except Exception as e:
            print(f"\n✗ ERRO durante a migração: {str(e)}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            sys.exit(1)


if __name__ == '__main__':
    migrate()
