import asyncio
import sys
from pathlib import Path
import re

# Add backend to python path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import AsyncSessionLocal
from app.models import Product, Category, ProductImage
from sqlalchemy import select

PRODUCTS_DATA = [
    {
        "name": "Cast Iron Tawa (10 inch)",
        "description": "Heavy-duty, pre-seasoned cast iron tawa perfect for making crispy dosas, rotis, and parathas. Appreciated for uniform heat distribution and durability.",
        "price": 799.0,
        "mrp": 1199.0,
        "category_name": "Tawas",
        "stock": 50,
        "unit": "piece",
        "weight": 2.2,
        "is_featured": True,
        "tags": ["cast iron", "tawa", "cookware", "traditional"],
        "image_url": "/uploads/products/cast_iron_tawa.webp"
    },
    {
        "name": "Traditional Iron Kadhai (2 Litre)",
        "description": "Authentic heavy iron kadhai ideal for deep frying, sautéing, and slow-cooking traditional Indian dishes. Enhances food with dietary iron naturally.",
        "price": 899.0,
        "mrp": 1299.0,
        "category_name": "Kadhai",
        "stock": 40,
        "unit": "piece",
        "weight": 2.5,
        "is_featured": True,
        "tags": ["iron", "kadhai", "cookware", "traditional"],
        "image_url": "/uploads/products/iron_kadhai.webp"
    },
    {
        "name": "Pre-Seasoned Cast Iron Skillet (8 inch)",
        "description": "Versatile cast iron skillet featuring a helper handle. Pre-seasoned with 100% natural vegetable oil. Can be used on gas stoves, induction, oven, or campfire.",
        "price": 699.0,
        "mrp": 999.0,
        "category_name": "Skillets",
        "stock": 60,
        "unit": "piece",
        "weight": 1.8,
        "is_featured": True,
        "tags": ["cast iron", "skillet", "cookware", "frypan"],
        "image_url": "/uploads/products/cast_iron_skillet.webp"
    },
    {
        "name": "Iron Spatula & Ladle Set",
        "description": "Set of 3 essential iron cooking utensils (spatula, slotted spoon, ladle) designed specifically for iron kadhais and tawas. Sturdy grip and long-lasting.",
        "price": 299.0,
        "mrp": 499.0,
        "category_name": "Utensils",
        "stock": 100,
        "unit": "set",
        "weight": 0.8,
        "is_featured": True,
        "tags": ["utensils", "spatula", "iron", "ladle"],
        "image_url": "/uploads/products/iron_utensils.webp"
    },
    {
        "name": "Handcrafted Neem Wood Spatula Set",
        "description": "Set of 4 eco-friendly neem wood cooking spoons and spatulas. Heat resistant, non-toxic, and gentle on cast iron surfaces to prevent scratching.",
        "price": 399.0,
        "mrp": 599.0,
        "category_name": "Wooden Products",
        "stock": 80,
        "unit": "set",
        "weight": 0.4,
        "is_featured": True,
        "tags": ["wooden", "spatula", "neem wood", "eco-friendly"],
        "image_url": "/uploads/products/wooden_spatulas.webp"
    },
    {
        "name": "Premium Cast Iron Cookware Combo",
        "description": "Complete cast iron cookware set including one 10-inch tawa, one 2-litre kadhai, and one 8-inch skillet. Perfect starter pack for a healthy, toxic-free kitchen.",
        "price": 2199.0,
        "mrp": 3299.0,
        "category_name": "Cast Iron Sets",
        "stock": 20,
        "unit": "set",
        "weight": 6.5,
        "is_featured": True,
        "tags": ["combo", "cast iron", "set", "cookware"],
        "image_url": "/uploads/products/cast_iron_combo.webp"
    },
    {
        "name": "Heavy Duty Iron Roti Tawa (8.5 inch)",
        "description": "Traditional iron tawa with a sturdy wooden handle to protect your hands from heat. Handcrafted specifically for quick and even roti/chapati making.",
        "price": 499.0,
        "mrp": 799.0,
        "category_name": "Tawas",
        "stock": 120,
        "unit": "piece",
        "weight": 1.4,
        "is_featured": True,
        "tags": ["tawa", "roti tawa", "iron", "cookware"],
        "image_url": "/uploads/products/iron_roti_tawa.webp"
    },
    {
        "name": "Deep Iron Kadai with Wooden Handles",
        "description": "3-Litre extra deep iron kadai equipped with double wooden handles for easy lifting and safety. Crafted for making bulk curries, frying, and festive cooking.",
        "price": 1099.0,
        "mrp": 1599.0,
        "category_name": "Kadhai",
        "stock": 35,
        "unit": "piece",
        "weight": 3.2,
        "is_featured": True,
        "tags": ["kadhai", "deep kadhai", "iron", "cookware"],
        "image_url": "/uploads/products/wooden_handle_kadai.webp"
    }
]

def slugify(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    return s

async def seed_products():
    async with AsyncSessionLocal() as session:
        # First, ensure all categories exist
        category_names = set(p["category_name"] for p in PRODUCTS_DATA)
        for cat_name in category_names:
            cat_slug = slugify(cat_name)
            existing_cat = (
                await session.execute(select(Category).where(Category.slug == cat_slug))
            ).scalar_one_or_none()
            if not existing_cat:
                new_cat = Category(
                    name=cat_name,
                    slug=cat_slug,
                    is_active=True,
                    position=10 # general position
                )
                session.add(new_cat)
                print(f"Created category: {cat_name}")
        
        await session.commit()
        
        # Load categories into a mapping dict by slug
        cat_result = await session.execute(select(Category))
        categories = {c.slug: c for c in cat_result.scalars().all()}
        
        # Clear existing products to avoid duplicates in seeding
        # This makes it easy to run the script multiple times
        existing_products = (await session.execute(select(Product))).scalars().all()
        for ep in existing_products:
            await session.delete(ep)
        await session.commit()
        print("Cleared old products.")

        # Seed products
        for p_data in PRODUCTS_DATA:
            cat = categories[slugify(p_data["category_name"])]
            product = Product(
                name=p_data["name"],
                slug=slugify(p_data["name"]),
                description=p_data["description"],
                price=p_data["price"],
                mrp=p_data["mrp"],
                category_id=cat.id,
                category=cat.name,
                stock=p_data["stock"],
                unit=p_data["unit"],
                weight=p_data["weight"],
                is_featured=p_data["is_featured"],
                is_active=True,
                tags=p_data["tags"],
                metafields={}
            )
            session.add(product)
            await session.flush() # flush to get product.id

            # Add product image
            product_image = ProductImage(
                product_id=product.id,
                url=p_data["image_url"],
                position=0
            )
            session.add(product_image)
            print(f"Seeded product: {product.name}")
        
        await session.commit()
        print("All products seeded successfully!")

if __name__ == "__main__":
    asyncio.run(seed_products())
