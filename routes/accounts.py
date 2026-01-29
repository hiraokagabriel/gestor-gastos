from flask import Blueprint, request, jsonify, render_template
from models import Account
from database import db
from datetime import datetime

accounts_bp = Blueprint('accounts', __name__, url_prefix='/accounts')

@accounts_bp.route('/')
def index():
    return render_template('accounts.html')

@accounts_bp.route('/api/accounts', methods=['GET'])
def get_accounts():
    account_type = request.args.get('type')
    query = Account.query
    
    if account_type:
        query = query.filter_by(type=account_type)
    
    accounts = query.order_by(Account.date.desc()).all()
    return jsonify([account.to_dict() for account in accounts])

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
        recurring=data.get('recurring', False)
    )
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
    db.session.commit()
    return jsonify(account.to_dict())

@accounts_bp.route('/api/accounts/<int:account_id>', methods=['DELETE'])
def delete_account(account_id):
    account = Account.query.get_or_404(account_id)
    db.session.delete(account)
    db.session.commit()
    return jsonify({'message': 'Conta deletada com sucesso'}), 200