from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from models import db, PaymentGateway
from utils.payment_gateways.exceptions import GatewayConfigurationError
from utils.payment_security import get_security_manager
from datetime import datetime
import json

payment_config_bp = Blueprint('payment_config', __name__)

@payment_config_bp.route('/')
@login_required
def index():
    """Payment gateway configuration index"""
    gateways = PaymentGateway.query.all()
    return render_template('payment_config/index.html', gateways=gateways)

@payment_config_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_gateway():
    """Create new payment gateway configuration"""
    if request.method == 'POST':
        try:
            data = request.get_json()
            
            # Validate required fields
            required_fields = ['name', 'display_name']
            for field in required_fields:
                if not data.get(field):
                    return jsonify({
                        'success': False,
                        'message': f'{field.title()} is required'
                    }), 400
            
            # Check if gateway name already exists
            existing = PaymentGateway.query.filter_by(name=data['name'].lower()).first()
            if existing:
                return jsonify({
                    'success': False,
                    'message': 'Gateway with this name already exists'
                }), 400
            
            # Create gateway
            gateway = PaymentGateway(
                name=data['name'],
                display_name=data['display_name'],
                is_enabled=data.get('is_enabled', False),
                is_test_mode=data.get('is_test_mode', True)
            )
            
            # Set configuration
            if data.get('api_key'):
                gateway.api_key = data['api_key']
            if data.get('secret_key'):
                gateway.secret_key = data['secret_key']
            if data.get('webhook_secret'):
                gateway.webhook_secret = data['webhook_secret']
            
            # Set supported currencies and methods
            if data.get('supported_currencies'):
                gateway.set_supported_currencies(data['supported_currencies'])
            if data.get('supported_payment_methods'):
                gateway.set_supported_payment_methods(data['supported_payment_methods'])
            
            # Set fees and limits
            if data.get('transaction_fee_percentage'):
                gateway.transaction_fee_percentage = data['transaction_fee_percentage']
            if data.get('transaction_fee_fixed'):
                gateway.transaction_fee_fixed = data['transaction_fee_fixed']
            if data.get('min_amount'):
                gateway.min_amount = data['min_amount']
            if data.get('max_amount'):
                gateway.max_amount = data['max_amount']
            if data.get('daily_transaction_limit'):
                gateway.daily_transaction_limit = data['daily_transaction_limit']
            if data.get('monthly_transaction_limit'):
                gateway.monthly_transaction_limit = data['monthly_transaction_limit']
            
            # Set additional configuration
            if data.get('additional_config'):
                gateway.additional_config = data['additional_config']
            
            db.session.add(gateway)
            db.session.commit()
            
            # Log security event
            get_security_manager().log_security_event('GATEWAY_CREATED', {
                'gateway_name': gateway.name,
                'created_by': current_user.id,
                'is_enabled': gateway.is_enabled,
                'is_test_mode': gateway.is_test_mode
            })
            
            return jsonify({
                'success': True,
                'message': 'Payment gateway created successfully',
                'gateway_id': gateway.id
            })
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Gateway creation error: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'Failed to create payment gateway'
            }), 500
    
    # GET request - show creation form
    return render_template('payment_config/create.html')

@payment_config_bp.route('/<int:gateway_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_gateway(gateway_id):
    """Edit payment gateway configuration"""
    gateway = PaymentGateway.query.get_or_404(gateway_id)
    
    if request.method == 'POST':
        try:
            data = request.get_json()
            
            # Update basic fields
            if data.get('display_name'):
                gateway.display_name = data['display_name']
            
            gateway.is_enabled = data.get('is_enabled', gateway.is_enabled)
            gateway.is_test_mode = data.get('is_test_mode', gateway.is_test_mode)
            
            # Update API keys (only if provided)
            if data.get('api_key'):
                gateway.api_key = data['api_key']
            if data.get('secret_key'):
                gateway.secret_key = data['secret_key']
            if data.get('webhook_secret'):
                gateway.webhook_secret = data['webhook_secret']
            
            # Update supported currencies and methods
            if data.get('supported_currencies'):
                gateway.set_supported_currencies(data['supported_currencies'])
            if data.get('supported_payment_methods'):
                gateway.set_supported_payment_methods(data['supported_payment_methods'])
            
            # Update fees and limits
            if data.get('transaction_fee_percentage') is not None:
                gateway.transaction_fee_percentage = data['transaction_fee_percentage']
            if data.get('transaction_fee_fixed') is not None:
                gateway.transaction_fee_fixed = data['transaction_fee_fixed']
            if data.get('min_amount') is not None:
                gateway.min_amount = data['min_amount']
            if data.get('max_amount') is not None:
                gateway.max_amount = data['max_amount']
            if data.get('daily_transaction_limit') is not None:
                gateway.daily_transaction_limit = data['daily_transaction_limit']
            if data.get('monthly_transaction_limit') is not None:
                gateway.monthly_transaction_limit = data['monthly_transaction_limit']
            
            # Update additional configuration
            if data.get('additional_config'):
                gateway.additional_config = data['additional_config']
            
            gateway.updated_at = datetime.utcnow()
            db.session.commit()
            
            # Log security event
            get_security_manager().log_security_event('GATEWAY_UPDATED', {
                'gateway_name': gateway.name,
                'updated_by': current_user.id,
                'changes': list(data.keys())
            })
            
            return jsonify({
                'success': True,
                'message': 'Payment gateway updated successfully'
            })
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Gateway update error: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'Failed to update payment gateway'
            }), 500
    
    # GET request - show edit form
    return render_template('payment_config/edit.html', gateway=gateway)

@payment_config_bp.route('/<int:gateway_id>/toggle', methods=['POST'])
@login_required
def toggle_gateway(gateway_id):
    """Toggle gateway enabled/disabled status"""
    try:
        gateway = PaymentGateway.query.get_or_404(gateway_id)
        
        gateway.is_enabled = not gateway.is_enabled
        gateway.updated_at = datetime.utcnow()
        
        if gateway.is_enabled:
            # Reset daily stats when re-enabling
            gateway.reset_daily_stats()
        
        db.session.commit()
        
        # Log security event
        get_security_manager().log_security_event('GATEWAY_TOGGLED', {
            'gateway_name': gateway.name,
            'new_status': 'enabled' if gateway.is_enabled else 'disabled',
            'toggled_by': current_user.id
        })
        
        return jsonify({
            'success': True,
            'message': f'Gateway {"enabled" if gateway.is_enabled else "disabled"} successfully',
            'is_enabled': gateway.is_enabled
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Gateway toggle error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to toggle gateway status'
        }), 500

@payment_config_bp.route('/<int:gateway_id>/test', methods=['POST'])
@login_required
def test_gateway(gateway_id):
    """Test gateway connectivity and configuration"""
    try:
        gateway = PaymentGateway.query.get_or_404(gateway_id)
        
        if not gateway.is_enabled:
            return jsonify({
                'success': False,
                'message': 'Gateway must be enabled to test'
            }), 400
        
        # Test based on gateway type
        if gateway.name == 'razorpay':
            result = test_razorpay_gateway(gateway)
        elif gateway.name == 'stripe':
            result = test_stripe_gateway(gateway)
        else:
            return jsonify({
                'success': False,
                'message': f'Testing not supported for {gateway.name}'
            }), 400
        
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Gateway test error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Gateway test failed'
        }), 500

@payment_config_bp.route('/<int:gateway_id>/suspend', methods=['POST'])
@login_required
def suspend_gateway(gateway_id):
    """Suspend gateway with reason"""
    try:
        gateway = PaymentGateway.query.get_or_404(gateway_id)
        data = request.get_json()
        reason = data.get('reason', 'Manual suspension')
        
        gateway.suspend(reason)
        db.session.commit()
        
        # Log security event
        get_security_manager().log_security_event('GATEWAY_SUSPENDED', {
            'gateway_name': gateway.name,
            'reason': reason,
            'suspended_by': current_user.id
        })
        
        return jsonify({
            'success': True,
            'message': 'Gateway suspended successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Gateway suspension error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to suspend gateway'
        }), 500

@payment_config_bp.route('/<int:gateway_id>/unsuspend', methods=['POST'])
@login_required
def unsuspend_gateway(gateway_id):
    """Unsuspend gateway"""
    try:
        gateway = PaymentGateway.query.get_or_404(gateway_id)
        
        gateway.unsuspend()
        gateway.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Log security event
        get_security_manager().log_security_event('GATEWAY_UNSUSPENDED', {
            'gateway_name': gateway.name,
            'unsuspended_by': current_user.id
        })
        
        return jsonify({
            'success': True,
            'message': 'Gateway unsuspended successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Gateway unsuspension error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to unsuspend gateway'
        }), 500

@payment_config_bp.route('/<int:gateway_id>/delete', methods=['POST'])
@login_required
def delete_gateway(gateway_id):
    """Delete gateway configuration"""
    try:
        gateway = PaymentGateway.query.get_or_404(gateway_id)
        
        # Check if gateway has transactions
        if gateway.transactions:
            return jsonify({
                'success': False,
                'message': 'Cannot delete gateway with existing transactions'
            }), 400
        
        gateway_name = gateway.name
        db.session.delete(gateway)
        db.session.commit()
        
        # Log security event
        get_security_manager().log_security_event('GATEWAY_DELETED', {
            'gateway_name': gateway_name,
            'deleted_by': current_user.id
        })
        
        return jsonify({
            'success': True,
            'message': 'Gateway deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Gateway deletion error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to delete gateway'
        }), 500

@payment_config_bp.route('/api/gateways')
@login_required
def api_gateways():
    """API endpoint to get all gateways"""
    try:
        gateways = PaymentGateway.query.all()
        gateways_data = [gateway.to_dict() for gateway in gateways]
        
        return jsonify({
            'success': True,
            'gateways': gateways_data,
            'total': len(gateways_data)
        })
        
    except Exception as e:
        current_app.logger.error(f"API gateways error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch gateways'
        }), 500

@payment_config_bp.route('/api/gateways/enabled')
@login_required
def api_enabled_gateways():
    """API endpoint to get enabled gateways"""
    try:
        gateways = PaymentGateway.get_enabled_gateways()
        gateways_data = [gateway.to_dict() for gateway in gateways]
        
        return jsonify({
            'success': True,
            'gateways': gateways_data,
            'total': len(gateways_data)
        })
        
    except Exception as e:
        current_app.logger.error(f"API enabled gateways error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch enabled gateways'
        }), 500

def test_razorpay_gateway(gateway):
    """Test Razorpay gateway connectivity"""
    try:
        from utils.payment_gateways.razorpay import RazorpayGateway
        
        razorpay_gateway = RazorpayGateway(gateway)
        
        # Test API key by fetching payment methods
        payment_methods = razorpay_gateway.get_payment_methods()
        
        return {
            'success': True,
            'message': 'Razorpay gateway test successful',
            'details': {
                'payment_methods_available': len(payment_methods),
                'api_connectivity': 'OK',
                'test_mode': gateway.is_test_mode
            }
        }
        
    except Exception as e:
        return {
            'success': False,
            'message': f'Razorpay gateway test failed: {str(e)}',
            'details': {
                'error_type': type(e).__name__,
                'api_connectivity': 'FAILED'
            }
        }

def test_stripe_gateway(gateway):
    """Test Stripe gateway connectivity"""
    try:
        from utils.payment_gateways.stripe import StripeGateway
        
        stripe_gateway = StripeGateway(gateway)
        
        # Test API key by creating a test customer
        customer = stripe_gateway.create_customer(
            name="Test Customer",
            email="test@example.com"
        )
        
        return {
            'success': True,
            'message': 'Stripe gateway test successful',
            'details': {
                'customer_created': customer['customer_id'],
                'api_connectivity': 'OK',
                'test_mode': gateway.is_test_mode
            }
        }
        
    except Exception as e:
        return {
            'success': False,
            'message': f'Stripe gateway test failed: {str(e)}',
            'details': {
                'error_type': type(e).__name__,
                'api_connectivity': 'FAILED'
            }
        }

@payment_config_bp.route('/webhook-config')
@login_required
def webhook_config():
    """Webhook configuration guide"""
    gateways = PaymentGateway.query.filter_by(is_enabled=True).all()
    
    webhook_urls = {}
    for gateway in gateways:
        if gateway.name == 'razorpay':
            webhook_urls['razorpay'] = url_for('payment.razorpay_webhook', _external=True)
        elif gateway.name == 'stripe':
            webhook_urls['stripe'] = url_for('payment.stripe_webhook', _external=True)
    
    return render_template('payment_config/webhook_config.html', webhook_urls=webhook_urls)

@payment_config_bp.route('/security-check')
@login_required
def security_check():
    """Run security compliance check"""
    try:
        gateways = PaymentGateway.query.all()
        compliance_results = []
        
        for gateway in gateways:
            # Check compliance requirements
            payment_data = {
                'gateway_name': gateway.name,
                'has_api_key': bool(gateway.api_key),
                'has_secret_key': bool(gateway.secret_key),
                'has_webhook_secret': bool(gateway.webhook_secret),
                'is_test_mode': gateway.is_test_mode,
                'is_enabled': gateway.is_enabled
            }
            
            compliance_result = get_security_manager().check_compliance_requirements(payment_data)
            
            compliance_results.append({
                'gateway': gateway.name,
                'display_name': gateway.display_name,
                'compliant': compliance_result['compliant'],
                'warnings': compliance_result['warnings'],
                'errors': compliance_result['errors'],
                'checks': {
                    'api_key_configured': bool(gateway.api_key),
                    'secret_key_configured': bool(gateway.secret_key),
                    'webhook_secret_configured': bool(gateway.webhook_secret),
                    'test_mode_active': gateway.is_test_mode
                }
            })
        
        return jsonify({
            'success': True,
            'compliance_results': compliance_results,
            'overall_compliant': all(result['compliant'] for result in compliance_results)
        })
        
    except Exception as e:
        current_app.logger.error(f"Security check error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Security compliance check failed'
        }), 500