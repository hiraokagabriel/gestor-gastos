from flask import Blueprint, jsonify, render_template
from models import CreditCard, Bill, Account, Transaction
from database import db
from datetime import datetime, timedelta
from sqlalchemy import func, extract

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