"""
Manual payment gateway (for manual payment entry).
"""
from decimal import Decimal
from typing import Dict
from .base import PaymentGateway


class ManualPaymentGateway(PaymentGateway):
    """Manual payment gateway for admin-entered payments."""
    
    def process_payment(self, amount: Decimal, currency: str, **kwargs) -> Dict:
        """
        Process a manual payment (immediately completed).
        
        Args:
            amount: Payment amount
            currency: Currency code
            **kwargs: Additional parameters (not used for manual)
            
        Returns:
            Dict with payment result
        """
        return {
            'success': True,
            'transaction_id': kwargs.get('transaction_id', 'MANUAL'),
            'response_data': {
                'method': 'manual',
                'amount': str(amount),
                'currency': currency,
            }
        }
    
    def refund_payment(self, transaction_id: str, amount: Decimal, **kwargs) -> Dict:
        """
        Process a manual refund.
        
        Args:
            transaction_id: Original transaction ID
            amount: Refund amount
            **kwargs: Additional parameters
            
        Returns:
            Dict with refund result
        """
        return {
            'success': True,
            'refund_id': f"REFUND-{transaction_id}",
            'response_data': {
                'method': 'manual',
                'refund_amount': str(amount),
            }
        }
    
    def verify_payment(self, transaction_id: str) -> Dict:
        """
        Verify a manual payment (always returns completed).
        
        Args:
            transaction_id: Transaction ID to verify
            
        Returns:
            Dict with verification result
        """
        return {
            'success': True,
            'status': 'completed',
            'response_data': {
                'method': 'manual',
                'transaction_id': transaction_id,
            }
        }

