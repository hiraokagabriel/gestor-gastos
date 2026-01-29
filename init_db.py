"""Script para inicializar o banco de dados"""
from app import app
from database import db
from models import CreditCard, Transaction, Installment, Bill, Account, Category, Invoice

if __name__ == '__main__':
    with app.app_context():
        # Criar todas as tabelas
        db.create_all()
        
        print("✅ Banco de dados criado com sucesso!")
        print("\nTabelas criadas:")
        print("  - credit_cards (Cartões de Crédito)")
        print("  - transactions (Transações)")
        print("  - installments (Parcelas)")
        print("  - invoices (Faturas) ⭐ NOVO")
        print("  - bills (Boletos)")
        print("  - accounts (Contas)")
        print("  - categories (Categorias)")
        print("\n✅ Pronto para usar! Execute: python app.py")