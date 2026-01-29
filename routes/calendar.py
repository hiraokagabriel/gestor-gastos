from flask import Blueprint, request, jsonify, render_template
from models import Invoice, Bill, CreditCard, Installment, Transaction, Account
from database import db
from datetime import datetime, timedelta
from calendar import monthrange
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
            Invoice.due_date <= end_date
        ).all()
        
        for invoice in invoices:
            is_paid = invoice.status == 'paid'
            events.append({
                'id': f'invoice-{invoice.id}',
                'title': f'💳 {invoice.card.name}',
                'start': invoice.due_date.strftime('%Y-%m-%d'),
                'backgroundColor': '#28a745' if is_paid else '#dc3545',
                'borderColor': '#28a745' if is_paid else '#dc3545',
                'textColor': '#ffffff',
                'classNames': ['event-invoice'],
                'extendedProps': {
                    'type': 'invoice',
                    'icon': '💳',
                    'typeLabel': 'Fatura de Cartão',
                    'amount': invoice.amount,
                    'description': f'Fatura do cartão {invoice.card.name}',
                    'status': 'Paga' if is_paid else 'Aberta',
                    'link': '/invoices',
                    'reference_id': invoice.id,
                    'card_name': invoice.card.name
                }
            })
        
        # 2. Boletos
        bills = Bill.query.filter(
            Bill.due_date >= start_date,
            Bill.due_date <= end_date
        ).all()
        
        for bill in bills:
            is_paid = bill.paid
            events.append({
                'id': f'bill-{bill.id}',
                'title': f'📄 {bill.description}',
                'start': bill.due_date.strftime('%Y-%m-%d'),
                'backgroundColor': '#28a745' if is_paid else '#ffc107',
                'borderColor': '#28a745' if is_paid else '#ffc107',
                'textColor': '#000000' if not is_paid else '#ffffff',
                'classNames': ['event-bill'],
                'extendedProps': {
                    'type': 'bill',
                    'icon': '📄',
                    'typeLabel': 'Boleto',
                    'amount': bill.amount,
                    'description': bill.description,
                    'status': bill.status,
                    'link': '/bills',
                    'reference_id': bill.id,
                    'category': bill.category
                }
            })
        
        # 3. Despesas Recorrentes
        recurring_expenses = Account.query.filter(
            Account.recurring == True,
            Account.type == 'expense'
        ).all()
        
        for expense in recurring_expenses:
            # Gerar eventos recorrentes para cada mês no range
            current_date = start_date
            while current_date <= end_date:
                # Usar o dia original da despesa ou dia 1 se não especificado
                day = expense.date.day if expense.date else 1
                year = current_date.year
                month = current_date.month
                
                # Ajustar dia se exceder o mês
                max_day = monthrange(year, month)[1]
                day = min(day, max_day)
                
                event_date = datetime(year, month, day)
                
                if start_date <= event_date <= end_date:
                    events.append({
                        'id': f'recurring-expense-{expense.id}-{year}-{month}',
                        'title': f'🔁 {expense.description}',
                        'start': event_date.strftime('%Y-%m-%d'),
                        'backgroundColor': '#6f42c1',
                        'borderColor': '#6f42c1',
                        'textColor': '#ffffff',
                        'classNames': ['event-recurring'],
                        'extendedProps': {
                            'type': 'recurring_expense',
                            'icon': '🔁',
                            'typeLabel': 'Despesa Recorrente',
                            'amount': expense.amount,
                            'description': expense.description,
                            'status': 'Recorrente',
                            'link': '/accounts',
                            'reference_id': expense.id,
                            'category': expense.category
                        }
                    })
                
                # Avançar para o próximo mês
                if month == 12:
                    month = 1
                    year += 1
                else:
                    month += 1
                current_date = datetime(year, month, 1)
        
        # 4. Receitas Recorrentes
        recurring_incomes = Account.query.filter(
            Account.recurring == True,
            Account.type == 'income'
        ).all()
        
        for income in recurring_incomes:
            # Gerar eventos recorrentes para cada mês no range
            current_date = start_date
            while current_date <= end_date:
                day = income.date.day if income.date else 1
                year = current_date.year
                month = current_date.month
                
                max_day = monthrange(year, month)[1]
                day = min(day, max_day)
                
                event_date = datetime(year, month, day)
                
                if start_date <= event_date <= end_date:
                    events.append({
                        'id': f'recurring-income-{income.id}-{year}-{month}',
                        'title': f'💵 {income.description}',
                        'start': event_date.strftime('%Y-%m-%d'),
                        'backgroundColor': '#20c997',
                        'borderColor': '#20c997',
                        'textColor': '#ffffff',
                        'classNames': ['event-income'],
                        'extendedProps': {
                            'type': 'recurring_income',
                            'icon': '💵',
                            'typeLabel': 'Receita Recorrente',
                            'amount': income.amount,
                            'description': income.description,
                            'status': 'Recorrente',
                            'link': '/accounts',
                            'reference_id': income.id,
                            'category': income.category
                        }
                    })
                
                # Avançar para o próximo mês
                if month == 12:
                    month = 1
                    year += 1
                else:
                    month += 1
                current_date = datetime(year, month, 1)
        
        # 5. Parcelas (descomentado para mostrar todas)
        installments = Installment.query.join(Transaction).filter(
            Installment.due_date >= start_date,
            Installment.due_date <= end_date,
            Installment.paid == False
        ).all()
        
        for inst in installments:
            events.append({
                'id': f'installment-{inst.id}',
                'title': f'🔹 {inst.transaction.description} ({inst.installment_number}/{inst.total_installments})',
                'start': inst.due_date.strftime('%Y-%m-%d'),
                'backgroundColor': '#0dcaf0',
                'borderColor': '#0dcaf0',
                'textColor': '#000000',
                'classNames': ['event-installment'],
                'extendedProps': {
                    'type': 'installment',
                    'icon': '🔹',
                    'typeLabel': 'Parcela',
                    'amount': inst.amount,
                    'description': f'{inst.transaction.description} - Parcela {inst.installment_number}/{inst.total_installments}',
                    'status': 'Pendente',
                    'link': '/cards',
                    'reference_id': inst.id,
                    'card_name': inst.transaction.card.name
                }
            })
        
        return jsonify(events)
        
    except Exception as e:
        print(f"Erro em get_events: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500