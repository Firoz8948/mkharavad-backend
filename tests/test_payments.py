import hashlib
import hmac

from app.config import settings
from app.payments.service import _verify_signature


def test_verify_signature_valid(monkeypatch):
    monkeypatch.setattr(settings, "RAZORPAY_KEY_SECRET", "test_secret")
    order_id = "order_123"
    payment_id = "pay_456"
    message = f"{order_id}|{payment_id}".encode()
    signature = hmac.new(b"test_secret", message, hashlib.sha256).hexdigest()
    assert _verify_signature(order_id, payment_id, signature) is True


def test_verify_signature_invalid(monkeypatch):
    monkeypatch.setattr(settings, "RAZORPAY_KEY_SECRET", "test_secret")
    assert _verify_signature("order_123", "pay_456", "bad_signature") is False
