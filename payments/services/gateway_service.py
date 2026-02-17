"""
Gateway abstraction layer for handling different payment providers.

Currently, only manual payments are fully implemented via PaymentService.
Concrete gateway implementations (Stripe, PayPal, etc.) can be added here
without changing views or other business logic.
"""
from decimal import Decimal
from typing import Any

from django.utils import timezone

from ..models import PaymentGateway, PaymentMethodCode
from .invoice_service import InvoiceService
from .payment_service import PaymentService


class GatewayService:
    """
    Facade for processing payments through different gateways.

    Usage::

        GatewayService.process_payment(
            invoice=invoice,
            amount=Decimal("100.00"),
            payment_method=PaymentMethodCode.CREDIT_CARD,
            recorded_by=request.user,
            payment_gateway=PaymentGateway.STRIPE,
            gateway_payload=stripe_payload,
        )
    """

    @staticmethod
    def process_payment(
        invoice,
        amount: Decimal,
        payment_method: str,
        recorded_by,
        payment_gateway: str = PaymentGateway.MANUAL,
        **kwargs: Any,
    ):
        """
        Route payment processing to the appropriate handler based on gateway.

        For MANUAL gateway, this simply records a payment immediately using
        existing PaymentService logic. For real gateways, this method is the
        single integration point to extend.
        """
        if payment_gateway == PaymentGateway.MANUAL:
            return PaymentService.record_payment(
                invoice=invoice,
                amount=amount,
                payment_method=payment_method,
                recorded_by=recorded_by,
                payment_gateway=PaymentGateway.MANUAL,
                **kwargs,
            )

        if payment_gateway == PaymentGateway.STRIPE:
            # Placeholder for future Stripe integration.
            raise NotImplementedError(
                "Stripe gateway processing is not implemented yet. "
                "Use MANUAL gateway for offline payments."
            )

        if payment_gateway == PaymentGateway.PAYPAL:
            # Placeholder for future PayPal integration.
            raise NotImplementedError(
                "PayPal gateway processing is not implemented yet. "
                "Use MANUAL gateway for offline payments."
            )

        # Fallback for any other/unexpected gateways
        raise ValueError(f"Unsupported payment gateway: {payment_gateway}")


