#!/usr/bin/env python3
"""
Script de migração para adicionar campos de recorrência aprimorados

EXECUTAR ESTE SCRIPT UMA VEZ:
python migrate_recurrence_system.py
"""

from app import app
from database import db
from sqlalchemy import text
import sys

def migrate():
    print("=" * 70)
    print("MIGRAÇÃO: Sistema de Recorrência Aprimorado")
    print("=" * 70)
    
    with app.app_context():
        try:
            # Verificar estrutura atual
            result = db.session.execute(
                text("PRAGMA table_info(accounts)")
            ).fetchall()
            
            columns = [row[1] for row in result]
            print(f"\nColunas atuais: {', '.join(columns)}")
            
            changes_made = False
            
            # 1. Adicionar parent_id
            if 'parent_id' not in columns:
                print("\n[1/3] Adicionando coluna 'parent_id'...")
                db.session.execute(
                    text("ALTER TABLE accounts ADD COLUMN parent_id INTEGER")
                )
                db.session.commit()
                print("  ✓ Coluna 'parent_id' adicionada!")
                changes_made = True
            else:
                print("\n[1/3] Coluna 'parent_id' já existe.")
            
            # 2. Adicionar recurring_day
            if 'recurring_day' not in columns:
                print("\n[2/3] Adicionando coluna 'recurring_day'...")
                db.session.execute(
                    text("ALTER TABLE accounts ADD COLUMN recurring_day INTEGER")
                )
                db.session.commit()
                print("  ✓ Coluna 'recurring_day' adicionada!")
                changes_made = True
            else:
                print("\n[2/3] Coluna 'recurring_day' já existe.")
            
            # 3. Verificar/adicionar consolidated e consolidated_date
            if 'consolidated' not in columns:
                print("\n[3/3] Adicionando coluna 'consolidated'...")
                db.session.execute(
                    text("ALTER TABLE accounts ADD COLUMN consolidated BOOLEAN DEFAULT 0")
                )
                db.session.commit()
                print("  ✓ Coluna 'consolidated' adicionada!")
                changes_made = True
            else:
                print("\n[3/3] Coluna 'consolidated' já existe.")
            
            if 'consolidated_date' not in columns:
                print("\n[Bonus] Adicionando coluna 'consolidated_date'...")
                db.session.execute(
                    text("ALTER TABLE accounts ADD COLUMN consolidated_date DATETIME")
                )
                db.session.commit()
                print("  ✓ Coluna 'consolidated_date' adicionada!")
                changes_made = True
            else:
                print("\n[Bonus] Coluna 'consolidated_date' já existe.")
            
            # Verificar resultado final
            print("\n" + "=" * 70)
            print("VERIFICAÇÃO FINAL")
            print("=" * 70)
            
            result = db.session.execute(
                text("PRAGMA table_info(accounts)")
            ).fetchall()
            
            print("\nEstrutura da tabela 'accounts':")
            print(f"{'ID':<5} {'Nome':<25} {'Tipo':<15} {'NOT NULL':<10}")
            print("-" * 60)
            for row in result:
                print(f"{row[0]:<5} {row[1]:<25} {row[2]:<15} {row[3]:<10}")
            
            # Estatísticas
            stats = db.session.execute(
                text("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN recurring = 1 THEN 1 ELSE 0 END) as recurring_origins,
                    SUM(CASE WHEN parent_id IS NOT NULL THEN 1 ELSE 0 END) as recurring_children,
                    SUM(CASE WHEN consolidated = 1 THEN 1 ELSE 0 END) as consolidated_count
                FROM accounts
                """)
            ).fetchone()
            
            print("\n" + "=" * 70)
            print("ESTATÍSTICAS")
            print("=" * 70)
            print(f"Total de lançamentos: {stats[0]}")
            print(f"Origens recorrentes: {stats[1]}")
            print(f"Gerados automaticamente: {stats[2]}")
            print(f"Consolidados: {stats[3]}")
            
            print("\n" + "=" * 70)
            if changes_made:
                print("✓ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
            else:
                print("✓ BANCO DE DADOS JÁ ESTÁ ATUALIZADO!")
            print("=" * 70)
            
            print("\n🎉 SISTEMA PRONTO!")
            print("\nPróximos passos:")
            print("1. Reinicie o servidor Flask: python app.py")
            print("2. Acesse /accounts")
            print("3. Teste criar uma conta recorrente")
            print("4. Leia o GUIA_RECORRENCIA_E_CLAREZA.md para entender tudo\n")
            
        except Exception as e:
            print(f"\n✗ ERRO durante a migração: {str(e)}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            sys.exit(1)

if __name__ == '__main__':
    migrate()