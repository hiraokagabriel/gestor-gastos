from flask import Blueprint, request, jsonify, render_template
from models import Invoice, Bill, CreditCard, Installment, Transaction, Account
from database import db
from datetime import datetime
from calendar import monthrange
from dateutil.relativedelta import relativedelta
import traceback

calendar_bp = Blueprint('calendar', __name__, url_prefix='/calendar')

@calendar_bp.route('/')
def index():
    """Página do calendário"""
    return render_template('calendar.html')


def _month_start(d: datetime) -> datetime:
    return datetime(d.year, d.month, 1)


def _ensure_recurring_materialized_for_range(start_date: datetime, end_date: datetime) -> int:
    """Materializa instâncias mensais (filhos) para todas as origens recorrentes dentro do range.

    Faz commit apenas se criar algo. Mantém o calendário alinhado com a aba de contas.
    """
    origins = Account.query.filter(
        Account.recurring == True,
        Account.parent_id.is_(None)
    ).all()

    if not origins:
        return 0

    created = 0
    current = _month_start(start_date)
    end_month = _month_start(end_date)

    while current <= end_month:
        year = current.year
        month = current.month

        for origin in origins:
            if not origin.date:
                continue

            origin_ym = (origin.date.year, origin.date.month)
            target_ym = (year, month)
            if target_ym < origin_ym:
                continue

            # Se a origem já é do mês/ano, não cria filho
            if origin.date.year == year and origin.date.month == month:
                continue

            day = origin.recurring_day or origin.date.day
            max_day = monthrange(year, month)[1]
            day = min(day, max_day)
            target_date = datetime(year, month, day)

            exists = Account.query.filter(
                Account.parent_id == origin.id,
                db.extract('year', Account.date) == year,
                db.extract('month', Account.date) == month
            ).first()

            if exists:
                continue

            child = Account(
                description=origin.description,
                amount=origin.amount,
                type=origin.type,
                category=origin.category,
                date=target_date,
                recurring=False,
                parent_id=origin.id,
                recurring_day=origin.recurring_day,
                consolidated=False
            )
            db.session.add(child)
            created += 1

        current = current + relativedelta(months=1)

    if created:
        db.session.commit()

    return created


@calendar_bp.route('/api/events', methods=['GET'])
def get_events():
    """Retorna eventos para o calendário"""
    try:
        start_str = request.args.get('start')
        end_str = request.args.get('end')

        if not start_str or not end_str:
            return jsonify({'error': 'Parâmetros start e end são obrigatórios'}), 400

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

        # 3. Materializar recorrências no range e listar lançamentos reais
        _ensure_recurring_materialized_for_range(start_date, end_date)

        accounts = Account.query.filter(
            Account.date >= start_date,
            Account.date <= end_date
        ).all()

        for acc in accounts:
            try:
                is_income = acc.type == 'income'
                is_consolidated = bool(acc.consolidated)

                # Cor base: consolidado verde; pendente amarelo
                bg = '#28a745' if is_consolidated else '#ffc107'
                border = bg
                text = '#ffffff' if is_consolidated else '#000000'

                # Diferenciar recorrência com borda roxa/rosa (sem mudar muito)
                if acc.is_recurring_origin:
                    border = '#6f42c1'
                elif acc.is_recurring_child:
                    border = '#e83e8c'

                icon = '💵' if is_income else '💸'
                title = f"{icon} {acc.description}"

                events.append({
                    'id': f'account-{acc.id}',
                    'title': title,
                    'start': acc.date.strftime('%Y-%m-%d'),
                    'backgroundColor': bg,
                    'borderColor': border,
                    'textColor': text,
                    'classNames': ['event-account'],
                    'extendedProps': {
                        'type': 'account',
                        'icon': icon,
                        'typeLabel': 'Lançamento',
                        'amount': float(acc.amount),
                        'description': acc.description,
                        'status': acc.status,
                        'link': '/accounts',
                        'reference_id': acc.id,
                        'category': acc.category or 'Sem categoria',
                        'is_recurring_origin': acc.is_recurring_origin,
                        'is_recurring_child': acc.is_recurring_child
                    }
                })
            except Exception as e:
                print(f"Erro ao processar account {acc.id}: {str(e)}")

        # 4. Parcelas
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

        return jsonify(events)

    except Exception as e:
        print(f"Erro em get_events: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
