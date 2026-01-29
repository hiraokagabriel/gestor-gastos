#!/usr/bin/env python3
"""
Script de migração para adicionar campos de consolidação no modelo Account

Executar este script UMA VEZ após atualizar o código:
python migrate_accounts_consolidation.py
"""

from app import app
from database import db
from sqlalchemy import text
import sys

def migrate():
    print("=" * 60)
    print("MIGRAÇÃO: Adicionar campos de consolidação em Account")
    print("=" * 60)
    
    with app.app_context():
        try:
            # Verificar se as colunas já existem
            result = db.session.execute(
                text("PRAGMA table_info(accounts)")
            ).fetchall()
            
            columns = [row[1] for row in result]
            print(f"\nColunas existentes na tabela 'accounts': {columns}")
            
            # Adicionar coluna 'consolidated' se não existir
            if 'consolidated' not in columns:
                print("\n[1/2] Adicionando coluna 'consolidated'...")
                db.session.execute(
                    text("ALTER TABLE accounts ADD COLUMN consolidated BOOLEAN DEFAULT 0")
                )
                db.session.commit()
                print("  ✓ Coluna 'consolidated' adicionada com sucesso!")
            else:
                print("\n[1/2] Coluna 'consolidated' já existe. Pulando...")
            
            # Adicionar coluna 'consolidated_date' se não existir
            if 'consolidated_date' not in columns:
                print("\n[2/2] Adicionando coluna 'consolidated_date'...")
                db.session.execute(
                    text("ALTER TABLE accounts ADD COLUMN consolidated_date DATETIME")
                )
                db.session.commit()
                print("  ✓ Coluna 'consolidated_date' adicionada com sucesso!")
            else:
                print("\n[2/2] Coluna 'consolidated_date' já existe. Pulando...")
            
            # Verificar resultado final
            print("\n" + "=" * 60)
            print("VERIFICAÇÃO FINAL")
            print("=" * 60)
            
            result = db.session.execute(
                text("PRAGMA table_info(accounts)")
            ).fetchall()
            
            print("\nEstrutura atualizada da tabela 'accounts':")
            print(f"{'ID':<5} {'Nome':<25} {'Tipo':<15} {'NOT NULL':<10} {'Padrão':<15}")
            print("-" * 70)
            for row in result:
                print(f"{row[0]:<5} {row[1]:<25} {row[2]:<15} {row[3]:<10} {str(row[4] or ''):<15}")
            
            # Contar registros
            count = db.session.execute(text("SELECT COUNT(*) FROM accounts")).scalar()
            print(f"\n  ✓ Total de lançamentos no banco: {count}")
            print(f"  ✓ Todos os lançamentos existentes estão marcados como 'Não Consolidados' por padrão")
            
            print("\n" + "=" * 60)
            print("✓ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
            print("=" * 60)
            print("\nPróximos passos:")
            print("1. Reinicie o servidor Flask")
            print("2. Acesse /accounts para ver o novo sistema")
            print("3. Use os botões 'Consolidar' para marcar lançamentos como pagos/recebidos\n")
            
        except Exception as e:
            print(f"\n✗ ERRO durante a migração: {str(e)}")
            print("\nDetalhes do erro:")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            sys.exit(1)

if __name__ == '__main__':
    migrate()