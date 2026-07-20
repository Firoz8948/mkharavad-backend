from datetime import date

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PromoCode
from app.orders.models import calc_shipping


def serialize_promo(promo: PromoCode) -> dict:
    return {
        "id": promo.id,
        "code": promo.code,
        "action_type": promo.action_type,
        "percent_value": promo.percent_value,
        "valid_from": promo.valid_from.isoformat() if promo.valid_from else None,
        "valid_to": promo.valid_to.isoformat() if promo.valid_to else None,
        "is_active": promo.is_active,
        "created_at": promo.created_at.isoformat() if promo.created_at else None,
        "updated_at": promo.updated_at.isoformat() if promo.updated_at else None,
    }


def action_label(promo: PromoCode | dict) -> str:
    if isinstance(promo, dict):
        action = promo.get("action_type")
        percent = promo.get("percent_value")
    else:
        action = promo.action_type
        percent = promo.percent_value
    if action == "free_shipping":
        return "Free shipping"
    if action == "percent_off":
        return f"{int(percent) if percent else 0}% off"
    return action or ""


async def list_promos(db: AsyncSession) -> list[dict]:
    result = await db.execute(select(PromoCode).order_by(PromoCode.created_at.desc()))
    items = []
    for promo in result.scalars().all():
        data = serialize_promo(promo)
        data["action_label"] = action_label(promo)
        items.append(data)
    return items


async def create_promo(db: AsyncSession, data: dict) -> dict:
    if data.get("action_type") == "percent_off" and not data.get("percent_value"):
        raise HTTPException(status_code=400, detail="percent_value is required for percent_off")
    if data.get("action_type") == "free_shipping":
        data["percent_value"] = None

    existing = await db.execute(
        select(PromoCode).where(PromoCode.code == data["code"])
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Promo code already exists")

    promo = PromoCode(**data)
    db.add(promo)
    await db.commit()
    await db.refresh(promo)
    out = serialize_promo(promo)
    out["action_label"] = action_label(promo)
    return out


async def update_promo(db: AsyncSession, promo_id: int, data: dict) -> dict | None:
    result = await db.execute(select(PromoCode).where(PromoCode.id == promo_id))
    promo = result.scalar_one_or_none()
    if not promo:
        return None

    if "code" in data and data["code"] != promo.code:
        clash = await db.execute(
            select(PromoCode).where(PromoCode.code == data["code"])
        )
        if clash.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Promo code already exists")

    for key, value in data.items():
        setattr(promo, key, value)

    if promo.action_type == "free_shipping":
        promo.percent_value = None
    elif promo.action_type == "percent_off" and not promo.percent_value:
        raise HTTPException(status_code=400, detail="percent_value is required for percent_off")

    await db.commit()
    await db.refresh(promo)
    out = serialize_promo(promo)
    out["action_label"] = action_label(promo)
    return out


async def delete_promo(db: AsyncSession, promo_id: int) -> bool:
    result = await db.execute(select(PromoCode).where(PromoCode.id == promo_id))
    promo = result.scalar_one_or_none()
    if not promo:
        return False
    await db.delete(promo)
    await db.commit()
    return True


async def get_valid_promo(db: AsyncSession, code: str) -> PromoCode | None:
    result = await db.execute(
        select(PromoCode).where(PromoCode.code == code.strip().upper())
    )
    promo = result.scalar_one_or_none()
    if not promo or not promo.is_active:
        return None
    today = date.today()
    if today < promo.valid_from or today > promo.valid_to:
        return None
    return promo


def apply_promo_to_totals(
    promo: PromoCode,
    subtotal: float,
    shipping_charge: float | None = None,
) -> dict:
    shipping = (
        float(shipping_charge)
        if shipping_charge is not None
        else calc_shipping(subtotal)
    )
    discount = 0.0

    if promo.action_type == "free_shipping":
        shipping = 0.0
    elif promo.action_type == "percent_off":
        pct = float(promo.percent_value or 0)
        discount = round(subtotal * pct / 100, 2)

    total = round(max(subtotal - discount, 0) + shipping, 2)
    return {
        "valid": True,
        "code": promo.code,
        "action_type": promo.action_type,
        "percent_value": promo.percent_value,
        "action_label": action_label(promo),
        "discount_amount": discount,
        "shipping_charge": shipping,
        "subtotal": subtotal,
        "total": total,
        "message": f"Promo applied: {action_label(promo)}",
    }


async def validate_promo(
    db: AsyncSession,
    code: str,
    subtotal: float,
    shipping_charge: float | None = None,
) -> dict:
    promo = await get_valid_promo(db, code)
    if not promo:
        raise HTTPException(status_code=400, detail="Invalid or expired promo code")
    return apply_promo_to_totals(promo, subtotal, shipping_charge)


async def resolve_promo_for_order(
    db: AsyncSession,
    code: str | None,
    subtotal: float,
    shipping_charge: float,
) -> tuple[float, float, str | None]:
    """Returns (discount_amount, shipping_charge, promo_code)."""
    if not code:
        return 0.0, shipping_charge, None
    promo = await get_valid_promo(db, code)
    if not promo:
        raise HTTPException(status_code=400, detail="Invalid or expired promo code")
    applied = apply_promo_to_totals(promo, subtotal, shipping_charge)
    return applied["discount_amount"], applied["shipping_charge"], promo.code
