from flask import Blueprint, request, jsonify, render_template, session
from models import CreditCard, Invoice, Transaction, Installment
from database import db
from datetime import datetime
from calendar import monthrange

invoices_bp = Blueprint('invoices', __name__, url_prefix='/invoices')

@invoices_bp.route('/')
def index():
    """Página principal de faturas"""
    return render_template('invoices.html')

@invoices_bp.route('/api/set-viewing-date', methods=['POST'])
def set_viewing_date():
    """Define a data que o usuário está visualizando"""
    data = request.json
    month = int(data.get('month'))
    year = int(data.get('year'))
    
    session['viewing_month'] = month
    session['viewing_year'] = year
    
    return jsonify({
        'success': True,
        'viewing_month': month,
        'viewing_year': year
    })

@invoices_bp.route('/api/get-viewing-date', methods=['GET'])
def get_viewing_date():
    """Retorna a data que o usuário está visualizando"""
    today = datetime.now()
    month = session.get('viewing_month', today.month)
    year = session.get('viewing_year', today.year)
    
    return jsonify({
        'viewing_month': month,
        'viewing_year': year,
        'current_month': today.month,
        'current_year': today.year
    })

@invoices_bp.route('/api/reset-viewing-date', methods=['POST'])
def reset_viewing_date():
    """Volta para a data atual (hoje)"""
    session.pop('viewing_month', None)
    session.pop('viewing_year', None)
    
    today = datetime.now()
    return jsonify({
        'success': True,
        'viewing_month': today.month,
        'viewing_year': today.year
    })

@invoices_bp.route('/api/invoices', methods=['GET'])
def get_invoices():
    """Lista faturas de todos os cartões"""
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    
    if not month or not year:
        today = datetime.now()
        month = session.get('viewing_month', today.month)
        year = session.get('viewing_year', today.year)
    
    cards = CreditCard.query.filter_by(active=True).all()
    invoices_data = []
    
    for card in cards:
        # Calcular valor da fatura para este mês
        amount = card.get_bill_for_month(month, year)
        
        # Buscar ou criar fatura
        invoice = Invoice.query.filter_by(
            card_id=card.id,
            month=month,
            year=year
        ).first()
        
        if not invoice and amount > 0:
            # Criar fatura automaticamente
            due_day = min(card.due_day, monthrange(year, month)[1])
            due_date = datetime(year, month, due_day)
            
            invoice = Invoice(
                card_id=card.id,
                month=month,
                year=year,
                amount=amount,
                due_date=due_date,
                status='open'
            )
            db.session.add(invoice)
            db.session.commit()
        elif invoice:
            # Atualizar valor se mudou
            if invoice.amount != amount:
                invoice.amount = amount
                db.session.commit()
        
        if invoice or amount > 0:
            # Buscar parcelas deste período
            closing_day = min(card.closing_day, monthrange(year, month)[1])
            closing_date = datetime(year, month, closing_day)
            
            prev_month = month - 1 if month > 1 else 12
            prev_year = year if month > 1 else year - 1
            start_date = datetime(prev_year, prev_month, min(card.closing_day, monthrange(prev_year, prev_month)[1]))
            
            installments = Installment.query.join(Transaction).filter(
                Transaction.card_id == card.id,
                Installment.due_date >= start_date,
                Installment.due_date < closing_date
            ).all()
            
            invoices_data.append({
                'invoice': invoice.to_dict() if invoice else None,
                'card': card.to_dict(),
                'amount': amount,
                'installments_count': len(installments),
                'installments': [inst.to_dict() for inst in installments]
            })
    
    return jsonify(invoices_data)

@invoices_bp.route('/api/invoices/<int:invoice_id>/pay', methods=['POST'])
def pay_invoice(invoice_id):
    """Marca uma fatura como paga"""
    invoice = Invoice.query.get_or_404(invoice_id)
    invoice.status = 'paid'
    invoice.paid_date = datetime.utcnow()
    
    # Marcar todas as parcelas como pagas
    card = invoice.card
    closing_day = min(card.closing_day, monthrange(invoice.year, invoice.month)[1])
    closing_date = datetime(invoice.year, invoice.month, closing_day)
    
    prev_month = invoice.month - 1 if invoice.month > 1 else 12
    prev_year = invoice.year if invoice.month > 1 else invoice.year - 1
    start_date = datetime(prev_year, prev_month, min(card.closing_day, monthrange(prev_year, prev_month)[1]))
    
    installments = Installment.query.join(Transaction).filter(
        Transaction.card_id == card.id,
        Installment.due_date >= start_date,
        Installment.due_date < closing_date,
        Installment.paid == False
    ).all()
    
    for inst in installments:
        inst.paid = True
        inst.paid_date = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify(invoice.to_dict())

@invoices_bp.route('/api/invoices/<int:invoice_id>/unpay', methods=['POST'])
def unpay_invoice(invoice_id):
    """Desmarca uma fatura como paga (despagar)"""
    invoice = Invoice.query.get_or_404(invoice_id)
    invoice.status = 'open'
    invoice.paid_date = None
    
    # Desmarcar todas as parcelas
    card = invoice.card
    closing_day = min(card.closing_day, monthrange(invoice.year, invoice.month)[1])
    closing_date = datetime(invoice.year, invoice.month, closing_day)
    
    prev_month = invoice.month - 1 if invoice.month > 1 else 12
    prev_year = invoice.year if invoice.month > 1 else invoice.year - 1
    start_date = datetime(prev_year, prev_month, min(card.closing_day, monthrange(prev_year, prev_month)[1]))
    
    installments = Installment.query.join(Transaction).filter(
        Transaction.card_id == card.id,
        Installment.due_date >= start_date,
        Installment.due_date < closing_date
    ).all()
    
    for inst in installments:
        inst.paid = False
        inst.paid_date = None
    
    db.session.commit()
    
    return jsonify(invoice.to_dict())

@invoices_bp.route('/api/timeline', methods=['GET'])
def get_timeline():
    """Retorna timeline de faturas (12 meses)"""
    today = datetime.now()
    current_month = today.month
    current_year = today.year
    
    timeline = []
    
    # 12 meses: 6 passados + atual + 5 futuros
    for offset in range(-6, 6):
        month = current_month + offset
        year = current_year
        
        while month < 1:
            month += 12
            year -= 1
        while month > 12:
            month -= 12
            year += 1
        
        cards = CreditCard.query.filter_by(active=True).all()
        total_month = sum(card.get_bill_for_month(month, year) for card in cards)
        
        # Verificar se tem faturas pagas
        invoices = Invoice.query.filter_by(month=month, year=year).all()
        all_paid = len(invoices) > 0 and all(inv.status == 'paid' for inv in invoices)
        
        month_names = ['', 'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
        
        timeline.append({
            'month': month,
            'year': year,
            'month_name': month_names[month],
            'amount': total_month,
            'is_current': month == current_month and year == current_year,
            'is_past': year < current_year or (year == current_year and month < current_month),
            'is_paid': all_paid
        })
    
    return jsonify(timeline)