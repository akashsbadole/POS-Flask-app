from flask import Flask
from . import auth, dashboard, orders, menu, tables, inventory, kot, reports, api

def init_app(app: Flask):
    """Initialize all routes"""
    app.register_blueprint(auth.auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard.dashboard_bp)
    app.register_blueprint(orders.orders_bp, url_prefix='/orders')
    app.register_blueprint(menu.menu_bp, url_prefix='/menu')
    app.register_blueprint(tables.tables_bp, url_prefix='/tables')
    app.register_blueprint(inventory.inventory_bp, url_prefix='/inventory')
    app.register_blueprint(kot.kot_bp, url_prefix='/kot')
    app.register_blueprint(reports.reports_bp, url_prefix='/reports')
    app.register_blueprint(api.api_bp, url_prefix='/api')
