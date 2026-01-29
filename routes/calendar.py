from flask import Blueprint, request, jsonify, render_template
from models import Invoice, Bill, CreditCard, Installment, Transaction
from datetime import datetime
import traceback

calendar_bp = Blueprint('calendar', __name__, url_prefix='/calendar')

@calendar_bp.route('/')
def index():
    """Página do calendário"""
    return render_template('calendar.html')

@calendar_bp.route('/api/events', methods=['GET'])
def get_events():
    """Retorna eventos para o calendário"""
    try:
        start_str = request.args.get('start')
        end_str = request.args.get('end')
        
        if not start_str or not end_str:
            return jsonify({'error': 'Parâmetros start e end são obrigatórios'}), 400
        
        start_date = datetime.fromisoformat(start_str.replace('Z', ''))
        end_date = datetime.fromisoformat(end_str.replace('Z', ''))
        
        events = []
        
        # 1. Faturas de cartões
        invoices = Invoice.query.filter(
            Invoice.due_date >= start_date,
            Invoice.due_date <= end_date,
            Invoice.status == 'open'
        ).all()
        
        for invoice in invoices:
            events.append({
                'id': f'invoice-{invoice.id}',
                'title': f'{invoice.card.name}: R$ {invoice.amount:.2f}',
                'start': invoice.due_date.strftime('%Y-%m-%d'),
                'backgroundColor': '#dc3545',
                'borderColor': '#dc3545',
                'extendedProps': {
                    'type': 'invoice',
                    'typeLabel': 'Fatura de Cartão',
                    'amount': invoice.amount,
                    'description': f'Fatura do cartão {invoice.card.name}',
                    'status': 'Aberta',
                    'link': '/invoices',
                    'reference_id': invoice.id
                }
            })
        
        # 2. Boletos
        bills = Bill.query.filter(
            Bill.due_date >= start_date,
            Bill.due_date <= end_date,
            Bill.paid == False
        ).all()
        
        for bill in bills:
            events.append({
                'id': f'bill-{bill.id}',
                'title': f'{bill.description}: R$ {bill.amount:.2f}',
                'start': bill.due_date.strftime('%Y-%m-%d'),
                'backgroundColor': '#ffc107',
                'borderColor': '#ffc107',
                'extendedProps': {
                    'type': 'bill',
                    'typeLabel': 'Boleto',
                    'amount': bill.amount,
                    'description': bill.description,
                    'status': bill.status,
                    'link': '/bills',
                    'reference_id': bill.id
                }
            })
        
        # 3. Parcelas individuais (opcional - pode poluir o calendário)
        # Descomente se quiser ver todas as parcelas
        '''
        installments = Installment.query.join(Transaction).filter(
            Installment.due_date >= start_date,
            Installment.due_date <= end_date,
            Installment.paid == False
        ).all()
        
        for inst in installments:
            events.append({
                'id': f'installment-{inst.id}',
                'title': f'{inst.transaction.description} ({inst.installment_number}/{inst.total_installments}): R$ {inst.amount:.2f}',
                'start': inst.due_date.strftime('%Y-%m-%d'),
                'backgroundColor': '#0dcaf0',
                'borderColor': '#0dcaf0',
                'extendedProps': {
                    'type': 'installment',
                    'typeLabel': 'Parcela',
                    'amount': inst.amount,
                    'description': f'{inst.transaction.description} - Parcela {inst.installment_number}/{inst.total_installments}',
                    'status': 'Pendente',
                    'link': '/cards',
                    'reference_id': inst.id
                }
            })
        '''
        
        return jsonify(events)
        
    except Exception as e:
        print(f"Erro em get_events: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500