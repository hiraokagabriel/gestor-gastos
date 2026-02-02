from flask import Blueprint, request, jsonify, render_template
from models import Bill
from database import db
from datetime import datetime
from calendar import monthrange

bills_bp = Blueprint('bills', __name__, url_prefix='/bills')

@bills_bp.route('/')
def index():
    return render_template('bills.html')

@bills_bp.route('/api/bills', methods=['GET'])
def get_bills():
    status = request.args.get('status')
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)

    query = Bill.query

    # Filtro mensal (por vencimento)
    if month and year:
        last_day = monthrange(year, month)[1]
        start = datetime(year, month, 1)
        end = datetime(year, month, last_day, 23, 59, 59, 999999)
        query = query.filter(Bill.due_date >= start).filter(Bill.due_date <= end)

    # Filtro por status (aplicado em cima do recorte mensal)
    if status == 'paid':
        query = query.filter_by(paid=True)
    elif status == 'pending':
        query = query.filter_by(paid=False).filter(Bill.due_date >= datetime.now())
    elif status == 'overdue':
        query = query.filter_by(paid=False).filter(Bill.due_date < datetime.now())

    bills = query.order_by(Bill.due_date).all()
    return jsonify([bill.to_dict() for bill in bills])

@bills_bp.route('/api/bills/<int:bill_id>', methods=['GET'])
def get_bill(bill_id):
    bill = Bill.query.get_or_404(bill_id)
    return jsonify(bill.to_dict())

@bills_bp.route('/api/bills', methods=['POST'])
def create_bill():
    data = request.json
    bill = Bill(
        description=data['description'],
        amount=float(data['amount']),
        due_date=datetime.strptime(data['due_date'], '%Y-%m-%d'),
        category=data.get('category', ''),
        barcode=data.get('barcode', '')
    )
    db.session.add(bill)
    db.session.commit()
    return jsonify(bill.to_dict()), 201

@bills_bp.route('/api/bills/<int:bill_id>', methods=['PUT'])
def update_bill(bill_id):
    bill = Bill.query.get_or_404(bill_id)
    data = request.json
    bill.description = data.get('description', bill.description)
    bill.amount = float(data.get('amount', bill.amount))
    bill.due_date = datetime.strptime(data['due_date'], '%Y-%m-%d') if 'due_date' in data else bill.due_date
    bill.category = data.get('category', bill.category)
    bill.barcode = data.get('barcode', bill.barcode)
    db.session.commit()
    return jsonify(bill.to_dict())

@bills_bp.route('/api/bills/<int:bill_id>/pay', methods=['POST'])
def pay_bill(bill_id):
    bill = Bill.query.get_or_404(bill_id)
    bill.paid = True
    bill.paid_date = datetime.utcnow()
    db.session.commit()
    return jsonify(bill.to_dict())

@bills_bp.route('/api/bills/<int:bill_id>', methods=['DELETE'])
def delete_bill(bill_id):
    bill = Bill.query.get_or_404(bill_id)
    db.session.delete(bill)
    db.session.commit()
    return jsonify({'message': 'Boleto deletado com sucesso'}), 200