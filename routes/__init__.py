from flask import Blueprint

def register_routes(app):
    """Registra todas as rotas da aplicação"""
    from .cards import cards_bp
    from .bills import bills_bp
    from .accounts import accounts_bp
    from .dashboard import dashboard_bp
    from .invoices import invoices_bp
    
    app.register_blueprint(cards_bp)
    app.register_blueprint(bills_bp)
    app.register_blueprint(accounts_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(invoices_bp)