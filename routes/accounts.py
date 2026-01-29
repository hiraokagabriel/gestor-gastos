from flask import Blueprint, request, jsonify, render_template
from models import Account
from database import db
from datetime import datetime
from calendar import monthrange
from sqlalchemy import extract, and_, or_

accounts_bp = Blueprint('accounts', __name__, url_prefix='/accounts')

@accounts_bp.route('/')
def index():
    return render_template('accounts.html')

@accounts_bp.route('/api/accounts', methods=['GET'])
def get_accounts():
    """Listar lançamentos com filtros"""
    account_type = request.args.get('type')  # income, expense
    status = request.args.get('status')  # pending, consolidated, all
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    include_recurring = request.args.get('include_recurring', 'true').lower() == 'true'
    
    query = Account.query
    
    # Filtrar por tipo
    if account_type:
        query = query.filter_by(type=account_type)
    
    # Filtrar por status de consolidação
    if status == 'pending':
        query = query.filter_by(consolidated=False)
    elif status == 'consolidated':
        query = query.filter_by(consolidated=True)
    
    # Filtrar por mês/ano
    if month and year:
        first_day = datetime(year, month, 1)
        last_day_num = monthrange(year, month)[1]
        last_day = datetime(year, month, last_day_num, 23, 59, 59)
        
        query = query.filter(
            and_(
                Account.date >= first_day,
                Account.date <= last_day
            )
        )
    
    # Ordenar: Pendentes primeiro, depois por data decrescente
    query = query.order_by(
        Account.consolidated.asc(),  # Pendentes primeiro
        Account.date.desc()  # Depois por data
    )
    
    accounts = query.all()
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
    
    first_day = datetime(year, month, 1)
    last_day_num = monthrange(year, month)[1]
    last_day = datetime(year, month, last_day_num, 23, 59, 59)
    
    accounts = Account.query.filter(
        and_(
            Account.date >= first_day,
            Account.date <= last_day
        )
    ).all()
    
    summary = {
        'income_pending': 0.0,
        'income_consolidated': 0.0,
        'income_total': 0.0,
        'expense_pending': 0.0,
        'expense_consolidated': 0.0,
        'expense_total': 0.0,
        'balance_pending': 0.0,
        'balance_consolidated': 0.0,
        'balance_total': 0.0,
        
        # Estatísticas extras
        'recurring_count': 0,
        'pending_count': 0,
        'consolidated_count': 0,
    }
    
    for account in accounts:
        if account.type == 'income':
            summary['income_total'] += account.amount
            if account.consolidated:
                summary['income_consolidated'] += account.amount
                summary['consolidated_count'] += 1
            else:
                summary['income_pending'] += account.amount
                summary['pending_count'] += 1
        else:
            summary['expense_total'] += account.amount
            if account.consolidated:
                summary['expense_consolidated'] += account.amount
                summary['consolidated_count'] += 1
            else:
                summary['expense_pending'] += account.amount
                summary['pending_count'] += 1
        
        if account.is_recurring_origin or account.is_recurring_child:
            summary['recurring_count'] += 1
    
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
    """Criar lançamento, e se for recorrente, gerar próximos meses"""
    data = request.json
    
    account = Account(
        description=data['description'],
        amount=float(data['amount']),
        type=data['type'],
        category=data.get('category', ''),
        date=datetime.strptime(data['date'], '%Y-%m-%d'),
        recurring=data.get('recurring', False),
        recurring_day=data.get('recurring_day'),  # Dia do mês
        consolidated=data.get('consolidated', False)
    )
    
    if account.consolidated:
        account.consolidated_date = datetime.now()
    
    db.session.add(account)
    db.session.commit()
    
    # Se for recorrente, gerar próximos meses automaticamente
    if account.recurring:
        # Gerar próximos 12 meses
        generated = account.generate_next_months(12)
        return jsonify({
            'account': account.to_dict(),
            'generated_count': len(generated),
            'message': f'Lançamento recorrente criado! {len(generated)} meses gerados automaticamente.'
        }), 201
    
    return jsonify(account.to_dict()), 201

@accounts_bp.route('/api/accounts/<int:account_id>', methods=['PUT'])
def update_account(account_id):
    account = Account.query.get_or_404(account_id)
    data = request.json
    
    # Salvar estado anterior de recorrência
    was_recurring = account.recurring
    
    account.description = data.get('description', account.description)
    account.amount = float(data.get('amount', account.amount))
    account.type = data.get('type', account.type)
    account.category = data.get('category', account.category)
    account.date = datetime.strptime(data['date'], '%Y-%m-%d') if 'date' in data else account.date
    account.recurring = data.get('recurring', account.recurring)
    account.recurring_day = data.get('recurring_day', account.recurring_day)
    
    # Atualizar consolidação
    if 'consolidated' in data:
        was_consolidated = account.consolidated
        account.consolidated = data['consolidated']
        
        if not was_consolidated and account.consolidated:
            account.consolidated_date = datetime.now()
        elif was_consolidated and not account.consolidated:
            account.consolidated_date = None
    
    db.session.commit()
    
    # Se mudou para recorrente, gerar meses
    if not was_recurring and account.recurring and not account.parent_id:
        generated = account.generate_next_months(12)
        return jsonify({
            'account': account.to_dict(),
            'generated_count': len(generated),
            'message': f'{len(generated)} meses futuros gerados!'
        })
    
    return jsonify(account.to_dict())

@accounts_bp.route('/api/accounts/<int:account_id>/consolidate', methods=['POST'])
def consolidate_account(account_id):
    """Consolidar lançamento"""
    account = Account.query.get_or_404(account_id)
    
    if account.consolidated:
        return jsonify({'error': 'Lançamento já consolidado'}), 400
    
    account.consolidated = True
    account.consolidated_date = datetime.now()
    db.session.commit()
    
    return jsonify({
        'message': 'Lançamento consolidado',
        'account': account.to_dict()
    })

@accounts_bp.route('/api/accounts/<int:account_id>/unconsolidate', methods=['POST'])
def unconsolidate_account(account_id):
    """Reverter consolidação"""
    account = Account.query.get_or_404(account_id)
    
    if not account.consolidated:
        return jsonify({'error': 'Lançamento não consolidado'}), 400
    
    account.consolidated = False
    account.consolidated_date = None
    db.session.commit()
    
    return jsonify({
        'message': 'Consolidação revertida',
        'account': account.to_dict()
    })

@accounts_bp.route('/api/accounts/<int:account_id>/generate-future', methods=['POST'])
def generate_future_months(account_id):
    """Gerar meses futuros manualmente para uma conta recorrente"""
    account = Account.query.get_or_404(account_id)
    
    if not account.recurring or account.parent_id:
        return jsonify({'error': 'Apenas contas recorrentes principais podem gerar meses'}), 400
    
    num_months = request.json.get('months', 12)
    generated = account.generate_next_months(num_months)
    
    return jsonify({
        'message': f'{len(generated)} meses gerados',
        'generated_count': len(generated)
    })

@accounts_bp.route('/api/accounts/<int:account_id>', methods=['DELETE'])
def delete_account(account_id):
    """Deletar lançamento"""
    account = Account.query.get_or_404(account_id)
    
    # Se for recorrente principal, perguntar se quer deletar filhos
    delete_children = request.args.get('delete_children', 'false').lower() == 'true'
    
    if account.recurring and not account.parent_id and delete_children:
        # Deletar todas as contas geradas
        children_count = account.children.count()
        account.children.delete()
        db.session.commit()
    
    db.session.delete(account)
    db.session.commit()
    
    return jsonify({
        'message': 'Conta deletada',
        'deleted_children': delete_children
    }), 200

@accounts_bp.route('/api/accounts/<int:account_id>/delete-series', methods=['DELETE'])
def delete_recurring_series(account_id):
    """Deletar conta recorrente e TODAS as geradas automaticamente"""
    account = Account.query.get_or_404(account_id)
    
    # Se for filho, pegar o pai
    if account.parent_id:
        parent = Account.query.get(account.parent_id)
        if parent:
            account = parent
    
    if not account.recurring:
        return jsonify({'error': 'Conta não é recorrente'}), 400
    
    # Contar filhos
    children_count = account.children.count()
    
    # Deletar todos os filhos
    account.children.delete()
    
    # Deletar o pai
    db.session.delete(account)
    db.session.commit()
    
    return jsonify({
        'message': f'Série recorrente deletada: 1 origem + {children_count} geradas',
        'deleted_total': children_count + 1
    }), 200