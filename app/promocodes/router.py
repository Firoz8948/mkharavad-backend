from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_admin
from app.database import get_db
from app.promocodes import service
from app.promocodes.schemas import (
    PromoCodeCreateRequest,
    PromoCodeUpdateRequest,
    PromoValidateRequest,
)

router = APIRouter()


@router.get("/admin/all")
async def admin_list_promos(
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    return await service.list_promos(db)


@router.post("/", status_code=201)
async def create_promo(
    body: PromoCodeCreateRequest,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    return await service.create_promo(db, body.model_dump())


@router.put("/{promo_id}")
async def update_promo(
    promo_id: int,
    body: PromoCodeUpdateRequest,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    updated = await service.update_promo(db, promo_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="Promo code not found")
    return updated


@router.delete("/{promo_id}")
async def delete_promo(
    promo_id: int,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    deleted = await service.delete_promo(db, promo_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Promo code not found")
    return {"message": "Promo code deleted"}


@router.post("/validate")
async def validate_promo(
    body: PromoValidateRequest,
    db: AsyncSession = Depends(get_db),
):
    return await service.validate_promo(
        db,
        body.code,
        body.subtotal,
        body.shipping_charge,
    )
