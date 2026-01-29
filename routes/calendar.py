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
        
        # Remover timezone se presente
        start_str = start_str.split('T')[0] if 'T' in start_str else start_str
        end_str = end_str.split('T')[0] if 'T' in end_str else end_str
        
        start_date = datetime.strptime(start_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_str, '%Y-%m-%d')
        
        events = []
        
        # 1. Faturas de cartões
        invoices = Invoice.query.filter(
            Invoice.due_date >= start_date,
            Invoice.due_date <= end_date
        ).all()
        
        for invoice in invoices:
            try:
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
                        'amount': float(invoice.amount),
                        'description': f'Fatura do cartão {invoice.card.name}',
                        'status': 'Paga' if is_paid else 'Aberta',
                        'link': '/invoices',
                        'reference_id': invoice.id,
                        'card_name': invoice.card.name
                    }
                })
            except Exception as e:
                print(f"Erro ao processar fatura {invoice.id}: {str(e)}")
        
        # 2. Boletos
        bills = Bill.query.filter(
            Bill.due_date >= start_date,
            Bill.due_date <= end_date
        ).all()
        
        for bill in bills:
            try:
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
                        'amount': float(bill.amount),
                        'description': bill.description,
                        'status': bill.status,
                        'link': '/bills',
                        'reference_id': bill.id,
                        'category': bill.category or 'Sem categoria'
                    }
                })
            except Exception as e:
                print(f"Erro ao processar boleto {bill.id}: {str(e)}")
        
        # 3. Despesas Recorrentes
        recurring_expenses = Account.query.filter(
            Account.recurring == True,
            Account.type == 'expense'
        ).all()
        
        for expense in recurring_expenses:
            try:
                # Pular se não tiver data
                if not expense.date:
                    print(f"Despesa recorrente {expense.id} sem data - pulando")
                    continue
                
                # Gerar eventos recorrentes para cada mês no range
                current_date = start_date
                while current_date <= end_date:
                    day = expense.date.day
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
                                'amount': float(expense.amount),
                                'description': expense.description,
                                'status': 'Recorrente',
                                'link': '/accounts',
                                'reference_id': expense.id,
                                'category': expense.category or 'Sem categoria'
                            }
                        })
                    
                    # Avançar para o próximo mês
                    if month == 12:
                        month = 1
                        year += 1
                    else:
                        month += 1
                    current_date = datetime(year, month, 1)
            except Exception as e:
                print(f"Erro ao processar despesa recorrente {expense.id}: {str(e)}")
        
        # 4. Receitas Recorrentes
        recurring_incomes = Account.query.filter(
            Account.recurring == True,
            Account.type == 'income'
        ).all()
        
        for income in recurring_incomes:
            try:
                # Pular se não tiver data
                if not income.date:
                    print(f"Receita recorrente {income.id} sem data - pulando")
                    continue
                
                # Gerar eventos recorrentes para cada mês no range
                current_date = start_date
                while current_date <= end_date:
                    day = income.date.day
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
                                'amount': float(income.amount),
                                'description': income.description,
                                'status': 'Recorrente',
                                'link': '/accounts',
                                'reference_id': income.id,
                                'category': income.category or 'Sem categoria'
                            }
                        })
                    
                    # Avançar para o próximo mês
                    if month == 12:
                        month = 1
                        year += 1
                    else:
                        month += 1
                    current_date = datetime(year, month, 1)
            except Exception as e:
                print(f"Erro ao processar receita recorrente {income.id}: {str(e)}")
        
        # 5. Parcelas
        try:
            installments = Installment.query.join(Transaction).filter(
                Installment.due_date >= start_date,
                Installment.due_date <= end_date,
                Installment.paid == False
            ).all()
            
            for inst in installments:
                try:
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
                            'amount': float(inst.amount),
                            'description': f'{inst.transaction.description} - Parcela {inst.installment_number}/{inst.total_installments}',
                            'status': 'Pendente',
                            'link': '/cards',
                            'reference_id': inst.id,
                            'card_name': inst.transaction.card.name
                        }
                    })
                except Exception as e:
                    print(f"Erro ao processar parcela {inst.id}: {str(e)}")
        except Exception as e:
            print(f"Erro ao buscar parcelas: {str(e)}")
        
        print(f"Total de eventos retornados: {len(events)}")
        return jsonify(events)
        
    except Exception as e:
        print(f"Erro em get_events: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500