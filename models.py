from database import db
from datetime import datetime, timedelta
from sqlalchemy import func
from calendar import monthrange
from dateutil.relativedelta import relativedelta

class CreditCard(db.Model):
    """Modelo para Cartões de Crédito"""
    __tablename__ = 'credit_cards'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

    # Mantemos NOT NULL no schema original; quando usuário cadastrar em branco, o backend normaliza com defaults.
    limit_total = db.Column(db.Float, nullable=False)
    closing_day = db.Column(db.Integer, nullable=False)
    due_day = db.Column(db.Integer, nullable=False)

    flag = db.Column(db.String(50))
    last_digits = db.Column(db.String(4))

    # Validade do cartão (opcional)
    expiry_month = db.Column(db.Integer)
    expiry_year = db.Column(db.Integer)

    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    transactions = db.relationship('Transaction', backref='card', lazy=True, cascade='all, delete-orphan')
    invoices = db.relationship('Invoice', backref='card', lazy=True, cascade='all, delete-orphan')

    def get_bill_for_month(self, month, year):
        """Calcula o valor total da fatura para um mês/ano específico (total do ciclo, mesmo se já tiver sido pago)."""
        total = db.session.query(func.sum(Installment.amount)).join(Transaction).filter(
            Transaction.card_id == self.id,
            Installment.statement_month == month,
            Installment.statement_year == year
        ).scalar() or 0.0
        return total

    def get_open_bill_for_month(self, month, year):
        """Calcula o valor em aberto da fatura (apenas parcelas não pagas) para um mês/ano."""
        total = db.session.query(func.sum(Installment.amount)).join(Transaction).filter(
            Transaction.card_id == self.id,
            Installment.statement_month == month,
            Installment.statement_year == year,
            Installment.paid == False
        ).scalar() or 0.0
        return total

    def get_current_bill_amount(self):
        """Valor em aberto da fatura do mês atual (por mês calendário, não por range de datas)."""
        today = datetime.now()
        return self.get_open_bill_for_month(today.month, today.year)

    def get_available_limit(self):
        used = self.get_total_used()
        total = self.limit_total or 0.0
        return total - used

    def get_total_used(self):
        total = db.session.query(func.sum(Installment.amount)).join(Transaction).filter(
            Transaction.card_id == self.id,
            Installment.paid == False
        ).scalar() or 0.0
        return total

    def to_dict(self):
        today = datetime.now()
        return {
            'id': self.id,
            'name': self.name,
            'limit_total': float(self.limit_total or 0.0),
            'limit_available': float(self.get_available_limit()),
            # Compat: current_bill agora significa "em aberto" (zera quando pagar)
            'current_bill': float(self.get_current_bill_amount()),
            # Extra (não quebra front antigo): total do mês atual (mesmo se pago)
            'current_bill_total': float(self.get_bill_for_month(today.month, today.year)),
            'total_used': float(self.get_total_used()),
            'closing_day': self.closing_day,
            'due_day': self.due_day,
            'flag': self.flag,
            'last_digits': self.last_digits,
            'expiry_month': self.expiry_month,
            'expiry_year': self.expiry_year,
            'active': self.active
        }

class Transaction(db.Model):
    """Modelo para Transações de Cartão"""
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    card_id = db.Column(db.Integer, db.ForeignKey('credit_cards.id'), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    category = db.Column(db.String(50))
    installments_total = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    installments = db.relationship('Installment', backref='transaction', lazy=True, cascade='all, delete-orphan')

    def _first_statement_month_year(self):
        """Define em qual fatura a compra cai (parcela 1)."""
        card = self.card
        tx_date = self.date

        closing_day = min(card.closing_day, monthrange(tx_date.year, tx_date.month)[1])
        closing_date = datetime(tx_date.year, tx_date.month, closing_day)

        if tx_date >= closing_date:
            ref = datetime(tx_date.year, tx_date.month, 1) + relativedelta(months=1)
        else:
            ref = datetime(tx_date.year, tx_date.month, 1)

        return ref.month, ref.year

    def _invoice_due_date(self, month: int, year: int) -> datetime:
        """Calcula vencimento da fatura do cartão para um statement (mês/ano).

        Suporta due_day > último dia do mês (ex.: default fechamento + 7 dias).
        """
        card = self.card
        due_day = card.due_day or ((card.closing_day or 1) + 7)

        days_in_month = monthrange(year, month)[1]
        if due_day <= days_in_month:
            return datetime(year, month, due_day)

        overflow = due_day - days_in_month
        return datetime(year, month, days_in_month) + timedelta(days=overflow)

    def create_installments(self):
        """Cria parcelas de forma não ambígua.

        - Cada parcela recebe statement_month/year (em qual fatura aparece).
        - due_date passa a ser o vencimento do cartão naquele statement (igual apps).
        """
        first_month, first_year = self._first_statement_month_year()

        if self.installments_total == 1:
            due_date = self._invoice_due_date(first_month, first_year)
            installment = Installment(
                transaction_id=self.id,
                installment_number=1,
                total_installments=1,
                amount=self.amount,
                due_date=due_date,
                statement_month=first_month,
                statement_year=first_year,
                original_statement_month=first_month,
                original_statement_year=first_year,
                paid=False
            )
            db.session.add(installment)
        else:
            amount_per_installment = self.amount / self.installments_total
            base = datetime(first_year, first_month, 1)
            for i in range(1, self.installments_total + 1):
                ref = base + relativedelta(months=(i - 1))
                stmt_month, stmt_year = ref.month, ref.year
                due_date = self._invoice_due_date(stmt_month, stmt_year)

                installment = Installment(
                    transaction_id=self.id,
                    installment_number=i,
                    total_installments=self.installments_total,
                    amount=amount_per_installment,
                    due_date=due_date,
                    statement_month=stmt_month,
                    statement_year=stmt_year,
                    original_statement_month=stmt_month,
                    original_statement_year=stmt_year,
                    paid=False
                )
                db.session.add(installment)

    def to_dict(self):
        return {
            'id': self.id,
            'card_id': self.card_id,
            'description': self.description,
            'amount': self.amount,
            'date': self.date.strftime('%Y-%m-%d'),
            'category': self.category,
            'installments_total': self.installments_total,
            'installments': [inst.to_dict() for inst in self.installments]
        }

class Installment(db.Model):
    """Modelo para Parcelas"""
    __tablename__ = 'installments'

    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), nullable=False)
    installment_number = db.Column(db.Integer, nullable=False)
    total_installments = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    due_date = db.Column(db.DateTime, nullable=False)

    # Fonte de verdade: em qual fatura esta parcela aparece
    statement_month = db.Column(db.Integer)
    statement_year = db.Column(db.Integer)

    # Auditoria (não ambíguo): onde a parcela estava originalmente
    original_statement_month = db.Column(db.Integer)
    original_statement_year = db.Column(db.Integer)

    # Auditoria de antecipação (quando aplicável)
    anticipated_at = db.Column(db.DateTime)
    anticipated_from_month = db.Column(db.Integer)
    anticipated_from_year = db.Column(db.Integer)

    paid = db.Column(db.Boolean, default=False)
    paid_date = db.Column(db.DateTime)

    def to_dict(self):
        return {
            'id': self.id,
            'installment_number': self.installment_number,
            'total_installments': self.total_installments,
            'amount': self.amount,
            'due_date': self.due_date.strftime('%Y-%m-%d'),
            'paid': self.paid,
            'paid_date': self.paid_date.strftime('%Y-%m-%d') if self.paid_date else None,
            'statement_month': self.statement_month,
            'statement_year': self.statement_year,
            'original_statement_month': self.original_statement_month,
            'original_statement_year': self.original_statement_year,
            'anticipated_at': self.anticipated_at.strftime('%Y-%m-%d %H:%M:%S') if self.anticipated_at else None,
            'anticipated_from_month': self.anticipated_from_month,
            'anticipated_from_year': self.anticipated_from_year,
        }

class Invoice(db.Model):
    """Modelo para Faturas de Cartão"""
    __tablename__ = 'invoices'

    id = db.Column(db.Integer, primary_key=True)
    card_id = db.Column(db.Integer, db.ForeignKey('credit_cards.id'), nullable=False)
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    due_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='open')
    paid_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        today = datetime.now()
        reference_date = datetime(self.year, self.month, 1)

        if self.status == 'paid':
            status_label = 'PAGA'
        elif reference_date.year < today.year or (reference_date.year == today.year and reference_date.month < today.month):
            status_label = 'ATRASADA'
        elif reference_date.year == today.year and reference_date.month == today.month:
            status_label = 'ATUAL'
        else:
            status_label = 'FUTURA'

        return {
            'id': self.id,
            'card_id': self.card_id,
            'month': self.month,
            'year': self.year,
            'amount': self.amount,
            'due_date': self.due_date.strftime('%Y-%m-%d'),
            'status': self.status,
            'status_label': status_label,
            'paid_date': self.paid_date.strftime('%Y-%m-%d') if self.paid_date else None
        }

class Bill(db.Model):
    """Modelo para Boletos"""
    __tablename__ = 'bills'

    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    due_date = db.Column(db.DateTime, nullable=False)
    category = db.Column(db.String(50))
    barcode = db.Column(db.String(100))
    paid = db.Column(db.Boolean, default=False)
    paid_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def is_overdue(self):
        if not self.paid and self.due_date < datetime.now():
            return True
        return False

    @property
    def status(self):
        if self.paid:
            return 'Pago'
        elif self.is_overdue:
            return 'Vencido'
        else:
            return 'Pendente'

    def to_dict(self):
        return {
            'id': self.id,
            'description': self.description,
            'amount': self.amount,
            'due_date': self.due_date.strftime('%Y-%m-%d'),
            'category': self.category,
            'barcode': self.barcode,
            'paid': self.paid,
            'paid_date': self.paid_date.strftime('%Y-%m-%d') if self.paid_date else None,
            'status': self.status,
            'is_overdue': self.is_overdue
        }

class Account(db.Model):
    """Modelo para Contas Gerais (Lançamentos)"""
    __tablename__ = 'accounts'

    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(20), nullable=False)  # income, expense
    category = db.Column(db.String(50))
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # SISTEMA DE RECORRÊNCIA (origem + instâncias por mês)
    recurring = db.Column(db.Boolean, default=False)  # Se é origem de recorrência
    parent_id = db.Column(db.Integer, db.ForeignKey('accounts.id'))  # Conta pai (se foi gerada)
    recurring_day = db.Column(db.Integer)  # Dia do mês (1-31)

    # CONSOLIDAÇÃO
    consolidated = db.Column(db.Boolean, default=False)
    consolidated_date = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relacionamentos
    children = db.relationship('Account', backref=db.backref('parent', remote_side=[id]), lazy='dynamic')

    @property
    def status(self):
        return 'Consolidado' if self.consolidated else 'Pendente'

    @property
    def is_recurring_origin(self):
        return self.recurring and not self.parent_id

    @property
    def is_recurring_child(self):
        return self.parent_id is not None

    def generate_next_months(self, num_months=12):
        """Gera lançamentos para os próximos N meses.

        Evita duplicidade checando por parent_id + (year, month) (não por date exata).
        """
        if not self.recurring or self.parent_id:
            return []

        generated = []
        base_date = self.date
        if not base_date:
            return []

        day_pref = self.recurring_day or base_date.day

        for i in range(1, num_months + 1):
            next_month_date = base_date + relativedelta(months=i)

            year = next_month_date.year
            month = next_month_date.month

            max_day = monthrange(year, month)[1]
            day = min(day_pref, max_day)
            target_date = datetime(year, month, day)

            existing = Account.query.filter(
                Account.parent_id == self.id,
                db.extract('year', Account.date) == year,
                db.extract('month', Account.date) == month
            ).first()

            if existing:
                continue

            new_account = Account(
                description=self.description,
                amount=self.amount,
                type=self.type,
                category=self.category,
                date=target_date,
                recurring=False,
                parent_id=self.id,
                recurring_day=self.recurring_day,
                consolidated=False
            )
            db.session.add(new_account)
            generated.append(new_account)

        if generated:
            db.session.commit()

        return generated

    def to_dict(self):
        return {
            'id': self.id,
            'description': self.description,
            'amount': self.amount,
            'type': self.type,
            'category': self.category,
            'date': self.date.strftime('%Y-%m-%d'),
            'recurring': self.recurring,
            'parent_id': self.parent_id,
            'recurring_day': self.recurring_day,
            'consolidated': self.consolidated,
            'consolidated_date': self.consolidated_date.strftime('%Y-%m-%d') if self.consolidated_date else None,
            'status': self.status,
            'is_recurring_origin': self.is_recurring_origin,
            'is_recurring_child': self.is_recurring_child,
            'children_count': self.children.count() if self.recurring else 0
        }

class Category(db.Model):
    """Modelo para Categorias"""
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    type = db.Column(db.String(20), nullable=False)
    color = db.Column(db.String(7), default='#007bff')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'color': self.color
        }

class Notification(db.Model):
    """Modelo para Notificações"""
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), default='normal')
    read = db.Column(db.Boolean, default=False)
    link = db.Column(db.String(200))
    reference_id = db.Column(db.Integer)
    reference_type = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type,
            'title': self.title,
            'message': self.message,
            'priority': self.priority,
            'read': self.read,
            'link': self.link,
            'reference_id': self.reference_id,
            'reference_type': self.reference_type,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'read_at': self.read_at.strftime('%Y-%m-%d %H:%M:%S') if self.read_at else None
        }
