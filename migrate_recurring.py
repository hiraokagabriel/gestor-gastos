#!/usr/bin/env python3
"""
Script de migração para adicionar campos de recorrência no modelo Account

Executar UMA VEZ após atualizar o código:
python migrate_recurring.py
"""

from app import app
from database import db
from sqlalchemy import text
import sys

def migrate():
    print("="*70)
    print(" MIGRAÇÃO: Sistema de Recorrência Aprimorado")
    print("="*70)
    print()
    print("Este script adicionará os seguintes campos na tabela 'accounts':")
    print("  - parent_id (relacionamento pai-filho)")
    print("  - recurring_day (dia do mês para recorrência)")
    print()
    
    with app.app_context():
        try:
            # Verificar estrutura atual
            result = db.session.execute(
                text("PRAGMA table_info(accounts)")
            ).fetchall()
            
            columns = [row[1] for row in result]
            print(f"Colunas existentes: {', '.join(columns)}")
            print()
            
            # Adicionar parent_id
            if 'parent_id' not in columns:
                print("[1/2] Adicionando coluna 'parent_id'...")
                db.session.execute(
                    text("ALTER TABLE accounts ADD COLUMN parent_id INTEGER")
                )
                db.session.commit()
                print("  ✓ Coluna 'parent_id' adicionada!")
            else:
                print("[1/2] ✓ Coluna 'parent_id' já existe")
            
            # Adicionar recurring_day
            if 'recurring_day' not in columns:
                print("[2/2] Adicionando coluna 'recurring_day'...")
                db.session.execute(
                    text("ALTER TABLE accounts ADD COLUMN recurring_day INTEGER")
                )
                db.session.commit()
                print("  ✓ Coluna 'recurring_day' adicionada!")
            else:
                print("[2/2] ✓ Coluna 'recurring_day' já existe")
            
            print()
            print("="*70)
            print(" VERIFICAÇÃO FINAL")
            print("="*70)
            
            # Mostrar estrutura final
            result = db.session.execute(
                text("PRAGMA table_info(accounts)")
            ).fetchall()
            
            print()
            print("Estrutura atualizada da tabela 'accounts':")
            print(f"{'ID':<5} {'Nome':<25} {'Tipo':<15} {'NOT NULL':<10} {'Padrão':<15}")
            print("-"*70)
            for row in result:
                print(f"{row[0]:<5} {row[1]:<25} {row[2]:<15} {row[3]:<10} {str(row[4] or ''):<15}")
            
            # Estatísticas
            count = db.session.execute(text("SELECT COUNT(*) FROM accounts")).scalar()
            recurring_count = db.session.execute(
                text("SELECT COUNT(*) FROM accounts WHERE recurring = 1")
            ).scalar()
            
            print()
            print(f"  ✓ Total de lançamentos: {count}")
            print(f"  ✓ Lançamentos recorrentes existentes: {recurring_count}")
            
            print()
            print("="*70)
            print(" ✓ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
            print("="*70)
            print()
            print("PRÓXIMOS PASSOS:")
            print("1. Reinicie o servidor Flask")
            print("2. Acesse /accounts")
            print("3. Crie um novo lançamento marcando 'Recorrente'")
            print("4. O sistema criará automaticamente os próximos 12 meses")
            print("5. Use o botão 'Deletar Série' para remover todas as instâncias")
            print()
            
        except Exception as e:
            print()
            print(f"✗ ERRO: {str(e)}")
            print()
            print("Detalhes:")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            sys.exit(1)

if __name__ == '__main__':
    migrate()