from flask import Blueprint, request, jsonify, render_template
from models import Notification, Invoice, Bill, CreditCard
from database import db
from datetime import datetime, timedelta
import traceback

notifications_bp = Blueprint('notifications', __name__, url_prefix='/notifications')

@notifications_bp.route('/')
def index():
    """Página de notificações"""
    return render_template('notifications.html')

@notifications_bp.route('/api/notifications', methods=['GET'])
def get_notifications():
    """Lista todas as notificações"""
    try:
        unread_only = request.args.get('unread', 'false').lower() == 'true'
        
        query = Notification.query
        if unread_only:
            query = query.filter_by(read=False)
        
        notifications = query.order_by(Notification.created_at.desc()).limit(50).all()
        
        return jsonify([n.to_dict() for n in notifications])
    except Exception as e:
        print(f"Erro em get_notifications: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@notifications_bp.route('/api/notifications/count', methods=['GET'])
def count_unread():
    """Conta notificações não lidas"""
    try:
        count = Notification.query.filter_by(read=False).count()
        return jsonify({'count': count})
    except Exception as e:
        print(f"Erro em count_unread: {str(e)}")
        return jsonify({'error': str(e)}), 500

@notifications_bp.route('/api/notifications/<int:notification_id>/read', methods=['POST'])
def mark_as_read(notification_id):
    """Marca notificação como lida"""
    try:
        notification = Notification.query.get_or_404(notification_id)
        notification.read = True
        notification.read_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify(notification.to_dict())
    except Exception as e:
        print(f"Erro em mark_as_read: {str(e)}")
        return jsonify({'error': str(e)}), 500

@notifications_bp.route('/api/notifications/read-all', methods=['POST'])
def mark_all_as_read():
    """Marca todas como lidas"""
    try:
        Notification.query.filter_by(read=False).update({'read': True, 'read_at': datetime.utcnow()})
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Erro em mark_all_as_read: {str(e)}")
        return jsonify({'error': str(e)}), 500

@notifications_bp.route('/api/notifications/<int:notification_id>', methods=['DELETE'])
def delete_notification(notification_id):
    """Deleta uma notificação"""
    try:
        notification = Notification.query.get_or_404(notification_id)
        db.session.delete(notification)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Erro em delete_notification: {str(e)}")
        return jsonify({'error': str(e)}), 500

@notifications_bp.route('/api/notifications/generate', methods=['POST'])
def generate_notifications():
    """Gera notificações automáticas baseado no estado atual"""
    try:
        today = datetime.now()
        generated = []
        
        # 1. Verificar faturas vencendo em 5 dias
        future_date = today + timedelta(days=5)
        invoices = Invoice.query.filter(
            Invoice.status == 'open',
            Invoice.due_date <= future_date,
            Invoice.due_date >= today
        ).all()
        
        for invoice in invoices:
            # Verificar se já existe notificação
            existing = Notification.query.filter_by(
                type='invoice_due',
                reference_id=invoice.id,
                read=False
            ).first()
            
            if not existing:
                days_left = (invoice.due_date - today).days
                notification = Notification(
                    type='invoice_due',
                    title=f'Fatura vencendo em {days_left} dias',
                    message=f'A fatura do cartão {invoice.card.name} vence em {invoice.due_date.strftime("%d/%m/%Y")}. Valor: R$ {invoice.amount:.2f}',
                    priority='high' if days_left <= 2 else 'normal',
                    link=f'/invoices',
                    reference_id=invoice.id,
                    reference_type='invoice'
                )
                db.session.add(notification)
                generated.append('invoice_due')
        
        # 2. Verificar boletos vencendo em 3 dias
        future_date_bills = today + timedelta(days=3)
        bills = Bill.query.filter(
            Bill.paid == False,
            Bill.due_date <= future_date_bills,
            Bill.due_date >= today
        ).all()
        
        for bill in bills:
            existing = Notification.query.filter_by(
                type='bill_due',
                reference_id=bill.id,
                read=False
            ).first()
            
            if not existing:
                days_left = (bill.due_date - today).days
                notification = Notification(
                    type='bill_due',
                    title=f'Boleto vencendo em {days_left} dias',
                    message=f'{bill.description} vence em {bill.due_date.strftime("%d/%m/%Y")}. Valor: R$ {bill.amount:.2f}',
                    priority='urgent' if days_left == 0 else 'high',
                    link=f'/bills',
                    reference_id=bill.id,
                    reference_type='bill'
                )
                db.session.add(notification)
                generated.append('bill_due')
        
        # 3. Verificar limite de cartões (>80%)
        cards = CreditCard.query.filter_by(active=True).all()
        for card in cards:
            usage_percent = (card.get_total_used() / card.limit_total) * 100 if card.limit_total > 0 else 0
            
            if usage_percent > 80:
                existing = Notification.query.filter_by(
                    type='limit_alert',
                    reference_id=card.id,
                    read=False
                ).first()
                
                if not existing:
                    notification = Notification(
                        type='limit_alert',
                        title=f'Limite do cartão alto',
                        message=f'Você está usando {usage_percent:.1f}% do limite do {card.name}. Disponível: R$ {card.get_available_limit():.2f}',
                        priority='normal',
                        link=f'/cards',
                        reference_id=card.id,
                        reference_type='card'
                    )
                    db.session.add(notification)
                    generated.append('limit_alert')
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'generated': len(generated),
            'types': generated
        })
        
    except Exception as e:
        print(f"Erro em generate_notifications: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500