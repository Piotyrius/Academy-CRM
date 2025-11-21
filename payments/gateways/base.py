"""
Base payment gateway interface.
"""
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Dict, Optional


class PaymentGateway(ABC):
    """Abstract base class for payment gateways."""
    
    @abstractmethod
    def process_payment(self, amount: Decimal, currency: str, **kwargs) -> Dict:
        """
        Process a payment.
        
        Args:
            amount: Payment amount
            currency: Currency code
            **kwargs: Additional gateway-specific parameters
            
        Returns:
            Dict with payment result including:
            - success: bool
            - transaction_id: str
            - response_data: dict
        """
        pass
    
    @abstractmethod
    def refund_payment(self, transaction_id: str, amount: Decimal, **kwargs) -> Dict:
        """
        Refund a payment.
        
        Args:
            transaction_id: Original transaction ID
            amount: Refund amount
            **kwargs: Additional gateway-specific parameters
            
        Returns:
            Dict with refund result including:
            - success: bool
            - refund_id: str
            - response_data: dict
        """
        pass
    
    @abstractmethod
    def verify_payment(self, transaction_id: str) -> Dict:
        """
        Verify a payment status.
        
        Args:
            transaction_id: Transaction ID to verify
            
        Returns:
            Dict with verification result including:
            - success: bool
            - status: str
            - response_data: dict
        """
        pass

