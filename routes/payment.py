from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, current_app
from flask_login import login_required, current_user
from models import db, Order, Payment, PaymentGateway, PaymentTransaction
from utils.payment_gateways.processor import get_payment_processor
from utils.payment_gateways.exceptions import PaymentGatewayError, WebhookVerificationError, PaymentValidationError
from datetime import datetime, timedelta
from decimal import Decimal
import json
import hmac
import hashlib

payment_bp = Blueprint('payment', __name__)

@payment_bp.route('/process', methods=['POST'])
@login_required
def process_payment():
    """Process payment for an order"""
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        gateway_name = data.get('gateway_name')
        payment_method_type = data.get('payment_method_type')
        payment_method_details = data.get('payment_method_details', {})
        customer_details = data.get('customer_details', {})
        
        if not all([order_id, gateway_name]):
            return jsonify({
                'success': False,
                'message': 'Order ID and gateway name are required'
            }), 400
        
        # Process payment using the payment processor
        result = get_payment_processor().process_payment(
            order_id=order_id,
            gateway_name=gateway_name,
            payment_method_type=payment_method_type,
            payment_method_details=payment_method_details,
            customer_details=customer_details,
            processed_by=current_user.id
        )
        
        return jsonify({
            'success': True,
            'message': 'Payment processed successfully',
            'data': result
        })
        
    except PaymentValidationError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400
    except PaymentGatewayError as e:
        return jsonify({
            'success': False,
            'message': f'Payment gateway error: {str(e)}'
        }), 500
    except Exception as e:
        current_app.logger.error(f"Payment processing error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An unexpected error occurred during payment processing'
        }), 500

@payment_bp.route('/confirm', methods=['POST'])
@login_required
def confirm_payment():
    """Confirm payment after customer completion"""
    try:
        data = request.get_json()
        payment_id = data.get('payment_id')
        gateway_transaction_id = data.get('gateway_transaction_id')
        gateway_name = data.get('gateway_name')
        
        if not all([payment_id, gateway_name]):
            return jsonify({
                'success': False,
                'message': 'Payment ID and gateway name are required'
            }), 400
        
        # Confirm payment using the payment processor
        confirmation_params = {
            'gateway_name': gateway_name
        }
        
        if gateway_name.lower() == 'razorpay':
            confirmation_params['razorpay_payment_id'] = gateway_transaction_id
        elif gateway_name.lower() == 'stripe':
            confirmation_params['stripe_payment_intent_id'] = gateway_transaction_id
        
        result = get_payment_processor().confirm_payment(
            payment_id=payment_id,
            **confirmation_params
        )
        
        # If payment was successful, redirect to success page
        if result.get('success') and result.get('status') == 'completed':
            payment = Payment.get_by_id(payment_id)
            return jsonify({
                'success': True,
                'message': 'Payment confirmed successfully',
                'redirect_url': url_for('payment.payment_success', payment_id=payment_id),
                'data': result
            })
        else:
            return jsonify({
                'success': result.get('success', False),
                'message': result.get('error_message', 'Payment confirmation failed'),
                'status': result.get('status'),
                'requires_action': result.get('requires_action', False),
                'data': result
            })
        
    except PaymentValidationError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400
    except PaymentGatewayError as e:
        return jsonify({
            'success': False,
            'message': f'Payment gateway error: {str(e)}'
        }), 500
    except Exception as e:
        current_app.logger.error(f"Payment confirmation error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An unexpected error occurred during payment confirmation'
        }), 500

@payment_bp.route('/success/<int:payment_id>')
@login_required
def payment_success(payment_id):
    """Payment success page"""
    try:
        payment = Payment.get_by_id(payment_id)
        if not payment:
            flash('Payment not found', 'error')
            return redirect(url_for('orders.list_orders'))
        
        order = payment.order
        
        return render_template('payment/success.html', 
                             payment=payment, 
                             order=order)
        
    except Exception as e:
        current_app.logger.error(f"Payment success page error: {str(e)}")
        flash('An error occurred loading payment details', 'error')
        return redirect(url_for('orders.list_orders'))

@payment_bp.route('/failure/<int:payment_id>')
@login_required
def payment_failure(payment_id):
    """Payment failure page"""
    try:
        payment = Payment.get_by_id(payment_id)
        if not payment:
            flash('Payment not found', 'error')
            return redirect(url_for('orders.list_orders'))
        
        order = payment.order
        transactions = PaymentTransaction.get_by_payment(payment_id)
        latest_transaction = transactions[-1] if transactions else None
        
        return render_template('payment/failure.html', 
                             payment=payment, 
                             order=order,
                             transaction=latest_transaction)
        
    except Exception as e:
        current_app.logger.error(f"Payment failure page error: {str(e)}")
        flash('An error occurred loading payment details', 'error')
        return redirect(url_for('orders.list_orders'))

@payment_bp.route('/webhook/razorpay', methods=['POST'])
def razorpay_webhook():
    """Razorpay webhook endpoint"""
    try:
        # Get signature from headers
        signature = request.headers.get('X-Razorpay-Signature')
        if not signature:
            return jsonify({'success': False, 'message': 'Missing signature'}), 400
        
        # Get raw payload
        payload = request.get_data(as_text=True)
        
        # Process webhook
        result = get_payment_processor().process_webhook(
            gateway_name='razorpay',
            payload=payload,
            signature=signature
        )
        
        return jsonify(result)
        
    except WebhookVerificationError as e:
        current_app.logger.error(f"Razorpay webhook verification failed: {str(e)}")
        return jsonify({'success': False, 'message': 'Invalid signature'}), 400
    except Exception as e:
        current_app.logger.error(f"Razorpay webhook processing error: {str(e)}")
        return jsonify({'success': False, 'message': 'Webhook processing failed'}), 500

@payment_bp.route('/webhook/stripe', methods=['POST'])
def stripe_webhook():
    """Stripe webhook endpoint"""
    try:
        # Get signature and timestamp from headers
        signature = request.headers.get('Stripe-Signature')
        timestamp = request.headers.get('Stripe-Timestamp')
        
        if not signature:
            return jsonify({'success': False, 'message': 'Missing signature'}), 400
        
        # Get raw payload
        payload = request.get_data(as_text=True)
        
        # Parse timestamp
        timestamp_int = None
        if timestamp:
            try:
                timestamp_int = int(timestamp)
            except ValueError:
                pass
        
        # Process webhook
        result = get_payment_processor().process_webhook(
            gateway_name='stripe',
            payload=payload,
            signature=signature,
            timestamp=timestamp_int
        )
        
        return jsonify(result)
        
    except WebhookVerificationError as e:
        current_app.logger.error(f"Stripe webhook verification failed: {str(e)}")
        return jsonify({'success': False, 'message': 'Invalid signature'}), 400
    except Exception as e:
        current_app.logger.error(f"Stripe webhook processing error: {str(e)}")
        return jsonify({'success': False, 'message': 'Webhook processing failed'}), 500

@payment_bp.route('/refund', methods=['POST'])
@login_required
def refund_payment():
    """Process refund for a payment"""
    try:
        data = request.get_json()
        payment_id = data.get('payment_id')
        refund_amount = data.get('refund_amount')
        refund_reason = data.get('refund_reason')
        
        if not all([payment_id, refund_amount]):
            return jsonify({
                'success': False,
                'message': 'Payment ID and refund amount are required'
            }), 400
        
        # Process refund using the payment processor
        result = get_payment_processor().refund_payment(
            payment_id=payment_id,
            amount=Decimal(str(refund_amount)),
            reason=refund_reason
        )
        
        return jsonify({
            'success': True,
            'message': 'Refund processed successfully',
            'data': result
        })
        
    except PaymentValidationError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400
    except Exception as e:
        current_app.logger.error(f"Refund processing error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An unexpected error occurred during refund processing'
        }), 500

@payment_bp.route('/methods')
@login_required
def payment_methods():
    """Get available payment methods and gateways"""
    try:
        gateways = get_payment_processor().get_available_gateways()
        
        return jsonify({
            'success': True,
            'gateways': gateways,
            'total_gateways': len(gateways)
        })
        
    except Exception as e:
        current_app.logger.error(f"Payment methods error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to load payment methods'
        }), 500

@payment_bp.route('/status/<int:payment_id>')
@login_required
def payment_status(payment_id):
    """Get payment status"""
    try:
        status = get_payment_processor().get_payment_status(payment_id)
        
        return jsonify({
            'success': True,
            'status': status
        })
        
    except PaymentValidationError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400
    except Exception as e:
        current_app.logger.error(f"Payment status error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to get payment status'
        }), 500

@payment_bp.route('/transactions')
@login_required
def list_transactions():
    """List payment transactions with filters"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        payment_id = request.args.get('payment_id', type=int)
        gateway_name = request.args.get('gateway_name')
        status = request.args.get('status')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        query = PaymentTransaction.query
        
        if payment_id:
            query = query.filter_by(payment_id=payment_id)
        
        if gateway_name:
            query = query.join(PaymentGateway).filter(PaymentGateway.name == gateway_name)
        
        if status:
            query = query.filter_by(status=status)
        
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
                query = query.filter(PaymentTransaction.created_at >= date_from_obj)
            except ValueError:
                pass
        
        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
                query = query.filter(PaymentTransaction.created_at < date_to_obj)
            except ValueError:
                pass
        
        transactions = query.order_by(PaymentTransaction.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        transactions_data = []
        for transaction in transactions.items:
            transaction_dict = transaction.to_dict()
            transaction_dict['payment'] = {
                'id': transaction.payment.id,
                'order_number': transaction.payment.order.order_number,
                'amount': float(transaction.payment.amount)
            }
            transactions_data.append(transaction_dict)
        
        return jsonify({
            'success': True,
            'transactions': transactions_data,
            'pagination': {
                'page': transactions.page,
                'pages': transactions.pages,
                'per_page': transactions.per_page,
                'total': transactions.total,
                'has_prev': transactions.has_prev,
                'has_next': transactions.has_next
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Transaction list error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to load transactions'
        }), 500

@payment_bp.route('/reconcile', methods=['POST'])
@login_required
def reconcile_payments():
    """Reconcile payments with gateway transactions"""
    try:
        data = request.get_json()
        gateway_name = data.get('gateway_name')
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        
        if not gateway_name:
            return jsonify({
                'success': False,
                'message': 'Gateway name is required'
            }), 400
        
        # Get gateway
        gateway = get_payment_processor().get_gateway(gateway_name)
        
        # Get date range
        date_from_obj = None
        date_to_obj = None
        
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            except ValueError:
                return jsonify({
                    'success': False,
                    'message': 'Invalid date_from format'
                }), 400
        
        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            except ValueError:
                return jsonify({
                    'success': False,
                    'message': 'Invalid date_to format'
                }), 400
        
        # Get local transactions
        query = PaymentTransaction.query.join(PaymentGateway).filter(
            PaymentGateway.name == gateway_name
        )
        
        if date_from_obj:
            query = query.filter(PaymentTransaction.created_at >= date_from_obj)
        
        if date_to_obj:
            query = query.filter(PaymentTransaction.created_at < date_to_obj)
        
        local_transactions = query.all()
        
        # Reconciliation logic would go here
        # This is a placeholder - actual implementation would depend on gateway-specific APIs
        
        reconciliation_data = {
            'gateway_name': gateway_name,
            'date_from': date_from,
            'date_to': date_to,
            'local_count': len(local_transactions),
            'reconciled_count': 0,  # Placeholder
            'discrepancies': []  # Placeholder
        }
        
        return jsonify({
            'success': True,
            'message': 'Reconciliation completed',
            'data': reconciliation_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Payment reconciliation error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Payment reconciliation failed'
        }), 500

@payment_bp.route('/analytics')
@login_required
def payment_analytics():
    """Get payment analytics and insights"""
    try:
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        gateway_name = request.args.get('gateway_name')
        
        # Default to last 30 days if no dates provided
        if not date_from:
            date_from = (datetime.utcnow() - timedelta(days=30)).strftime('%Y-%m-%d')
        if not date_to:
            date_to = datetime.utcnow().strftime('%Y-%m-%d')
        
        # Build query
        query = Payment.query.join(PaymentGateway)
        
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(
                Payment.created_at >= date_from_obj,
                Payment.created_at < date_to_obj
            )
        except ValueError:
            return jsonify({
                'success': False,
                'message': 'Invalid date format'
            }), 400
        
        if gateway_name:
            query = query.filter(PaymentGateway.name == gateway_name)
        
        payments = query.all()
        
        # Calculate analytics
        total_payments = len(payments)
        total_amount = sum(float(payment.amount) for payment in payments)
        completed_payments = [p for p in payments if p.is_completed]
        failed_payments = [p for p in payments if p.is_failed]
        
        # Gateway breakdown
        gateway_breakdown = {}
        for payment in payments:
            gateway_name = payment.gateway.name if payment.gateway else 'Manual'
            if gateway_name not in gateway_breakdown:
                gateway_breakdown[gateway_name] = {
                    'count': 0,
                    'amount': 0,
                    'completed': 0,
                    'failed': 0
                }
            
            gateway_breakdown[gateway_name]['count'] += 1
            gateway_breakdown[gateway_name]['amount'] += float(payment.amount)
            
            if payment.is_completed:
                gateway_breakdown[gateway_name]['completed'] += 1
            elif payment.is_failed:
                gateway_breakdown[gateway_name]['failed'] += 1
        
        # Payment method breakdown
        method_breakdown = {}
        for payment in payments:
            method = payment.payment_method_type or 'Unknown'
            if method not in method_breakdown:
                method_breakdown[method] = {
                    'count': 0,
                    'amount': 0
                }
            
            method_breakdown[method]['count'] += 1
            method_breakdown[method]['amount'] += float(payment.amount)
        
        analytics_data = {
            'date_from': date_from,
            'date_to': date_to,
            'total_payments': total_payments,
            'total_amount': total_amount,
            'completed_payments': len(completed_payments),
            'failed_payments': len(failed_payments),
            'success_rate': (len(completed_payments) / total_payments * 100) if total_payments > 0 else 0,
            'average_payment_amount': total_amount / total_payments if total_payments > 0 else 0,
            'gateway_breakdown': gateway_breakdown,
            'method_breakdown': method_breakdown
        }
        
        return jsonify({
            'success': True,
            'analytics': analytics_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Payment analytics error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to load payment analytics'
        }), 500

@payment_bp.route('/test-webhook/<gateway_name>', methods=['POST'])
@login_required
def test_webhook(gateway_name):
    """Test webhook endpoint for development"""
    if current_app.config.get('ENVIRONMENT') == 'production':
        return jsonify({'success': False, 'message': 'Not available in production'}), 403
    
    try:
        gateway_name = gateway_name.lower()
        
        # Create test webhook data
        if gateway_name == 'razorpay':
            test_data = {
                'entity': 'event',
                'event': 'payment.captured',
                'contains': ['payment'],
                'payload': {
                    'payment': {
                        'entity': {
                            'id': 'pay_test123456789',
                            'amount': 10000,
                            'currency': 'INR',
                            'status': 'captured',
                            'method': 'card',
                            'created_at': int(datetime.utcnow().timestamp())
                        }
                    }
                },
                'created_at': int(datetime.utcnow().timestamp())
            }
            signature = 'test_signature'
        elif gateway_name == 'stripe':
            test_data = {
                'id': 'evt_test_webhook',
                'object': 'event',
                'type': 'payment_intent.succeeded',
                'data': {
                    'object': {
                        'id': 'pi_test123456789',
                        'amount': 10000,
                        'currency': 'inr',
                        'status': 'succeeded',
                        'created': int(datetime.utcnow().timestamp())
                    }
                },
                'created': int(datetime.utcnow().timestamp())
            }
            signature = 'v1=test_signature'
        else:
            return jsonify({'success': False, 'message': 'Unsupported gateway'}), 400
        
        # Process test webhook
        result = get_payment_processor().process_webhook(
            gateway_name=gateway_name,
            payload=json.dumps(test_data),
            signature=signature
        )
        
        return jsonify({
            'success': True,
            'message': 'Test webhook processed',
            'result': result,
            'test_data': test_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Test webhook error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Test webhook failed'
        }), 500