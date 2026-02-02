from flask import Blueprint, jsonify, render_template, session, request
from models import CreditCard, Bill, Account, Transaction
from database import db
from datetime import datetime
from sqlalchemy import func
from calendar import monthrange

from services.recurrence import list_recurring_occurrences_for_month

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')


def _resolve_viewing_month_year():
    """Resolve mês/ano do dashboard.

    Prioridade:
    1) Query params month/year
    2) Session viewing_month/viewing_year
    3) Hoje
    """
    today = datetime.now()

    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)

    if month and year:
        return month, year

    viewing_month = session.get('viewing_month', today.month)
    viewing_year = session.get('viewing_year', today.year)
    return viewing_month, viewing_year


def _month_range(month: int, year: int):
    first_day = datetime(year, month, 1)

    if month == 12:
        next_month = datetime(year + 1, 1, 1)
    else:
        next_month = datetime(year, month + 1, 1)

    return first_day, next_month


@dashboard_bp.route('/')
def index():
    return render_template('dashboard.html')


@dashboard_bp.route('/api/summary', methods=['GET'])
def get_summary():
    card_id = request.args.get('card_id', type=int)
    viewing_month, viewing_year = _resolve_viewing_month_year()

    # Filtrar por cartão se especificado
    if card_id:
        cards = CreditCard.query.filter_by(id=card_id).all()
    else:
        cards = CreditCard.query.all()

    total_card_limit = sum(card.limit_total for card in cards)
    total_card_used = sum(card.get_total_used() for card in cards)
    total_card_available = total_card_limit - total_card_used

    # Período do mês aplicado
    first_day, next_month = _month_range(viewing_month, viewing_year)

    # Boletos
    # - Pendentes do mês: não pagos com vencimento dentro do mês aplicado
    pending_in_month = Bill.query.filter(
        Bill.paid == False,
        Bill.due_date >= first_day,
        Bill.due_date < next_month
    ).all()

    pending_in_month_amount = float(sum(bill.amount for bill in pending_in_month))

    # - Pendentes até aqui: não pagos com vencimento até hoje
    now = datetime.now()
    pending_until_today = Bill.query.filter(
        Bill.paid == False,
        Bill.due_date <= now
    ).all()

    pending_until_today_amount = float(sum(bill.amount for bill in pending_until_today))

    # Receitas (não filtradas por cartão)
    monthly_income = db.session.query(func.sum(Account.amount)).filter(
        Account.type == 'income',
        Account.date >= first_day,
        Account.date < next_month
    ).scalar() or 0.0

    # Despesas gerais (não de cartão)
    monthly_expenses = db.session.query(func.sum(Account.amount)).filter(
        Account.type == 'expense',
        Account.date >= first_day,
        Account.date < next_month
    ).scalar() or 0.0

    # Gastos de cartão (filtrados se card_id especificado)
    if card_id:
        monthly_card_expenses = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.card_id == card_id,
            Transaction.date >= first_day,
            Transaction.date < next_month
        ).scalar() or 0.0
    else:
        monthly_card_expenses = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.date >= first_day,
            Transaction.date < next_month
        ).scalar() or 0.0

    # Total de despesas
    if card_id:
        # Se filtrando por cartão, só mostrar despesas do cartão
        total_expenses = monthly_card_expenses
    else:
        # Senão mostrar tudo
        total_expenses = monthly_expenses + monthly_card_expenses

    balance = monthly_income - total_expenses

    return jsonify({
        'viewing_month': viewing_month,
        'viewing_year': viewing_year,
        'cards': {
            'total_limit': total_card_limit,
            'total_used': total_card_used,
            'total_available': total_card_available,
            'usage_percentage': (total_card_used / total_card_limit * 100) if total_card_limit > 0 else 0
        },
        'bills': {
            'pending_in_month_count': len(pending_in_month),
            'pending_in_month_amount': pending_in_month_amount,
            'pending_until_today_count': len(pending_until_today),
            'pending_until_today_amount': pending_until_today_amount,
        },
        'monthly': {
            'income': monthly_income,
            'expenses': total_expenses,
            'balance': balance,
            'card_expenses': monthly_card_expenses
        }
    })


@dashboard_bp.route('/api/prediction', methods=['GET'])
def get_prediction():
    """Previsor de gastos do mês.

    Objetivo: não ambíguo.
    - Sem card_id: soma faturas + boletos não pagos do mês + ocorrência do mês de recorrências.
    - Com card_id: soma apenas faturas do cartão (não inclui boletos/contas/receitas).
    """
    try:
        today = datetime.now()
        month_arg = request.args.get('month', type=int)
        year_arg = request.args.get('year', type=int)

        viewing_month = month_arg or session.get('viewing_month', today.month)
        viewing_year = year_arg or session.get('viewing_year', today.year)
        card_id = request.args.get('card_id', type=int)

        scope = 'card' if card_id else 'all'

        # 1) Faturas de cartões previstas
        if card_id:
            cards = CreditCard.query.filter_by(id=card_id, active=True).all()
        else:
            cards = CreditCard.query.filter_by(active=True).all()

        card_invoices_total = 0.0
        invoices_breakdown = []

        for card in cards:
            amount = float(card.get_bill_for_month(viewing_month, viewing_year))
            if amount > 0:
                card_invoices_total += amount
                invoices_breakdown.append({
                    'card_id': card.id,
                    'card_name': card.name,
                    'amount': amount
                })

        # 2) Boletos não pagos no mês (apenas Total Geral)
        bills_total = 0.0
        bills_breakdown = []
        if not card_id:
            first_day = datetime(viewing_year, viewing_month, 1)
            last_day_num = monthrange(viewing_year, viewing_month)[1]
            last_day = datetime(viewing_year, viewing_month, last_day_num, 23, 59, 59)

            bills = Bill.query.filter(
                Bill.paid == False,
                Bill.due_date >= first_day,
                Bill.due_date <= last_day
            ).all()

            bills_total = float(sum(bill.amount for bill in bills))
            bills_breakdown = [{
                'description': bill.description,
                'amount': float(bill.amount),
                'due_date': bill.due_date.strftime('%d/%m/%Y')
            } for bill in bills]

        # 3) Recorrentes do mês (apenas Total Geral) - baseado em ocorrência do mês
        recurring_total = 0.0
        recurring_breakdown = []
        if not card_id:
            recurring_items = list_recurring_occurrences_for_month(viewing_year, viewing_month, 'expense')
            recurring_total = float(sum(item['amount'] for item in recurring_items))
            recurring_breakdown = [{
                'description': item['description'],
                'amount': float(item['amount']),
                'date': item.get('date'),
                'origin_id': item.get('origin_id'),
                'source': item.get('source')
            } for item in recurring_items]

        # 4) Total previsto
        total_predicted = float(card_invoices_total + bills_total + recurring_total)

        # 5) Receitas previstas (apenas Total Geral) - recorrentes do mês
        income_total = 0.0
        income_recurring_items = []
        if not card_id:
            income_recurring_items = list_recurring_occurrences_for_month(viewing_year, viewing_month, 'income')
            income_total = float(sum(item['amount'] for item in income_recurring_items))

        # 6) Balanço previsto
        predicted_balance = float(income_total - total_predicted)

        # 7) Comparação com mês anterior (mesmo critério do mês atual)
        prev_month = viewing_month - 1 if viewing_month > 1 else 12
        prev_year = viewing_year if viewing_month > 1 else viewing_year - 1

        prev_month_expenses = 0.0
        for card in cards:
            prev_month_expenses += float(card.get_bill_for_month(prev_month, prev_year))

        if not card_id:
            prev_first_day = datetime(prev_year, prev_month, 1)
            prev_last_day_num = monthrange(prev_year, prev_month)[1]
            prev_last_day = datetime(prev_year, prev_month, prev_last_day_num, 23, 59, 59)

            prev_bills = Bill.query.filter(
                Bill.paid == False,
                Bill.due_date >= prev_first_day,
                Bill.due_date <= prev_last_day
            ).all()

            prev_month_expenses += float(sum(bill.amount for bill in prev_bills))

            prev_recurring_items = list_recurring_occurrences_for_month(prev_year, prev_month, 'expense')
            prev_month_expenses += float(sum(item['amount'] for item in prev_recurring_items))

        if prev_month_expenses > 0:
            difference_percent = ((total_predicted - prev_month_expenses) / prev_month_expenses) * 100
        else:
            difference_percent = 0.0

        return jsonify({
            'scope': scope,
            'card_id': card_id,
            'total_predicted': total_predicted,
            'breakdown': {
                'card_invoices': {
                    'total': float(card_invoices_total),
                    'items': invoices_breakdown
                },
                'bills': {
                    'total': float(bills_total),
                    'count': len(bills_breakdown),
                    'items': bills_breakdown
                },
                'recurring': {
                    'total': float(recurring_total),
                    'count': len(recurring_breakdown),
                    'items': recurring_breakdown
                }
            },
            'income': {
                'total': float(income_total),
                'recurring_count': 0 if card_id else len(income_recurring_items)
            },
            'balance': {
                'predicted': float(predicted_balance),
                'status': 'positive' if predicted_balance >= 0 else 'negative'
            },
            'comparison': {
                'previous_month': float(prev_month_expenses),
                'difference': float(total_predicted - prev_month_expenses),
                'difference_percent': float(difference_percent)
            },
            'viewing_month': viewing_month,
            'viewing_year': viewing_year,
            'assumptions': {
                'bills_included': (card_id is None),
                'recurring_included': (card_id is None),
                'income_included': (card_id is None),
                'bills_filter': 'paid == False'
            }
        })
    except Exception as e:
        print(f"Erro em get_prediction: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/api/expenses-by-category', methods=['GET'])
def expenses_by_category():
    card_id = request.args.get('card_id', type=int)
    viewing_month, viewing_year = _resolve_viewing_month_year()
    first_day, next_month = _month_range(viewing_month, viewing_year)

    categories = {}

    # Despesas gerais (só em Total Geral)
    if not card_id:
        account_expenses = db.session.query(
            Account.category,
            func.sum(Account.amount).label('total')
        ).filter(
            Account.type == 'expense',
            Account.date >= first_day,
            Account.date < next_month
        ).group_by(Account.category).all()

        for category, total in account_expenses:
            cat_name = category or 'Sem categoria'
            categories[cat_name] = categories.get(cat_name, 0) + total

    # Gastos de cartão (filtrados se necessário)
    if card_id:
        card_expenses = db.session.query(
            Transaction.category,
            func.sum(Transaction.amount).label('total')
        ).filter(
            Transaction.card_id == card_id,
            Transaction.date >= first_day,
            Transaction.date < next_month
        ).group_by(Transaction.category).all()
    else:
        card_expenses = db.session.query(
            Transaction.category,
            func.sum(Transaction.amount).label('total')
        ).filter(
            Transaction.date >= first_day,
            Transaction.date < next_month
        ).group_by(Transaction.category).all()

    for category, total in card_expenses:
        cat_name = category or 'Sem categoria'
        categories[cat_name] = categories.get(cat_name, 0) + total

    return jsonify([
        {'category': k, 'amount': v}
        for k, v in categories.items()
    ])


@dashboard_bp.route('/api/monthly-trend', methods=['GET'])
def monthly_trend():
    viewing_month, viewing_year = _resolve_viewing_month_year()
    card_id = request.args.get('card_id', type=int)

    # Últimos 6 meses terminando no mês aplicado (inclusive)
    trends = []

    def _add_month(y, m, delta):
        mm = m + delta
        yy = y
        while mm > 12:
            mm -= 12
            yy += 1
        while mm < 1:
            mm += 12
            yy -= 1
        return yy, mm

    for offset in range(-5, 1):
        year, month = _add_month(viewing_year, viewing_month, offset)

        first_day = datetime(year, month, 1)
        if month == 12:
            last_day = datetime(year + 1, 1, 1)
        else:
            last_day = datetime(year, month + 1, 1)

        # Receitas (só em Total Geral)
        income = 0.0
        if not card_id:
            income = db.session.query(func.sum(Account.amount)).filter(
                Account.type == 'income',
                Account.date >= first_day,
                Account.date < last_day
            ).scalar() or 0.0

        # Despesas gerais (só em Total Geral)
        expenses = 0.0
        if not card_id:
            expenses = db.session.query(func.sum(Account.amount)).filter(
                Account.type == 'expense',
                Account.date >= first_day,
                Account.date < last_day
            ).scalar() or 0.0

        # Gastos de cartão (filtrados se necessário)
        if card_id:
            card_expenses = db.session.query(func.sum(Transaction.amount)).filter(
                Transaction.card_id == card_id,
                Transaction.date >= first_day,
                Transaction.date < last_day
            ).scalar() or 0.0
        else:
            card_expenses = db.session.query(func.sum(Transaction.amount)).filter(
                Transaction.date >= first_day,
                Transaction.date < last_day
            ).scalar() or 0.0

        expenses += card_expenses

        trends.append({
            'month': f"{year}-{month:02d}",
            'income': income,
            'expenses': expenses,
            'balance': income - expenses
        })

    return jsonify(trends)
