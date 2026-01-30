from flask import Blueprint, request, jsonify, render_template, session
from models import CreditCard, Invoice, Transaction, Installment, Bill, Account
from database import db
from datetime import datetime
from calendar import monthrange
import traceback

invoices_bp = Blueprint('invoices', __name__, url_prefix='/invoices')

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

@invoices_bp.route('/api/projected-balance', methods=['GET'])
def get_projected_balance():
    """Calcula saldo projetado se pagar todas as faturas até o mês anterior"""
    try:
        month = request.args.get('month', type=int)
        year = request.args.get('year', type=int)

        if not month or not year:
            today = datetime.now()
            month = session.get('viewing_month', today.month)
            year = session.get('viewing_year', today.year)

        today = datetime.now()
        current_month = today.month
        current_year = today.year

        current_balance = 0.0

        incomes = Account.query.filter(
            Account.type == 'income',
            Account.date <= datetime.now()
        ).all()
        current_balance += sum(acc.amount for acc in incomes)

        expenses = Account.query.filter(
            Account.type == 'expense',
            Account.date <= datetime.now()
        ).all()
        current_balance -= sum(acc.amount for acc in expenses)

        paid_invoices = Invoice.query.filter(
            Invoice.status == 'paid'
        ).all()
        current_balance -= sum(inv.amount for inv in paid_invoices)

        paid_bills = Bill.query.filter(
            Bill.paid == True
        ).all()
        current_balance -= sum(bill.amount for bill in paid_bills)

        total_to_pay = 0.0

        prev_month = month - 1 if month > 1 else 12
        prev_year = year if month > 1 else year - 1

        temp_month = current_month
        temp_year = current_year

        while (temp_year < prev_year) or (temp_year == prev_year and temp_month <= prev_month):
            invoices = Invoice.query.filter_by(
                month=temp_month,
                year=temp_year,
                status='open'
            ).all()
            total_to_pay += sum(inv.amount for inv in invoices)

            first_day = datetime(temp_year, temp_month, 1)
            last_day = datetime(temp_year, temp_month, monthrange(temp_year, temp_month)[1])

            bills = Bill.query.filter(
                Bill.paid == False,
                Bill.due_date >= first_day,
                Bill.due_date <= last_day
            ).all()
            total_to_pay += sum(bill.amount for bill in bills)

            temp_month += 1
            if temp_month > 12:
                temp_month = 1
                temp_year += 1

        projected_balance = current_balance - total_to_pay

        return jsonify({
            'current_balance': round(current_balance, 2),
            'total_to_pay': round(total_to_pay, 2),
            'projected_balance': round(projected_balance, 2),
            'viewing_month': month,
            'viewing_year': year,
            'current_month': current_month,
            'current_year': current_year
        })

    except Exception as e:
        print(f"Erro em get_projected_balance: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@invoices_bp.route('/api/invoices', methods=['GET'])
def get_invoices():
    """Lista faturas de todos os cartões"""
    try:
        month = request.args.get('month', type=int)
        year = request.args.get('year', type=int)

        if not month or not year:
            today = datetime.now()
            month = session.get('viewing_month', today.month)
            year = session.get('viewing_year', today.year)

        print(f"Buscando faturas para {month}/{year}")

        cards = CreditCard.query.filter_by(active=True).all()
        invoices_data = []

        for card in cards:
            try:
                amount = card.get_bill_for_month(month, year)
                print(f"Cartão {card.name}: R$ {amount}")

                invoice = Invoice.query.filter_by(
                    card_id=card.id,
                    month=month,
                    year=year
                ).first()

                if not invoice and amount > 0:
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
                    if invoice.amount != amount:
                        invoice.amount = amount
                        db.session.commit()

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
            except Exception as card_error:
                print(f"Erro ao processar cartão {card.name}: {str(card_error)}")
                traceback.print_exc()
                continue

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

        db.session.commit()

        return jsonify(invoice.to_dict())
    except Exception as e:
        print(f"Erro em unpay_invoice: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@invoices_bp.route('/api/timeline', methods=['GET'])
def get_timeline():
    """Retorna timeline de faturas (12 meses)"""
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

            try:
                cards = CreditCard.query.filter_by(active=True).all()
                total_month = 0
                for card in cards:
                    try:
                        total_month += card.get_bill_for_month(month, year)
                    except Exception as card_error:
                        print(f"Erro ao calcular fatura do cartão {card.name} para {month}/{year}: {str(card_error)}")
                        continue

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
            except Exception as month_error:
                print(f"Erro ao processar mês {month}/{year}: {str(month_error)}")
                traceback.print_exc()
                continue

        return jsonify(timeline)
    except Exception as e:
        print(f"Erro geral em get_timeline: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500
