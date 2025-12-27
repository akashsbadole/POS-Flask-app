"""Payment Gateway Exceptions"""

class PaymentGatewayError(Exception):
    """Base exception for payment gateway errors"""
    pass

class WebhookVerificationError(PaymentGatewayError):
    """Exception for webhook signature verification failures"""
    pass

class PaymentProcessingError(PaymentGatewayError):
    """Exception for payment processing errors"""
    pass

class PaymentValidationError(PaymentGatewayError):
    """Exception for payment validation errors"""
    pass

class InsufficientFundsError(PaymentGatewayError):
    """Exception for insufficient funds"""
    pass

class PaymentTimeoutError(PaymentGatewayError):
    """Exception for payment timeout"""
    pass

class GatewayConfigurationError(PaymentGatewayError):
    """Exception for gateway configuration errors"""
    pass

class RefundError(PaymentGatewayError):
    """Exception for refund processing errors"""
    pass

class CaptureError(PaymentGatewayError):
    """Exception for payment capture errors"""
    pass