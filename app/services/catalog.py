from typing import List, Optional

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import Category, Product, ProductVariant, Tag, product_tag_table
from app.models.stock import Inventory
from app.schemas.catalog import ProductCreate, ProductUpdate


async def create_category(db: AsyncSession, name: str, description: str | None = None) -> Category:
    category = Category(name=name, description=description)
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


async def create_tag(db: AsyncSession, name: str) -> Tag:
    tag = Tag(name=name)
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return tag


async def create_product(db: AsyncSession, payload: ProductCreate) -> Product:
    product = Product(
        name=payload.name,
        description=payload.description,
        category_id=payload.category_id,
        base_price=payload.base_price,
        requires_guarantee=payload.requires_guarantee,
        units_per_box=payload.units_per_box,
        piece_type=payload.piece_type,
        condition_status=payload.condition_status,
        photo_url=payload.photo_url,
    )
    db.add(product)
    if payload.variants:
        for variant in payload.variants:
            product.variants.append(
                ProductVariant(color=variant.color, material=variant.material, price_override=variant.price_override)
            )
    if payload.tag_ids:
        tags = await db.execute(select(Tag).where(Tag.id.in_(payload.tag_ids)))
        product.tags = list(tags.scalars())
    await db.commit()
    await db.refresh(product)
    return product


async def update_product(db: AsyncSession, product: Product, payload: ProductUpdate) -> Product:
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "variants":
            product.variants.clear()
            if value:
                for variant in value:
                    product.variants.append(
                        ProductVariant(color=variant.color, material=variant.material, price_override=variant.price_override)
                    )
            continue
        if field == "tag_ids" and value is not None:
            tags = await db.execute(select(Tag).where(Tag.id.in_(value)))
            product.tags = list(tags.scalars())
            continue
        setattr(product, field, value)
    await db.commit()
    await db.refresh(product)
    return product


async def list_products(
    db: AsyncSession,
    search: Optional[str] = None,
    category_id: Optional[str] = None,
    tag_id: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    only_available: bool = False,
) -> List[Product]:
    query: Select[tuple[Product]] = (
        select(Product)
            .options(
                selectinload(Product.variants),
                selectinload(Product.tags),
                selectinload(Product.images),
            )
            .where(Product.is_active.is_(True))
    )
    if search:
        ilike = f"%{search}%"
        query = query.where(or_(Product.name.ilike(ilike), Product.description.ilike(ilike)))
    if category_id:
        query = query.where(Product.category_id == category_id)
    if tag_id:
        query = query.join(product_tag_table).where(product_tag_table.c.tag_id == tag_id)
    if min_price is not None:
        query = query.where(Product.base_price >= min_price)
    if max_price is not None:
        query = query.where(Product.base_price <= max_price)
    if only_available:
        query = query.join(Inventory).group_by(Product.id).having(func.sum(Inventory.available) > 0)
    result = await db.execute(query.order_by(Product.created_at.desc()))
    return list(result.scalars().unique())
