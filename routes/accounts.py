from flask import Blueprint, request, jsonify, render_template, session
from models import Account
from database import db
from datetime import datetime
from calendar import monthrange
from sqlalchemy import extract, and_

accounts_bp = Blueprint('accounts', __name__, url_prefix='/accounts')

@accounts_bp.route('/')
def index():
    return render_template('accounts.html')

@accounts_bp.route('/api/accounts', methods=['GET'])
def get_accounts():
    """Listar lançamentos com filtros"""
    account_type = request.args.get('type')  # income, expense
    status = request.args.get('status')  # pending, consolidated, all
    month = request.args.get('month', type=int)  # 1-12
    year = request.args.get('year', type=int)  # 2026
    
    # Base query
    query = Account.query
    
    # Filtrar por tipo
    if account_type:
        query = query.filter_by(type=account_type)
    
    # Filtrar por status de consolidação
    if status == 'pending':
        query = query.filter_by(consolidated=False)
    elif status == 'consolidated':
        query = query.filter_by(consolidated=True)
    # Se status == 'all' ou None, mostra todos
    
    # Filtrar por mês/ano (CORREÇÃO DO BUG!)
    if month and year:
        # Primeiro e último dia do mês
        first_day = datetime(year, month, 1)
        last_day_num = monthrange(year, month)[1]
        last_day = datetime(year, month, last_day_num, 23, 59, 59)
        
        # Filtrar contas dentro do mês
        # Para recorrentes, mostrar apenas se a data original está neste mês
        query = query.filter(
            and_(
                Account.date >= first_day,
                Account.date <= last_day
            )
        )
    
    accounts = query.order_by(Account.date.desc()).all()
    return jsonify([account.to_dict() for account in accounts])

@accounts_bp.route('/api/accounts/summary', methods=['GET'])
def get_summary():
    """Resumo financeiro com separação de consolidados vs pendentes"""
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    
    if not month or not year:
        today = datetime.now()
        month = today.month
        year = today.year
    
    # Primeiro e último dia do mês
    first_day = datetime(year, month, 1)
    last_day_num = monthrange(year, month)[1]
    last_day = datetime(year, month, last_day_num, 23, 59, 59)
    
    # Buscar lançamentos do mês
    accounts = Account.query.filter(
        and_(
            Account.date >= first_day,
            Account.date <= last_day
        )
    ).all()
    
    # Calcular totais separados
    summary = {
        # Receitas
        'income_pending': 0.0,
        'income_consolidated': 0.0,
        'income_total': 0.0,
        
        # Despesas
        'expense_pending': 0.0,
        'expense_consolidated': 0.0,
        'expense_total': 0.0,
        
        # Saldo
        'balance_pending': 0.0,  # Previsto
        'balance_consolidated': 0.0,  # Efetivo (em caixa)
        'balance_total': 0.0,  # Geral
    }
    
    for account in accounts:
        if account.type == 'income':
            summary['income_total'] += account.amount
            if account.consolidated:
                summary['income_consolidated'] += account.amount
            else:
                summary['income_pending'] += account.amount
        else:  # expense
            summary['expense_total'] += account.amount
            if account.consolidated:
                summary['expense_consolidated'] += account.amount
            else:
                summary['expense_pending'] += account.amount
    
    # Calcular saldos
    summary['balance_pending'] = summary['income_pending'] - summary['expense_pending']
    summary['balance_consolidated'] = summary['income_consolidated'] - summary['expense_consolidated']
    summary['balance_total'] = summary['income_total'] - summary['expense_total']
    
    return jsonify(summary)

@accounts_bp.route('/api/accounts/<int:account_id>', methods=['GET'])
def get_account(account_id):
    account = Account.query.get_or_404(account_id)
    return jsonify(account.to_dict())

@accounts_bp.route('/api/accounts', methods=['POST'])
def create_account():
    data = request.json
    account = Account(
        description=data['description'],
        amount=float(data['amount']),
        type=data['type'],
        category=data.get('category', ''),
        date=datetime.strptime(data['date'], '%Y-%m-%d'),
        recurring=data.get('recurring', False),
        consolidated=data.get('consolidated', False)  # Novo campo
    )
    
    # Se já vier marcado como consolidado, marcar data
    if account.consolidated:
        account.consolidated_date = datetime.now()
    
    db.session.add(account)
    db.session.commit()
    return jsonify(account.to_dict()), 201

@accounts_bp.route('/api/accounts/<int:account_id>', methods=['PUT'])
def update_account(account_id):
    account = Account.query.get_or_404(account_id)
    data = request.json
    
    account.description = data.get('description', account.description)
    account.amount = float(data.get('amount', account.amount))
    account.type = data.get('type', account.type)
    account.category = data.get('category', account.category)
    account.date = datetime.strptime(data['date'], '%Y-%m-%d') if 'date' in data else account.date
    account.recurring = data.get('recurring', account.recurring)
    
    # Atualizar consolidação se mudou
    if 'consolidated' in data:
        was_consolidated = account.consolidated
        account.consolidated = data['consolidated']
        
        # Se mudou de não consolidado para consolidado
        if not was_consolidated and account.consolidated:
            account.consolidated_date = datetime.now()
        # Se mudou de consolidado para não consolidado
        elif was_consolidated and not account.consolidated:
            account.consolidated_date = None
    
    db.session.commit()
    return jsonify(account.to_dict())

@accounts_bp.route('/api/accounts/<int:account_id>/consolidate', methods=['POST'])
def consolidate_account(account_id):
    """Consolidar um lançamento (marcar como pago/recebido)"""
    account = Account.query.get_or_404(account_id)
    
    if account.consolidated:
        return jsonify({'error': 'Lançamento já está consolidado'}), 400
    
    account.consolidated = True
    account.consolidated_date = datetime.now()
    db.session.commit()
    
    return jsonify({
        'message': 'Lançamento consolidado com sucesso',
        'account': account.to_dict()
    })

@accounts_bp.route('/api/accounts/<int:account_id>/unconsolidate', methods=['POST'])
def unconsolidate_account(account_id):
    """Reverter consolidação de um lançamento"""
    account = Account.query.get_or_404(account_id)
    
    if not account.consolidated:
        return jsonify({'error': 'Lançamento não está consolidado'}), 400
    
    account.consolidated = False
    account.consolidated_date = None
    db.session.commit()
    
    return jsonify({
        'message': 'Consolidação revertida com sucesso',
        'account': account.to_dict()
    })

@accounts_bp.route('/api/accounts/<int:account_id>', methods=['DELETE'])
def delete_account(account_id):
    account = Account.query.get_or_404(account_id)
    db.session.delete(account)
    db.session.commit()
    return jsonify({'message': 'Conta deletada com sucesso'}), 200