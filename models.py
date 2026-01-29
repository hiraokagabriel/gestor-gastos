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
    limit_total = db.Column(db.Float, nullable=False)
    closing_day = db.Column(db.Integer, nullable=False)
    due_day = db.Column(db.Integer, nullable=False)
    flag = db.Column(db.String(50))
    last_digits = db.Column(db.String(4))
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    transactions = db.relationship('Transaction', backref='card', lazy=True, cascade='all, delete-orphan')
    invoices = db.relationship('Invoice', backref='card', lazy=True, cascade='all, delete-orphan')
    
    def get_bill_for_month(self, month, year):
        """Calcula o valor da fatura para um mês/ano específico"""
        closing_date = datetime(year, month, min(self.closing_day, monthrange(year, month)[1]))
        
        prev_month = month - 1 if month > 1 else 12
        prev_year = year if month > 1 else year - 1
        start_date = datetime(prev_year, prev_month, min(self.closing_day, monthrange(prev_year, prev_month)[1]))
        
        total = db.session.query(func.sum(Installment.amount)).join(Transaction).filter(
            Transaction.card_id == self.id,
            Installment.due_date >= start_date,
            Installment.due_date < closing_date
        ).scalar() or 0.0
        
        return total
    
    def get_current_bill_amount(self):
        today = datetime.now()
        return self.get_bill_for_month(today.month, today.year)
    
    def get_available_limit(self):
        used = self.get_total_used()
        return self.limit_total - used
    
    def get_total_used(self):
        total = db.session.query(func.sum(Installment.amount)).join(Transaction).filter(
            Transaction.card_id == self.id,
            Installment.paid == False
        ).scalar() or 0.0
        return total
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'limit_total': self.limit_total,
            'limit_available': self.get_available_limit(),
            'current_bill': self.get_current_bill_amount(),
            'total_used': self.get_total_used(),
            'closing_day': self.closing_day,
            'due_day': self.due_day,
            'flag': self.flag,
            'last_digits': self.last_digits,
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
    
    def create_installments(self):
        if self.installments_total == 1:
            installment = Installment(
                transaction_id=self.id,
                installment_number=1,
                total_installments=1,
                amount=self.amount,
                due_date=self.date,
                paid=False
            )
            db.session.add(installment)
        else:
            amount_per_installment = self.amount / self.installments_total
            for i in range(1, self.installments_total + 1):
                due_date = self.date + timedelta(days=30 * (i - 1))
                installment = Installment(
                    transaction_id=self.id,
                    installment_number=i,
                    total_installments=self.installments_total,
                    amount=amount_per_installment,
                    due_date=due_date,
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
            'paid_date': self.paid_date.strftime('%Y-%m-%d') if self.paid_date else None
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
    
    # SISTEMA DE RECORRÊNCIA APRIMORADO
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
        if self.consolidated:
            return 'Consolidado'
        else:
            return 'Pendente'
    
    @property
    def is_recurring_origin(self):
        """Verifica se é a conta original que gera recorrências"""
        return self.recurring and not self.parent_id
    
    @property
    def is_recurring_child(self):
        """Verifica se foi gerada automaticamente por recorrência"""
        return self.parent_id is not None
    
    def generate_next_months(self, num_months=12):
        """Gera lançamentos para os próximos N meses"""
        if not self.recurring or self.parent_id:
            return []
        
        generated = []
        base_date = self.date
        
        for i in range(1, num_months + 1):
            next_date = base_date + relativedelta(months=i)
            
            # Ajustar dia se necessário
            day = self.recurring_day or base_date.day
            max_day = monthrange(next_date.year, next_date.month)[1]
            day = min(day, max_day)
            
            next_date = datetime(next_date.year, next_date.month, day)
            
            # Verificar se já existe
            existing = Account.query.filter_by(
                parent_id=self.id,
                date=next_date
            ).first()
            
            if not existing:
                new_account = Account(
                    description=self.description,
                    amount=self.amount,
                    type=self.type,
                    category=self.category,
                    date=next_date,
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