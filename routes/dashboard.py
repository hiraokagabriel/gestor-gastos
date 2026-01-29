from flask import Blueprint, jsonify, render_template, session
from models import CreditCard, Bill, Account, Transaction, Invoice, Installment
from database import db
from datetime import datetime, timedelta
from sqlalchemy import func, extract
from calendar import monthrange

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@dashboard_bp.route('/')
def index():
    return render_template('dashboard.html')

@dashboard_bp.route('/api/summary', methods=['GET'])
def get_summary():
    cards = CreditCard.query.all()
    total_card_limit = sum(card.limit_total for card in cards)
    total_card_used = sum(card.get_total_used() for card in cards)
    total_card_available = total_card_limit - total_card_used
    
    pending_bills = Bill.query.filter_by(paid=False).all()
    total_pending_bills = sum(bill.amount for bill in pending_bills)
    overdue_bills = [bill for bill in pending_bills if bill.is_overdue]
    total_overdue = sum(bill.amount for bill in overdue_bills)
    
    today = datetime.now()
    first_day = datetime(today.year, today.month, 1)
    if today.month == 12:
        last_day = datetime(today.year + 1, 1, 1)
    else:
        last_day = datetime(today.year, today.month + 1, 1)
    
    monthly_income = db.session.query(func.sum(Account.amount)).filter(
        Account.type == 'income',
        Account.date >= first_day,
        Account.date < last_day
    ).scalar() or 0.0
    
    monthly_expenses = db.session.query(func.sum(Account.amount)).filter(
        Account.type == 'expense',
        Account.date >= first_day,
        Account.date < last_day
    ).scalar() or 0.0
    
    monthly_card_expenses = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.date >= first_day,
        Transaction.date < last_day
    ).scalar() or 0.0
    
    monthly_expenses += monthly_card_expenses
    balance = monthly_income - monthly_expenses
    
    return jsonify({
        'cards': {
            'total_limit': total_card_limit,
            'total_used': total_card_used,
            'total_available': total_card_available,
            'usage_percentage': (total_card_used / total_card_limit * 100) if total_card_limit > 0 else 0
        },
        'bills': {
            'pending_count': len(pending_bills),
            'pending_amount': total_pending_bills,
            'overdue_count': len(overdue_bills),
            'overdue_amount': total_overdue
        },
        'monthly': {
            'income': monthly_income,
            'expenses': monthly_expenses,
            'balance': balance,
            'card_expenses': monthly_card_expenses
        }
    })

@dashboard_bp.route('/api/prediction', methods=['GET'])
def get_prediction():
    """Previsor de gastos do mês atual"""
    try:
        today = datetime.now()
        viewing_month = session.get('viewing_month', today.month)
        viewing_year = session.get('viewing_year', today.year)
        
        # 1. Faturas de cartões previstas
        cards = CreditCard.query.filter_by(active=True).all()
        card_invoices_total = 0
        invoices_breakdown = []
        
        for card in cards:
            amount = card.get_bill_for_month(viewing_month, viewing_year)
            if amount > 0:
                card_invoices_total += amount
                invoices_breakdown.append({
                    'card_name': card.name,
                    'amount': amount
                })
        
        # 2. Boletos pendentes no mês
        first_day = datetime(viewing_year, viewing_month, 1)
        last_day_num = monthrange(viewing_year, viewing_month)[1]
        last_day = datetime(viewing_year, viewing_month, last_day_num, 23, 59, 59)
        
        bills = Bill.query.filter(
            Bill.paid == False,
            Bill.due_date >= first_day,
            Bill.due_date <= last_day
        ).all()
        
        bills_total = sum(bill.amount for bill in bills)
        bills_breakdown = [{
            'description': bill.description,
            'amount': bill.amount,
            'due_date': bill.due_date.strftime('%d/%m/%Y')
        } for bill in bills]
        
        # 3. Despesas recorrentes (contas gerais do tipo expense)
        recurring_expenses = Account.query.filter_by(
            type='expense',
            recurring=True
        ).all()
        
        recurring_total = sum(acc.amount for acc in recurring_expenses)
        recurring_breakdown = [{
            'description': acc.description,
            'amount': acc.amount
        } for acc in recurring_expenses]
        
        # 4. Total previsto
        total_predicted = card_invoices_total + bills_total + recurring_total
        
        # 5. Receitas previstas
        recurring_income = Account.query.filter_by(
            type='income',
            recurring=True
        ).all()
        
        income_total = sum(acc.amount for acc in recurring_income)
        
        # 6. Balanço previsto
        predicted_balance = income_total - total_predicted
        
        # 7. Comparar com mês anterior
        prev_month = viewing_month - 1 if viewing_month > 1 else 12
        prev_year = viewing_year if viewing_month > 1 else viewing_year - 1
        
        prev_month_expenses = 0
        for card in cards:
            prev_month_expenses += card.get_bill_for_month(prev_month, prev_year)
        
        # Boletos do mês anterior
        prev_first_day = datetime(prev_year, prev_month, 1)
        prev_last_day_num = monthrange(prev_year, prev_month)[1]
        prev_last_day = datetime(prev_year, prev_month, prev_last_day_num, 23, 59, 59)
        
        prev_bills = Bill.query.filter(
            Bill.due_date >= prev_first_day,
            Bill.due_date <= prev_last_day
        ).all()
        
        prev_month_expenses += sum(bill.amount for bill in prev_bills)
        prev_month_expenses += recurring_total
        
        # Diferença percentual
        if prev_month_expenses > 0:
            difference_percent = ((total_predicted - prev_month_expenses) / prev_month_expenses) * 100
        else:
            difference_percent = 0
        
        return jsonify({
            'total_predicted': total_predicted,
            'breakdown': {
                'card_invoices': {
                    'total': card_invoices_total,
                    'items': invoices_breakdown
                },
                'bills': {
                    'total': bills_total,
                    'count': len(bills),
                    'items': bills_breakdown
                },
                'recurring': {
                    'total': recurring_total,
                    'count': len(recurring_expenses),
                    'items': recurring_breakdown
                }
            },
            'income': {
                'total': income_total,
                'recurring_count': len(recurring_income)
            },
            'balance': {
                'predicted': predicted_balance,
                'status': 'positive' if predicted_balance >= 0 else 'negative'
            },
            'comparison': {
                'previous_month': prev_month_expenses,
                'difference': total_predicted - prev_month_expenses,
                'difference_percent': difference_percent
            },
            'viewing_month': viewing_month,
            'viewing_year': viewing_year
        })
    except Exception as e:
        print(f"Erro em get_prediction: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@dashboard_bp.route('/api/expenses-by-category', methods=['GET'])
def expenses_by_category():
    today = datetime.now()
    first_day = datetime(today.year, today.month, 1)
    
    account_expenses = db.session.query(
        Account.category,
        func.sum(Account.amount).label('total')
    ).filter(
        Account.type == 'expense',
        Account.date >= first_day
    ).group_by(Account.category).all()
    
    card_expenses = db.session.query(
        Transaction.category,
        func.sum(Transaction.amount).label('total')
    ).filter(
        Transaction.date >= first_day
    ).group_by(Transaction.category).all()
    
    categories = {}
    for category, total in account_expenses:
        cat_name = category or 'Sem categoria'
        categories[cat_name] = categories.get(cat_name, 0) + total
    
    for category, total in card_expenses:
        cat_name = category or 'Sem categoria'
        categories[cat_name] = categories.get(cat_name, 0) + total
    
    return jsonify([
        {'category': k, 'amount': v}
        for k, v in categories.items()
    ])

@dashboard_bp.route('/api/monthly-trend', methods=['GET'])
def monthly_trend():
    today = datetime.now()
    trends = []
    
    for i in range(6, 0, -1):
        month = today.month - i
        year = today.year
        while month <= 0:
            month += 12
            year -= 1
        
        first_day = datetime(year, month, 1)
        if month == 12:
            last_day = datetime(year + 1, 1, 1)
        else:
            last_day = datetime(year, month + 1, 1)
        
        income = db.session.query(func.sum(Account.amount)).filter(
            Account.type == 'income',
            Account.date >= first_day,
            Account.date < last_day
        ).scalar() or 0.0
        
        expenses = db.session.query(func.sum(Account.amount)).filter(
            Account.type == 'expense',
            Account.date >= first_day,
            Account.date < last_day
        ).scalar() or 0.0
        
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