import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_operator_or_admin, get_db
from app.models.catalog import Category, Product, Tag
from app.schemas.catalog import (
    CategoryCreate,
    CategoryOut,
    CategoryUpdate,
    ProductCreate,
    ProductOut,
    ProductUpdate,
    TagCreate,
    TagOut,
)
from app.services.catalog import create_category, create_product, create_tag, list_products, update_product

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/public", response_model=list[ProductOut])
async def public_catalog(
    db: AsyncSession = Depends(get_db),
    search: Optional[str] = None,
    category_id: Optional[str] = None,
    tag_id: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    available: bool = Query(False, description="Only include products with stock"),
):
    products = await list_products(db, search, category_id, tag_id, min_price, max_price, available)
    return [ProductOut.model_validate(p) for p in products]


@router.post("/products", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
async def create_product_endpoint(payload: ProductCreate, db: AsyncSession = Depends(get_db), current_user=Depends(get_operator_or_admin)):
    product = await create_product(db, payload)
    return ProductOut.model_validate(product)


@router.get("/products", response_model=list[ProductOut])
async def list_products_admin(db: AsyncSession = Depends(get_db), current_user=Depends(get_operator_or_admin)):
    result = await db.execute(select(Product))
    return [ProductOut.model_validate(p) for p in result.scalars().all()]


@router.get("/products/{product_id}", response_model=ProductOut)
async def get_product(product_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return ProductOut.model_validate(product)


@router.patch("/products/{product_id}", response_model=ProductOut)
async def update_product_endpoint(
    product_id: uuid.UUID, payload: ProductUpdate, db: AsyncSession = Depends(get_db), current_user=Depends(get_operator_or_admin)
):
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    product = await update_product(db, product, payload)
    return ProductOut.model_validate(product)


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(product_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_operator_or_admin)):
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    await db.delete(product)
    await db.commit()
    return None


@router.post("/categories", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
async def create_category_endpoint(payload: CategoryCreate, db: AsyncSession = Depends(get_db), current_user=Depends(get_operator_or_admin)):
    category = await create_category(db, payload.name, payload.description)
    return CategoryOut.model_validate(category)


@router.get("/categories", response_model=list[CategoryOut])
async def list_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category))
    return [CategoryOut.model_validate(c) for c in result.scalars().all()]


@router.patch("/categories/{category_id}", response_model=CategoryOut)
async def update_category(category_id: uuid.UUID, payload: CategoryUpdate, db: AsyncSession = Depends(get_db), current_user=Depends(get_operator_or_admin)):
    category = await db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(category, field, value)
    await db.commit()
    await db.refresh(category)
    return CategoryOut.model_validate(category)


@router.post("/tags", response_model=TagOut, status_code=status.HTTP_201_CREATED)
async def create_tag_endpoint(payload: TagCreate, db: AsyncSession = Depends(get_db), current_user=Depends(get_operator_or_admin)):
    tag = await create_tag(db, payload.name)
    return TagOut.model_validate(tag)


@router.get("/tags", response_model=list[TagOut])
async def list_tags(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Tag))
    return [TagOut.model_validate(t) for t in result.scalars().all()]
