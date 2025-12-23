import uuid
from decimal import Decimal
from typing import List

from pydantic import BaseModel, Field

from app.models.catalog import Product


class CategoryBase(BaseModel):
    name: str
    description: str | None = None


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class CategoryOut(CategoryBase):
    id: uuid.UUID

    model_config = {"from_attributes": True}


class TagBase(BaseModel):
    name: str


class TagOut(TagBase):
    id: uuid.UUID

    model_config = {"from_attributes": True}


class TagCreate(TagBase):
    pass


class ProductVariantBase(BaseModel):
    color: str | None = None
    material: str | None = None
    price_override: Decimal | None = None


class ProductVariantCreate(ProductVariantBase):
    pass


class ProductVariantOut(ProductVariantBase):
    id: uuid.UUID

    model_config = {"from_attributes": True}


class ProductBase(BaseModel):
    name: str
    description: str | None = None
    category_id: uuid.UUID | None = None
    base_price: Decimal = Field(..., gt=0)
    requires_guarantee: bool = False
    units_per_box: int = 1
    piece_type: str | None = None
    condition_status: str | None = None
    photo_url: str | None = None
    tag_ids: List[uuid.UUID] = []


class ProductCreate(ProductBase):
    variants: List[ProductVariantCreate] = []


class ProductUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    category_id: uuid.UUID | None = None
    base_price: Decimal | None = None
    requires_guarantee: bool | None = None
    units_per_box: int | None = None
    piece_type: str | None = None
    condition_status: str | None = None
    photo_url: str | None = None
    tag_ids: List[uuid.UUID] | None = None
    variants: List[ProductVariantCreate] | None = None


class ProductOut(ProductBase):
    id: uuid.UUID
    variants: List[ProductVariantOut]

    model_config = {"from_attributes": True}
