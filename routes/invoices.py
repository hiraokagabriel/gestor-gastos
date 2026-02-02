from flask import Blueprint, request, jsonify, render_template, session
from models import CreditCard, Invoice, Transaction, Installment, Bill, Account
from database import db
from datetime import datetime, timedelta
from calendar import monthrange
import traceback

invoices_bp = Blueprint('invoices', __name__, url_prefix='/invoices')


def _invoice_due_date(card: CreditCard, month: int, year: int) -> datetime:
    """Vencimento da fatura para um mês/ano.

    Suporta due_day > último dia do mês (ex.: fechamento + 7 dias).
    """
    due_day = card.due_day or ((card.closing_day or 1) + 7)
    days_in_month = monthrange(year, month)[1]

    if due_day <= days_in_month:
        return datetime(year, month, due_day)

    overflow = due_day - days_in_month
    return datetime(year, month, days_in_month) + timedelta(days=overflow)


def _closing_date(card: CreditCard, month: int, year: int) -> datetime:
    cd = min(card.closing_day, monthrange(year, month)[1])
    return datetime(year, month, cd)


def _sync_invoice_status(invoice: Invoice):
    """Garante status coerente baseado na data de fechamento.

    - paid nunca é alterado aqui.
    - open vira closed quando passar do fechamento.
    """
    if not invoice:
        return

    if invoice.status == 'paid':
        return

    close_dt = _closing_date(invoice.card, invoice.month, invoice.year)
    if datetime.now() >= close_dt:
        invoice.status = 'closed'
    else:
        invoice.status = 'open'


@invoices_bp.route('/')
def index():
    """Página principal de faturas"""
    return render_template('invoices.html')


@invoices_bp.route('/api/set-viewing-date', methods=['POST'])
def set_viewing_date():
    """Define a data que o usuário está visualizando"""
    try:
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
    except Exception as e:
        print(f"Erro em set_viewing_date: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@invoices_bp.route('/api/get-viewing-date', methods=['GET'])
def get_viewing_date():
    """Retorna a data que o usuário está visualizando"""
    try:
        today = datetime.now()
        month = session.get('viewing_month', today.month)
        year = session.get('viewing_year', today.year)

        return jsonify({
            'viewing_month': month,
            'viewing_year': year,
            'current_month': today.month,
            'current_year': today.year
        })
    except Exception as e:
        print(f"Erro em get_viewing_date: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@invoices_bp.route('/api/reset-viewing-date', methods=['POST'])
def reset_viewing_date():
    """Volta para a data atual (hoje)"""
    try:
        session.pop('viewing_month', None)
        session.pop('viewing_year', None)

        today = datetime.now()
        return jsonify({
            'success': True,
            'viewing_month': today.month,
            'viewing_year': today.year
        })
    except Exception as e:
        print(f"Erro em reset_viewing_date: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@invoices_bp.route('/api/invoices', methods=['GET'])
def get_invoices():
    """Lista faturas (por mês/ano) e permite filtrar por status e card_id."""
    try:
        month = request.args.get('month', type=int)
        year = request.args.get('year', type=int)
        status_filter = request.args.get('status')  # open|closed|paid|all
        card_id = request.args.get('card_id', type=int)

        if not month or not year:
            today = datetime.now()
            month = session.get('viewing_month', today.month)
            year = session.get('viewing_year', today.year)

        cards_q = CreditCard.query.filter_by(active=True)
        if card_id:
            cards_q = cards_q.filter(CreditCard.id == card_id)

        cards = cards_q.all()
        invoices_data = []

        for card in cards:
            amount = card.get_bill_for_month(month, year)

            invoice = Invoice.query.filter_by(
                card_id=card.id,
                month=month,
                year=year
            ).first()

            if not invoice and amount > 0:
                invoice = Invoice(
                    card_id=card.id,
                    month=month,
                    year=year,
                    amount=amount,
                    due_date=_invoice_due_date(card, month, year),
                    status='open'
                )
                db.session.add(invoice)
                db.session.flush()

            if invoice:
                if invoice.amount != amount:
                    invoice.amount = amount

                _sync_invoice_status(invoice)

            # status filtering (por status real, não por label)
            if status_filter and status_filter not in ('all', ''):
                if not invoice:
                    continue
                if invoice.status != status_filter:
                    continue

            if invoice or amount > 0:
                installments = Installment.query.join(Transaction).filter(
                    Transaction.card_id == card.id,
                    Installment.statement_month == month,
                    Installment.statement_year == year
                ).all()

                installments_data = []
                for inst in installments:
                    inst_dict = inst.to_dict()
                    inst_dict['transaction_id'] = inst.transaction_id
                    inst_dict['description'] = inst.transaction.description
                    installments_data.append(inst_dict)

                invoices_data.append({
                    'invoice': invoice.to_dict() if invoice else None,
                    'card': card.to_dict(),
                    'amount': amount,
                    'installments_count': len(installments),
                    'installments': installments_data
                })

        db.session.commit()
        return jsonify(invoices_data)

    except Exception as e:
        print(f"Erro geral em get_invoices: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500


@invoices_bp.route('/api/invoices/<int:invoice_id>/pay', methods=['POST'])
def pay_invoice(invoice_id):
    """Marca uma fatura como paga"""
    try:
        invoice = Invoice.query.get_or_404(invoice_id)
        invoice.status = 'paid'
        invoice.paid_date = datetime.utcnow()

        installments = Installment.query.join(Transaction).filter(
            Transaction.card_id == invoice.card_id,
            Installment.statement_month == invoice.month,
            Installment.statement_year == invoice.year,
            Installment.paid == False
        ).all()

        for inst in installments:
            inst.paid = True
            inst.paid_date = datetime.utcnow()

        db.session.commit()

        return jsonify(invoice.to_dict())
    except Exception as e:
        print(f"Erro em pay_invoice: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@invoices_bp.route('/api/invoices/<int:invoice_id>/unpay', methods=['POST'])
def unpay_invoice(invoice_id):
    """Desmarca uma fatura como paga (despagar)"""
    try:
        invoice = Invoice.query.get_or_404(invoice_id)
        invoice.status = 'open'
        invoice.paid_date = None

        installments = Installment.query.join(Transaction).filter(
            Transaction.card_id == invoice.card_id,
            Installment.statement_month == invoice.month,
            Installment.statement_year == invoice.year
        ).all()

        for inst in installments:
            inst.paid = False
            inst.paid_date = None

        _sync_invoice_status(invoice)
        db.session.commit()

        return jsonify(invoice.to_dict())
    except Exception as e:
        print(f"Erro em unpay_invoice: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@invoices_bp.route('/api/timeline', methods=['GET'])
def get_timeline():
    """Retorna timeline de faturas (12 meses)

    Mantido por compatibilidade (UI antiga).
    """
    try:
        today = datetime.now()
        current_month = today.month
        current_year = today.year

        timeline = []

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
            total_month = 0
            for card in cards:
                total_month += card.get_bill_for_month(month, year)

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
    except Exception as e:
        print(f"Erro geral em get_timeline: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500


@invoices_bp.route('/api/agenda', methods=['GET'])
def agenda():
    """Agenda/planner: próximos vencimentos (faturas + bills).

    MVP: retorna itens até N dias a partir de hoje.
    """
    try:
        days = request.args.get('days', default=15, type=int)
        if days < 1:
            days = 15

        start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=days)

        items = []

        # Faturas: considerar open/closed (não pagas)
        invoices = Invoice.query.filter(
            Invoice.status.in_(['open', 'closed']),
            Invoice.due_date >= start,
            Invoice.due_date <= end
        ).all()

        for inv in invoices:
            _sync_invoice_status(inv)
            items.append({
                'type': 'invoice',
                'date': inv.due_date.strftime('%Y-%m-%d'),
                'title': f"Fatura {inv.card.name}",
                'amount': float(inv.amount),
                'status': inv.status,
                'invoice_id': inv.id,
                'card_id': inv.card_id
            })

        # Bills
        bills = Bill.query.filter(
            Bill.paid == False,
            Bill.due_date >= start,
            Bill.due_date <= end
        ).all()

        for b in bills:
            items.append({
                'type': 'bill',
                'date': b.due_date.strftime('%Y-%m-%d'),
                'title': b.description,
                'amount': float(b.amount),
                'status': 'paid' if b.paid else 'open',
                'bill_id': b.id
            })

        db.session.commit()
        items.sort(key=lambda x: x['date'])

        return jsonify({
            'range_days': days,
            'start': start.strftime('%Y-%m-%d'),
            'end': end.strftime('%Y-%m-%d'),
            'items': items
        })

    except Exception as e:
        print(f"Erro em agenda: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
