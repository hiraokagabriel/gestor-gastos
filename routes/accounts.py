from flask import Blueprint, request, jsonify, render_template
from models import Account
from database import db
from datetime import datetime
from calendar import monthrange
from sqlalchemy import and_, func

from services.recurrence import ensure_recurring_materialized_for_month

accounts_bp = Blueprint('accounts', __name__, url_prefix='/accounts')


def _parse_date_ymd(value: str) -> datetime:
    return datetime.strptime(value, '%Y-%m-%d')


def _materialize_recurring_for_range(start_dt: datetime, end_dt: datetime) -> int:
    """Materializa recorrências mês a mês dentro do intervalo (inclusive)."""
    created = 0
    y, m = start_dt.year, start_dt.month
    end_ym = (end_dt.year, end_dt.month)

    while (y, m) <= end_ym:
        created += ensure_recurring_materialized_for_month(y, m)
        m += 1
        if m > 12:
            m = 1
            y += 1

    return created


@accounts_bp.route('/')
def index():
    return render_template('accounts.html')


@accounts_bp.route('/api/accounts', methods=['GET'])
def get_accounts():
    """Listar lançamentos com filtros.

    Suporta dois modos de período:
    - month/year (compat)
    - start_date/end_date (filtro customizado)

    Importante: se houver origens recorrentes, materializa automaticamente os meses no período.
    """
    account_type = request.args.get('type')  # income, expense
    status = request.args.get('status')  # pending, consolidated, all

    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)

    # Resolver período
    if start_date and end_date:
        start_dt = _parse_date_ymd(start_date)
        end_dt = _parse_date_ymd(end_date)

        if start_dt > end_dt:
            return jsonify({'error': 'start_date não pode ser maior que end_date'}), 400

        first_day = datetime(start_dt.year, start_dt.month, start_dt.day, 0, 0, 0)
        last_day = datetime(end_dt.year, end_dt.month, end_dt.day, 23, 59, 59)

        _materialize_recurring_for_range(first_day, last_day)
    elif month and year:
        ensure_recurring_materialized_for_month(year, month)

        first_day = datetime(year, month, 1)
        last_day_num = monthrange(year, month)[1]
        last_day = datetime(year, month, last_day_num, 23, 59, 59)
    else:
        # default: mês atual
        today = datetime.now()
        month = today.month
        year = today.year
        ensure_recurring_materialized_for_month(year, month)

        first_day = datetime(year, month, 1)
        last_day_num = monthrange(year, month)[1]
        last_day = datetime(year, month, last_day_num, 23, 59, 59)

    query = Account.query

    # Tipo
    if account_type:
        query = query.filter_by(type=account_type)

    # Status de consolidação
    if status == 'pending':
        query = query.filter_by(consolidated=False)
    elif status == 'consolidated':
        query = query.filter_by(consolidated=True)

    # Período
    query = query.filter(and_(Account.date >= first_day, Account.date <= last_day))

    # Ordenação
    query = query.order_by(Account.date.asc(), Account.consolidated.asc())

    accounts = query.all()
    return jsonify([account.to_dict() for account in accounts])


@accounts_bp.route('/api/accounts/summary', methods=['GET'])
def get_summary():
    """Resumo financeiro estilo fluxo de caixa.

    Retorna:
    - Totais do período (consolidado e total)
    - Saldo inicial (antes do período) e saldo final (saldo inicial + movimento do período)

    Suporta month/year e start_date/end_date.
    """
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)

    # Resolver período
    if start_date and end_date:
        start_dt = _parse_date_ymd(start_date)
        end_dt = _parse_date_ymd(end_date)

        if start_dt > end_dt:
            return jsonify({'error': 'start_date não pode ser maior que end_date'}), 400

        first_day = datetime(start_dt.year, start_dt.month, start_dt.day, 0, 0, 0)
        last_day = datetime(end_dt.year, end_dt.month, end_dt.day, 23, 59, 59)

        _materialize_recurring_for_range(first_day, last_day)
    else:
        if not month or not year:
            today = datetime.now()
            month = today.month
            year = today.year

        ensure_recurring_materialized_for_month(year, month)

        first_day = datetime(year, month, 1)
        last_day_num = monthrange(year, month)[1]
        last_day = datetime(year, month, last_day_num, 23, 59, 59)

    # Helpers de soma
    def _sum_amount(q):
        return float(q.scalar() or 0.0)

    # Saldo inicial (antes do período)
    initial_income_consolidated = _sum_amount(
        db.session.query(func.sum(Account.amount)).filter(
            Account.type == 'income',
            Account.consolidated == True,
            Account.date < first_day
        )
    )
    initial_expense_consolidated = _sum_amount(
        db.session.query(func.sum(Account.amount)).filter(
            Account.type == 'expense',
            Account.consolidated == True,
            Account.date < first_day
        )
    )
    balance_initial_consolidated = initial_income_consolidated - initial_expense_consolidated

    initial_income_total = _sum_amount(
        db.session.query(func.sum(Account.amount)).filter(
            Account.type == 'income',
            Account.date < first_day
        )
    )
    initial_expense_total = _sum_amount(
        db.session.query(func.sum(Account.amount)).filter(
            Account.type == 'expense',
            Account.date < first_day
        )
    )
    balance_initial_total = initial_income_total - initial_expense_total

    # Totais do período
    income_consolidated = _sum_amount(
        db.session.query(func.sum(Account.amount)).filter(
            Account.type == 'income',
            Account.consolidated == True,
            Account.date >= first_day,
            Account.date <= last_day
        )
    )
    income_pending = _sum_amount(
        db.session.query(func.sum(Account.amount)).filter(
            Account.type == 'income',
            Account.consolidated == False,
            Account.date >= first_day,
            Account.date <= last_day
        )
    )

    expense_consolidated = _sum_amount(
        db.session.query(func.sum(Account.amount)).filter(
            Account.type == 'expense',
            Account.consolidated == True,
            Account.date >= first_day,
            Account.date <= last_day
        )
    )
    expense_pending = _sum_amount(
        db.session.query(func.sum(Account.amount)).filter(
            Account.type == 'expense',
            Account.consolidated == False,
            Account.date >= first_day,
            Account.date <= last_day
        )
    )

    income_total = income_consolidated + income_pending
    expense_total = expense_consolidated + expense_pending

    period_balance_consolidated = income_consolidated - expense_consolidated
    period_balance_total = income_total - expense_total

    balance_final_consolidated = balance_initial_consolidated + period_balance_consolidated
    balance_final_total = balance_initial_total + period_balance_total

    # Contagens (para UI/diagnóstico)
    recurring_count = db.session.query(func.count(Account.id)).filter(
        Account.date >= first_day,
        Account.date <= last_day,
        ((Account.recurring == True) | (Account.parent_id.isnot(None)))
    ).scalar() or 0

    pending_count = db.session.query(func.count(Account.id)).filter(
        Account.date >= first_day,
        Account.date <= last_day,
        Account.consolidated == False
    ).scalar() or 0

    consolidated_count = db.session.query(func.count(Account.id)).filter(
        Account.date >= first_day,
        Account.date <= last_day,
        Account.consolidated == True
    ).scalar() or 0

    return jsonify({
        # Período usado
        'period_start': first_day.strftime('%Y-%m-%d'),
        'period_end': last_day.strftime('%Y-%m-%d'),

        # Totais do período
        'income_pending': round(income_pending, 2),
        'income_consolidated': round(income_consolidated, 2),
        'income_total': round(income_total, 2),
        'expense_pending': round(expense_pending, 2),
        'expense_consolidated': round(expense_consolidated, 2),
        'expense_total': round(expense_total, 2),

        # Fluxo de caixa
        'balance_initial_consolidated': round(balance_initial_consolidated, 2),
        'balance_initial_total': round(balance_initial_total, 2),
        'period_balance_consolidated': round(period_balance_consolidated, 2),
        'period_balance_total': round(period_balance_total, 2),
        'balance_consolidated': round(balance_final_consolidated, 2),
        'balance_total': round(balance_final_total, 2),

        # Estatísticas extras
        'recurring_count': int(recurring_count),
        'pending_count': int(pending_count),
        'consolidated_count': int(consolidated_count),
    })


@accounts_bp.route('/api/accounts/<int:account_id>', methods=['GET'])
def get_account(account_id):
    account = Account.query.get_or_404(account_id)
    return jsonify(account.to_dict())


@accounts_bp.route('/api/accounts', methods=['POST'])
def create_account():
    """Criar lançamento.

    Se for recorrente (origem), define recurring_day e gera meses futuros.
    """
    data = request.json

    date_obj = datetime.strptime(data['date'], '%Y-%m-%d')

    account = Account(
        description=data['description'],
        amount=float(data['amount']),
        type=data['type'],
        category=data.get('category', ''),
        date=date_obj,
        recurring=data.get('recurring', False),
        recurring_day=data.get('recurring_day'),
        consolidated=data.get('consolidated', False)
    )

    # Se marcou como recorrente e não enviou recurring_day, assumir o dia da data
    if account.recurring and not account.recurring_day:
        account.recurring_day = date_obj.day

    if account.consolidated:
        account.consolidated_date = datetime.now()

    db.session.add(account)
    db.session.commit()

    if account.recurring:
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

    was_recurring = account.recurring

    account.description = data.get('description', account.description)
    account.amount = float(data.get('amount', account.amount))
    account.type = data.get('type', account.type)
    account.category = data.get('category', account.category)

    if 'date' in data:
        account.date = datetime.strptime(data['date'], '%Y-%m-%d')

    account.recurring = data.get('recurring', account.recurring)
    account.recurring_day = data.get('recurring_day', account.recurring_day)

    # Se acabou de virar recorrente e não tem recurring_day, fixar
    if not was_recurring and account.recurring and not account.recurring_day and account.date:
        account.recurring_day = account.date.day

    # Atualizar consolidação
    if 'consolidated' in data:
        was_consolidated = account.consolidated
        account.consolidated = data['consolidated']

        if not was_consolidated and account.consolidated:
            account.consolidated_date = datetime.now()
        elif was_consolidated and not account.consolidated:
            account.consolidated_date = None

    db.session.commit()

    # Se mudou para recorrente (origem), gerar meses
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
    account = Account.query.get_or_404(account_id)

    if account.consolidated:
        return jsonify({'error': 'Lançamento já consolidado'}), 400

    account.consolidated = True
    account.consolidated_date = datetime.now()
    db.session.commit()

    return jsonify({'message': 'Lançamento consolidado', 'account': account.to_dict()})


@accounts_bp.route('/api/accounts/<int:account_id>/unconsolidate', methods=['POST'])
def unconsolidate_account(account_id):
    account = Account.query.get_or_404(account_id)

    if not account.consolidated:
        return jsonify({'error': 'Lançamento não consolidado'}), 400

    account.consolidated = False
    account.consolidated_date = None
    db.session.commit()

    return jsonify({'message': 'Consolidação revertida', 'account': account.to_dict()})


@accounts_bp.route('/api/accounts/<int:account_id>/generate-future', methods=['POST'])
def generate_future_months(account_id):
    account = Account.query.get_or_404(account_id)

    if not account.recurring or account.parent_id:
        return jsonify({'error': 'Apenas contas recorrentes principais podem gerar meses'}), 400

    num_months = request.json.get('months', 12)
    generated = account.generate_next_months(num_months)

    return jsonify({'message': f'{len(generated)} meses gerados', 'generated_count': len(generated)})


@accounts_bp.route('/api/accounts/<int:account_id>', methods=['DELETE'])
def delete_account(account_id):
    account = Account.query.get_or_404(account_id)

    delete_children = request.args.get('delete_children', 'false').lower() == 'true'

    if account.recurring and not account.parent_id and delete_children:
        account.children.delete()
        db.session.commit()

    db.session.delete(account)
    db.session.commit()

    return jsonify({'message': 'Conta deletada', 'deleted_children': delete_children}), 200


@accounts_bp.route('/api/accounts/<int:account_id>/delete-series', methods=['DELETE'])
def delete_recurring_series(account_id):
    """Deletar conta recorrente e TODAS as geradas automaticamente.

    Pode receber o id do pai (origem) ou de qualquer filho.
    """
    account = Account.query.get_or_404(account_id)

    if account.parent_id:
        parent = Account.query.get(account.parent_id)
        if parent:
            account = parent

    if not account.recurring:
        return jsonify({'error': 'Conta não é recorrente'}), 400

    children_count = account.children.count()
    account.children.delete()
    db.session.delete(account)
    db.session.commit()

    return jsonify({
        'message': f'Série recorrente deletada: 1 origem + {children_count} geradas',
        'deleted_total': children_count + 1
    }), 200
