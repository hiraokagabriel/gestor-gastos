from flask import Blueprint, request, jsonify, render_template
from models import CreditCard, Transaction, Installment
from database import db
from datetime import datetime

cards_bp = Blueprint('cards', __name__, url_prefix='/cards')

@cards_bp.route('/')
def index():
    return render_template('cards.html')

@cards_bp.route('/api/cards', methods=['GET'])
def get_cards():
    cards = CreditCard.query.all()
    return jsonify([card.to_dict() for card in cards])

@cards_bp.route('/api/cards/<int:card_id>', methods=['GET'])
def get_card(card_id):
    card = CreditCard.query.get_or_404(card_id)
    return jsonify(card.to_dict())

@cards_bp.route('/api/cards', methods=['POST'])
def create_card():
    data = request.json
    card = CreditCard(
        name=data['name'],
        limit_total=float(data['limit_total']),
        closing_day=int(data['closing_day']),
        due_day=int(data['due_day']),
        flag=data.get('flag', ''),
        last_digits=data.get('last_digits', ''),
        active=data.get('active', True)
    )
    db.session.add(card)
    db.session.commit()
    return jsonify(card.to_dict()), 201

@cards_bp.route('/api/cards/<int:card_id>', methods=['PUT'])
def update_card(card_id):
    card = CreditCard.query.get_or_404(card_id)
    data = request.json
    card.name = data.get('name', card.name)
    card.limit_total = float(data.get('limit_total', card.limit_total))
    card.closing_day = int(data.get('closing_day', card.closing_day))
    card.due_day = int(data.get('due_day', card.due_day))
    card.flag = data.get('flag', card.flag)
    card.last_digits = data.get('last_digits', card.last_digits)
    card.active = data.get('active', card.active)
    db.session.commit()
    return jsonify(card.to_dict())

@cards_bp.route('/api/cards/<int:card_id>', methods=['DELETE'])
def delete_card(card_id):
    card = CreditCard.query.get_or_404(card_id)
    db.session.delete(card)
    db.session.commit()
    return jsonify({'message': 'Cartão deletado com sucesso'}), 200

@cards_bp.route('/api/cards/<int:card_id>/transactions', methods=['GET'])
def get_card_transactions(card_id):
    card = CreditCard.query.get_or_404(card_id)
    transactions = Transaction.query.filter_by(card_id=card_id).order_by(Transaction.date.desc()).all()
    return jsonify([t.to_dict() for t in transactions])

@cards_bp.route('/api/transactions', methods=['POST'])
def create_transaction():
    data = request.json
    transaction = Transaction(
        card_id=int(data['card_id']),
        description=data['description'],
        amount=float(data['amount']),
        date=datetime.strptime(data['date'], '%Y-%m-%d'),
        category=data.get('category', ''),
        installments_total=int(data.get('installments_total', 1))
    )
    db.session.add(transaction)
    db.session.commit()
    transaction.create_installments()
    db.session.commit()
    return jsonify(transaction.to_dict()), 201

@cards_bp.route('/api/transactions/<int:transaction_id>', methods=['DELETE'])
def delete_transaction(transaction_id):
    transaction = Transaction.query.get_or_404(transaction_id)
    db.session.delete(transaction)
    db.session.commit()
    return jsonify({'message': 'Transação deletada com sucesso'}), 200

@cards_bp.route('/api/installments/<int:installment_id>/pay', methods=['POST'])
def pay_installment(installment_id):
    installment = Installment.query.get_or_404(installment_id)
    installment.paid = True
    installment.paid_date = datetime.utcnow()
    db.session.commit()
    return jsonify(installment.to_dict())