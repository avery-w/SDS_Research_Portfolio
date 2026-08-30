from flask import current_app
from app.utils.helpers import format_currency


def register_filters(app):
    @app.template_filter('currency')
    def currency_filter(amount):
        return format_currency(amount)

    @app.template_filter('status_color')
    def status_color_filter(status):
        colors = {
            'pending': 'warning',
            'processing': 'info',
            'shipped': 'primary',
            'delivered': 'success',
            'cancelled': 'danger',
            'rejected': 'danger',
            'approved': 'success',
            'completed': 'success'
        }
        return colors.get(status, 'secondary')

    @app.context_processor
    def inject_globals():
        return {
            'platform_name': current_app.config.get('PLATFORM_NAME', 'LongCat Marketplace'),
            'platform_fee': current_app.config.get('PLATFORM_FEE_PERCENT', 5.0)
        }
