from flask import Blueprint, request, jsonify, render_template
from models import CreditCard, Transaction, Installment, Invoice
from database import db
from datetime import datetime, timedelta
from calendar import monthrange
from dateutil.relativedelta import relativedelta

cards_bp = Blueprint('cards', __name__, url_prefix='/cards')


def _to_int_optional(value, default=None):
    if value is None:
        return default
    if isinstance(value, str) and value.strip() == '':
        return default
    try:
        return int(value)
    except Exception:
        return default


def _to_float_optional(value, default=None):
    if value is None:
        return default
    if isinstance(value, str) and value.strip() == '':
        return default
    try:
        return float(value)
    except Exception:
        return default


def _suggest_target_statement(card: CreditCard):
    """Regra pedida:

    - Se a fatura do mês corrente (mês calendário) já fechou, antecipações vão para a próxima.
    - Se ainda não fechou, vão para a fatura atual.

    Fechou = hoje >= data de fechamento (closing_day) do mês.
    """
    today = datetime.now()
    closing_day = min(card.closing_day, monthrange(today.year, today.month)[1])
    closing_date = datetime(today.year, today.month, closing_day)

    if today >= closing_date:
        ref = datetime(today.year, today.month, 1) + relativedelta(months=1)
        return ref.month, ref.year, 'next'

    return today.month, today.year, 'current'


def _invoice_due_date(card: CreditCard, month: int, year: int) -> datetime:
    """Vencimento da fatura para um statement.

    Suporta due_day > último dia do mês (caso default seja fechamento + 7 dias e caia no mês seguinte).
    """
    due_day = card.due_day or ((card.closing_day or 1) + 7)
    days_in_month = monthrange(year, month)[1]

    if due_day <= days_in_month:
        return datetime(year, month, due_day)

    overflow = due_day - days_in_month
    return datetime(year, month, days_in_month) + timedelta(days=overflow)


def _get_or_create_invoice(card: CreditCard, month: int, year: int) -> Invoice | None:
    amount = card.get_bill_for_month(month, year)
    invoice = Invoice.query.filter_by(card_id=card.id, month=month, year=year).first()

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
        db.session.commit()

    if invoice and invoice.amount != amount:
        invoice.amount = amount
        db.session.commit()

    return invoice


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
    data = request.json or {}

    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'Nome do cartão é obrigatório.'}), 400

    closing_day = _to_int_optional(data.get('closing_day'), None)
    if not closing_day:
        closing_day = 1

    due_day = _to_int_optional(data.get('due_day'), None)
    if not due_day:
        due_day = closing_day + 7

    limit_total = _to_float_optional(data.get('limit_total'), None)
    if limit_total is None:
        limit_total = 0.0

    flag = data.get('flag')
    if isinstance(flag, str) and flag.strip() == '':
        flag = None

    last_digits = data.get('last_digits')
    if isinstance(last_digits, str):
        last_digits = last_digits.strip()
        if last_digits == '':
            last_digits = None
        elif not last_digits.isdigit() or len(last_digits) != 4:
            return jsonify({'error': 'Últimos 4 dígitos devem ter exatamente 4 números (ou ficar em branco).'}), 400

    expiry_month = _to_int_optional(data.get('expiry_month'), None)
    expiry_year = _to_int_optional(data.get('expiry_year'), None)
    if expiry_month is not None and (expiry_month < 1 or expiry_month > 12):
        return jsonify({'error': 'expiry_month deve estar entre 1 e 12.'}), 400

    card = CreditCard(
        name=name,
        limit_total=float(limit_total),
        closing_day=int(closing_day),
        due_day=int(due_day),
        flag=flag,
        last_digits=last_digits,
        expiry_month=expiry_month,
        expiry_year=expiry_year,
        active=bool(data.get('active', True))
    )

    db.session.add(card)
    db.session.commit()
    return jsonify(card.to_dict()), 201

@cards_bp.route('/api/cards/<int:card_id>', methods=['PUT'])
def update_card(card_id):
    card = CreditCard.query.get_or_404(card_id)
    data = request.json or {}

    if 'name' in data:
        name = (data.get('name') or '').strip()
        if not name:
            return jsonify({'error': 'Nome do cartão é obrigatório.'}), 400
        card.name = name

    if 'limit_total' in data:
        card.limit_total = float(_to_float_optional(data.get('limit_total'), 0.0) or 0.0)

    if 'closing_day' in data:
        cd = _to_int_optional(data.get('closing_day'), 1)
        card.closing_day = int(cd or 1)

    if 'due_day' in data:
        dd = _to_int_optional(data.get('due_day'), None)
        if not dd:
            dd = (card.closing_day or 1) + 7
        card.due_day = int(dd)

    if 'flag' in data:
        flag = data.get('flag')
        if isinstance(flag, str) and flag.strip() == '':
            flag = None
        card.flag = flag

    if 'last_digits' in data:
        last_digits = data.get('last_digits')
        if isinstance(last_digits, str):
            last_digits = last_digits.strip()
            if last_digits == '':
                last_digits = None
            elif not last_digits.isdigit() or len(last_digits) != 4:
                return jsonify({'error': 'Últimos 4 dígitos devem ter exatamente 4 números (ou ficar em branco).'}), 400
        card.last_digits = last_digits

    if 'expiry_month' in data:
        em = _to_int_optional(data.get('expiry_month'), None)
        if em is not None and (em < 1 or em > 12):
            return jsonify({'error': 'expiry_month deve estar entre 1 e 12 (ou ficar em branco).'}), 400
        card.expiry_month = em

    if 'expiry_year' in data:
        ey = _to_int_optional(data.get('expiry_year'), None)
        card.expiry_year = ey

    if 'active' in data:
        card.active = bool(data.get('active'))

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
    CreditCard.query.get_or_404(card_id)
    transactions = Transaction.query.filter_by(card_id=card_id).order_by(Transaction.date.desc()).all()
    return jsonify([t.to_dict() for t in transactions])

@cards_bp.route('/api/transactions/<int:transaction_id>', methods=['GET'])
def get_transaction(transaction_id):
    tx = Transaction.query.get_or_404(transaction_id)
    card = CreditCard.query.get(tx.card_id)
    target_month, target_year, target_kind = _suggest_target_statement(card)

    data = tx.to_dict()
    data['anticipation_target'] = {
        'month': target_month,
        'year': target_year,
        'kind': target_kind
    }
    return jsonify(data)

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

@cards_bp.route('/api/cards/<int:card_id>/pay-current-invoice', methods=['POST'])
def pay_current_invoice(card_id):
    """Atalho para pagar a fatura "atual" do cartão.

    Importante: "atual" aqui segue a regra de fechamento do cartão (igual apps):
    - Se já fechou no mês, pagar a próxima fatura.
    - Se ainda não fechou, pagar a fatura do mês corrente.

    Se month/year forem enviados, eles têm prioridade.
    """
    card = CreditCard.query.get_or_404(card_id)

    payload = request.get_json(silent=True) or {}
    month = payload.get('month')
    year = payload.get('year')

    if not month or not year:
        month, year, _ = _suggest_target_statement(card)

    invoice = _get_or_create_invoice(card, int(month), int(year))
    if not invoice:
        return jsonify({
            'error': 'Não há fatura para pagar neste período (valor 0).',
            'target': {'month': int(month), 'year': int(year)}
        }), 400

    if invoice.status == 'paid':
        return jsonify({'message': 'Fatura já está paga.', 'invoice': invoice.to_dict()}), 200

    invoice.status = 'paid'
    invoice.paid_date = datetime.utcnow()

    installments = Installment.query.join(Transaction).filter(
        Transaction.card_id == card.id,
        Installment.statement_month == invoice.month,
        Installment.statement_year == invoice.year,
        Installment.paid == False
    ).all()

    for inst in installments:
        inst.paid = True
        inst.paid_date = datetime.utcnow()

    db.session.commit()

    return jsonify({'message': 'Fatura marcada como paga.', 'invoice': invoice.to_dict()}), 200

@cards_bp.route('/api/transactions/<int:transaction_id>/anticipate', methods=['POST'])
def anticipate_installments(transaction_id):
    """Antecipar parcelas futuras de uma compra.

    Regra:
    - Destino é automático: fatura atual se ainda aberta; se fechou, próxima.
    - Só move parcelas não pagas.
    """
    tx = Transaction.query.get_or_404(transaction_id)
    card = CreditCard.query.get(tx.card_id)

    data = request.json or {}
    installment_ids = data.get('installment_ids') or []

    if not installment_ids:
        return jsonify({'error': 'Envie installment_ids.'}), 400

    target_month, target_year, target_kind = _suggest_target_statement(card)

    moved = 0
    skipped = 0

    for inst_id in installment_ids:
        inst = Installment.query.get(inst_id)
        if not inst or inst.transaction_id != tx.id:
            skipped += 1
            continue

        if inst.paid:
            skipped += 1
            continue

        if not inst.statement_month or not inst.statement_year:
            return jsonify({'error': 'Parcela sem statement_month/year. Rode a migração migrate_installments_statement_fields.py.'}), 400

        current_stmt = (inst.statement_year, inst.statement_month)
        target_stmt = (target_year, target_month)

        # Só faz sentido antecipar se a parcela está em uma fatura futura
        if current_stmt <= target_stmt:
            skipped += 1
            continue

        # Auditoria
        if not inst.original_statement_month:
            inst.original_statement_month = inst.statement_month
        if not inst.original_statement_year:
            inst.original_statement_year = inst.statement_year

        inst.anticipated_at = datetime.utcnow()
        inst.anticipated_from_month = inst.statement_month
        inst.anticipated_from_year = inst.statement_year

        # Move para a fatura destino
        inst.statement_month = target_month
        inst.statement_year = target_year
        inst.due_date = _invoice_due_date(card, target_month, target_year)

        moved += 1

    if moved:
        db.session.commit()

    return jsonify({
        'message': 'Antecipação concluída.',
        'target': {'month': target_month, 'year': target_year, 'kind': target_kind},
        'moved': moved,
        'skipped': skipped
    }), 200

@cards_bp.route('/api/simple-interest', methods=['POST'])
def simple_interest():
    """Calcula juros simples (manual) para o usuário aplicar.

    Entrada:
    - principal: valor base
    - rate_percent_month: taxa ao mês em %
    - days: número de dias

    Fórmula: J = P * (i/100) * (days/30)
    """
    data = request.json or {}
    principal = float(data.get('principal', 0))
    rate_percent_month = float(data.get('rate_percent_month', 0))
    days = float(data.get('days', 0))

    interest = principal * (rate_percent_month / 100.0) * (days / 30.0)

    return jsonify({
        'principal': round(principal, 2),
        'rate_percent_month': rate_percent_month,
        'days': days,
        'interest': round(interest, 2),
        'total': round(principal + interest, 2),
        'formula': 'J = P * (i/100) * (days/30)'
    }), 200

@cards_bp.route('/api/installments/<int:installment_id>/pay', methods=['POST'])
def pay_installment(installment_id):
    installment = Installment.query.get_or_404(installment_id)
    installment.paid = True
    installment.paid_date = datetime.utcnow()
    db.session.commit()
    return jsonify(installment.to_dict())
