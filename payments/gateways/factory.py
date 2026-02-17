"""
Payment gateway factory.
"""
from ..models import PaymentGateway as PaymentGatewayChoice
from .base import PaymentGateway
from .manual import ManualPaymentGateway


class PaymentGatewayFactory:
    """Factory for creating payment gateway instances."""
    
    _gateways = {
        PaymentGatewayChoice.MANUAL: ManualPaymentGateway,
        # Future gateways will be added here:
        # PaymentGatewayChoice.STRIPE: StripePaymentGateway,
        # PaymentGatewayChoice.PAYPAL: PayPalPaymentGateway,
    }
    
    @classmethod
    def get_gateway(cls, gateway_name: str) -> PaymentGateway:
        """
        Get payment gateway instance.
        
        Args:
            gateway_name: Gateway name (from PaymentGateway choices)
            
        Returns:
            PaymentGateway instance
            
        Raises:
            ValueError: If gateway not found
        """
        gateway_class = cls._gateways.get(gateway_name)
        if not gateway_class:
            raise ValueError(f"Payment gateway '{gateway_name}' not found.")
        
        return gateway_class()
    
    @classmethod
    def register_gateway(cls, gateway_name: str, gateway_class: type):
        """
        Register a new payment gateway.
        
        Args:
            gateway_name: Gateway name
            gateway_class: Gateway class (must inherit from PaymentGateway)
        """
        if not issubclass(gateway_class, PaymentGateway):
            raise ValueError("Gateway class must inherit from PaymentGateway")
        
        cls._gateways[gateway_name] = gateway_class

