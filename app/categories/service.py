import re
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common import serialize_product
from app.models import Category, Product, ProductVariant, SubCategory


def slugify(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    return s


async def _unique_slug(
    db: AsyncSession, model, base: str, exclude_id: int | None = None
) -> str:
    slug = slugify(base) or "item"
    query = select(model).where(model.slug == slug)
    if exclude_id is not None:
        query = query.where(model.id != exclude_id)
    existing = (await db.execute(query)).scalar_one_or_none()
    if not existing:
        return slug
    return f"{slug}-{int(datetime.now(timezone.utc).timestamp())}"


def serialize_subcategory(
    sub: SubCategory,
    product_count: int = 0,
    category_name: str | None = None,
) -> dict:
    return {
        "id": sub.id,
        "category_id": sub.category_id,
        "name": sub.name,
        "slug": sub.slug,
        "description": sub.description,
        "image_url": sub.image_url,
        "is_active": sub.is_active,
        "position": sub.position,
        "product_count": product_count,
        "category_name": category_name
        or (sub.category.name if getattr(sub, "category", None) else None),
        "created_at": sub.created_at.isoformat() if sub.created_at else None,
        "updated_at": sub.updated_at.isoformat() if sub.updated_at else None,
    }


def serialize_category(
    category: Category,
    *,
    subcategory_count: int = 0,
    product_count: int = 0,
    subcategories: list | None = None,
) -> dict:
    return {
        "id": category.id,
        "name": category.name,
        "slug": category.slug,
        "description": category.description,
        "image_url": category.image_url,
        "is_active": category.is_active,
        "position": category.position,
        "subcategory_count": subcategory_count,
        "product_count": product_count,
        "subcategories": subcategories or [],
        "created_at": category.created_at.isoformat() if category.created_at else None,
        "updated_at": category.updated_at.isoformat() if category.updated_at else None,
    }


async def _product_counts_by_subcategory(db: AsyncSession) -> dict[int, int]:
    rows = await db.execute(
        select(Product.subcategory_id, func.count(Product.id)).group_by(
            Product.subcategory_id
        )
    )
    return {row[0]: row[1] for row in rows.all() if row[0] is not None}


async def get_all_categories(
    db: AsyncSession,
    include_inactive: bool = False,
) -> list:
    query = (
        select(Category)
        .options(selectinload(Category.subcategories))
        .order_by(Category.position, Category.name)
    )
    if not include_inactive:
        query = query.where(Category.is_active == True)  # noqa: E712

    result = await db.execute(query)
    categories = result.scalars().all()
    product_counts = await _product_counts_by_subcategory(db)

    out = []
    for cat in categories:
        subs = cat.subcategories or []
        if not include_inactive:
            subs = [s for s in subs if s.is_active]
        subs = sorted(subs, key=lambda s: (s.position, s.name))
        sub_payload = [
            serialize_subcategory(
                s, product_counts.get(s.id, 0), category_name=cat.name
            )
            for s in subs
        ]
        total_products = sum(s["product_count"] for s in sub_payload)
        out.append(
            serialize_category(
                cat,
                subcategory_count=len(sub_payload),
                product_count=total_products,
                subcategories=sub_payload,
            )
        )
    return out


async def get_category_by_id(db: AsyncSession, category_id: int) -> Optional[dict]:
    result = await db.execute(
        select(Category)
        .options(selectinload(Category.subcategories))
        .where(Category.id == category_id)
    )
    cat = result.scalar_one_or_none()
    if not cat:
        return None

    product_counts = await _product_counts_by_subcategory(db)
    subs = sorted(cat.subcategories or [], key=lambda s: (s.position, s.name))
    sub_payload = [
        serialize_subcategory(s, product_counts.get(s.id, 0), category_name=cat.name)
        for s in subs
    ]
    return serialize_category(
        cat,
        subcategory_count=len(sub_payload),
        product_count=sum(s["product_count"] for s in sub_payload),
        subcategories=sub_payload,
    )


async def get_category_by_slug(db: AsyncSession, slug: str) -> Optional[dict]:
    result = await db.execute(
        select(Category)
        .options(selectinload(Category.subcategories))
        .where(Category.slug == slug, Category.is_active == True)  # noqa: E712
    )
    cat = result.scalar_one_or_none()
    if not cat:
        return None

    product_counts = await _product_counts_by_subcategory(db)
    subs = [
        s
        for s in sorted(cat.subcategories or [], key=lambda x: (x.position, x.name))
        if s.is_active
    ]
    sub_payload = [
        serialize_subcategory(s, product_counts.get(s.id, 0), category_name=cat.name)
        for s in subs
    ]
    return serialize_category(
        cat,
        subcategory_count=len(sub_payload),
        product_count=sum(s["product_count"] for s in sub_payload),
        subcategories=sub_payload,
    )


async def create_category(db: AsyncSession, data: dict) -> dict:
    data = {k: v for k, v in data.items() if k != "product_ids"}
    slug = await _unique_slug(db, Category, data["name"])
    category = Category(slug=slug, **data)
    db.add(category)
    await db.commit()
    return await get_category_by_id(db, category.id)


async def update_category(db: AsyncSession, category_id: int, data: dict) -> Optional[dict]:
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    if not category:
        return None

    data = {k: v for k, v in data.items() if k != "product_ids"}
    for key, value in data.items():
        if hasattr(category, key) and value is not None:
            setattr(category, key, value)

    if "name" in data and data["name"]:
        category.slug = await _unique_slug(
            db, Category, data["name"], exclude_id=category.id
        )

    await db.commit()
    return await get_category_by_id(db, category_id)


async def delete_category(db: AsyncSession, category_id: int) -> bool:
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    if not category:
        return False

    # Clear product FKs first
    sub_ids = (
        await db.execute(
            select(SubCategory.id).where(SubCategory.category_id == category_id)
        )
    ).scalars().all()
    if sub_ids:
        await db.execute(
            update(Product)
            .where(Product.subcategory_id.in_(sub_ids))
            .values(subcategory_id=None)
        )
    await db.execute(
        update(Product)
        .where(Product.category_id == category_id)
        .values(category_id=None)
    )

    await db.delete(category)
    await db.commit()
    return True


async def set_category_image(
    db: AsyncSession, category_id: int, image_url: str
) -> Optional[dict]:
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    if not category:
        return None
    category.image_url = image_url
    await db.commit()
    return await get_category_by_id(db, category_id)


async def create_subcategory(
    db: AsyncSession, category_id: int, data: dict
) -> Optional[dict]:
    cat = (
        await db.execute(select(Category).where(Category.id == category_id))
    ).scalar_one_or_none()
    if not cat:
        return None

    product_ids = data.pop("product_ids", []) or []
    slug = await _unique_slug(db, SubCategory, f"{cat.slug}-{data['name']}")
    sub = SubCategory(category_id=category_id, slug=slug, **data)
    db.add(sub)
    await db.flush()

    if product_ids:
        await _map_products_to_subcategory(db, sub, cat, product_ids)

    await db.commit()
    return await get_subcategory_by_id(db, sub.id)


async def update_subcategory(
    db: AsyncSession, subcategory_id: int, data: dict
) -> Optional[dict]:
    result = await db.execute(
        select(SubCategory)
        .options(selectinload(SubCategory.category))
        .where(SubCategory.id == subcategory_id)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        return None

    product_ids = data.pop("product_ids", None)
    for key, value in data.items():
        if hasattr(sub, key) and value is not None:
            setattr(sub, key, value)

    if "name" in data and data["name"]:
        parent_slug = sub.category.slug if sub.category else "sub"
        sub.slug = await _unique_slug(
            db,
            SubCategory,
            f"{parent_slug}-{data['name']}",
            exclude_id=sub.id,
        )

    if product_ids is not None:
        await db.execute(
            update(Product)
            .where(Product.subcategory_id == subcategory_id)
            .values(subcategory_id=None)
        )
        if product_ids:
            await _map_products_to_subcategory(db, sub, sub.category, product_ids)

    await db.commit()
    return await get_subcategory_by_id(db, subcategory_id)


async def _map_products_to_subcategory(
    db: AsyncSession,
    sub: SubCategory,
    category: Category | None,
    product_ids: list[int],
) -> None:
    label = (
        f"{category.name} / {sub.name}" if category else sub.name
    )
    await db.execute(
        update(Product)
        .where(Product.id.in_(product_ids))
        .values(
            subcategory_id=sub.id,
            category_id=sub.category_id,
            category=label[:100],
        )
    )


async def delete_subcategory(db: AsyncSession, subcategory_id: int) -> bool:
    result = await db.execute(
        select(SubCategory).where(SubCategory.id == subcategory_id)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        return False
    await db.execute(
        update(Product)
        .where(Product.subcategory_id == subcategory_id)
        .values(subcategory_id=None)
    )
    await db.delete(sub)
    await db.commit()
    return True


async def set_subcategory_image(
    db: AsyncSession, subcategory_id: int, image_url: str
) -> Optional[dict]:
    result = await db.execute(
        select(SubCategory).where(SubCategory.id == subcategory_id)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        return None
    sub.image_url = image_url
    await db.commit()
    return await get_subcategory_by_id(db, subcategory_id)


async def get_subcategory_by_id(db: AsyncSession, subcategory_id: int) -> Optional[dict]:
    result = await db.execute(
        select(SubCategory)
        .options(selectinload(SubCategory.category))
        .where(SubCategory.id == subcategory_id)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        return None
    count = (
        await db.execute(
            select(func.count(Product.id)).where(
                Product.subcategory_id == subcategory_id
            )
        )
    ).scalar() or 0
    return serialize_subcategory(
        sub,
        count,
        category_name=sub.category.name if sub.category else None,
    )


async def get_subcategory_by_slug(db: AsyncSession, slug: str) -> Optional[dict]:
    result = await db.execute(
        select(SubCategory)
        .options(selectinload(SubCategory.category))
        .where(SubCategory.slug == slug, SubCategory.is_active == True)  # noqa: E712
    )
    sub = result.scalar_one_or_none()
    if not sub:
        return None
    count = (
        await db.execute(
            select(func.count(Product.id)).where(Product.subcategory_id == sub.id)
        )
    ).scalar() or 0
    return serialize_subcategory(
        sub,
        count,
        category_name=sub.category.name if sub.category else None,
    )


async def get_subcategory_products(
    db: AsyncSession,
    subcategory_id: int,
    page: int = 1,
    limit: int = 20,
) -> dict:
    total = (
        await db.execute(
            select(func.count(Product.id)).where(
                Product.subcategory_id == subcategory_id
            )
        )
    ).scalar() or 0

    result = await db.execute(
        select(Product)
        .options(
            selectinload(Product.images),
            selectinload(Product.variants).selectinload(ProductVariant.options),
        )
        .where(Product.subcategory_id == subcategory_id)
        .order_by(Product.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    products = [serialize_product(p) for p in result.scalars().all()]
    return {"products": products, "total": total, "page": page, "limit": limit}


async def get_category_products(
    db: AsyncSession,
    category_id: int,
    page: int = 1,
    limit: int = 20,
) -> dict:
    """Categories do not hold products directly — return empty list."""
    return {"products": [], "total": 0, "page": page, "limit": limit, "subcategories_only": True}


async def get_all_products_for_mapping(db: AsyncSession) -> list:
    result = await db.execute(
        select(Product).options(selectinload(Product.images)).order_by(Product.name)
    )
    products = result.scalars().all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "slug": p.slug,
            "category": p.category,
            "category_id": p.category_id,
            "subcategory_id": p.subcategory_id,
            "price": p.price,
            "image": p.images[0].url if p.images else None,
            "is_active": p.is_active,
        }
        for p in products
    ]


async def resolve_product_category_fields(
    db: AsyncSession, subcategory_id: int | None
) -> dict:
    """Return category_id, subcategory_id, category label for product save."""
    if not subcategory_id:
        return {}
    result = await db.execute(
        select(SubCategory)
        .options(selectinload(SubCategory.category))
        .where(SubCategory.id == int(subcategory_id))
    )
    sub = result.scalar_one_or_none()
    if not sub:
        return {}
    parent_name = sub.category.name if sub.category else ""
    label = f"{parent_name} / {sub.name}" if parent_name else sub.name
    return {
        "subcategory_id": sub.id,
        "category_id": sub.category_id,
        "category": label[:100],
    }
