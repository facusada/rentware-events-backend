import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.deps import get_db, get_operator_or_admin
from app.models.catalog import Product, ProductVariant
from app.models.stock import Inventory, StockMovement, StockMovementReason, Warehouse
from app.schemas.stock import (
    InventoryOut,
    StockMovementCreate,
    StockMovementOut,
    StockMovementWithMeta,
    WarehouseCreate,
    WarehouseOut,
)

router = APIRouter(prefix="/stock", tags=["stock"])


@router.post("/warehouses", response_model=WarehouseOut, status_code=status.HTTP_201_CREATED)
async def create_warehouse(payload: WarehouseCreate, db: AsyncSession = Depends(get_db), user=Depends(get_operator_or_admin)):
    warehouse = Warehouse(name=payload.name, address=payload.address)
    db.add(warehouse)
    await db.commit()
    await db.refresh(warehouse)
    return WarehouseOut.model_validate(warehouse)


@router.get("/warehouses", response_model=list[WarehouseOut])
async def list_warehouses(db: AsyncSession = Depends(get_db), user=Depends(get_operator_or_admin)):
    result = await db.execute(select(Warehouse))
    return [WarehouseOut.model_validate(w) for w in result.scalars().all()]


@router.get("/", response_model=list[InventoryOut])
async def list_inventory(db: AsyncSession = Depends(get_db), user=Depends(get_operator_or_admin)):
    result = await db.execute(select(Inventory))
    return [InventoryOut.model_validate(i) for i in result.scalars().all()]


@router.post("/inventories", response_model=InventoryOut, status_code=status.HTTP_201_CREATED)
async def create_inventory(
    product_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    available: int = 0,
    variant_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_operator_or_admin),
):
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    if variant_id:
        variant = await db.get(ProductVariant, variant_id)
        if not variant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variant not found")
    inventory = Inventory(product_id=product_id, warehouse_id=warehouse_id, available=available, variant_id=variant_id)
    db.add(inventory)
    await db.commit()
    await db.refresh(inventory)
    return InventoryOut.model_validate(inventory)


@router.post("/movements", response_model=StockMovementOut, status_code=status.HTTP_201_CREATED)
async def create_movement(payload: StockMovementCreate, db: AsyncSession = Depends(get_db), user=Depends(get_operator_or_admin)):
    inventory = await db.get(Inventory, payload.inventory_id)
    if not inventory:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory not found")
    inventory.available += payload.quantity_change
    movement = StockMovement(
        inventory_id=payload.inventory_id,
        quantity_change=payload.quantity_change,
        reason=payload.reason,
        reference=payload.reference,
        amount=payload.amount,
    )
    db.add(movement)
    await db.commit()
    await db.refresh(movement)
    return StockMovementOut.model_validate(movement)


@router.get("/movements", response_model=list[StockMovementWithMeta])
async def list_movements(db: AsyncSession = Depends(get_db), user=Depends(get_operator_or_admin)):
    stmt = (
        select(
            StockMovement.id,
            StockMovement.inventory_id,
            StockMovement.quantity_change,
            StockMovement.reason,
            StockMovement.reference,
            StockMovement.amount,
            StockMovement.created_at,
            Inventory.product_id,
            Inventory.variant_id,
            Inventory.warehouse_id,
            Product.name.label("product_name"),
            Warehouse.name.label("warehouse_name"),
        )
        .join(Inventory, StockMovement.inventory_id == Inventory.id)
        .join(Product, Inventory.product_id == Product.id)
        .join(Warehouse, Inventory.warehouse_id == Warehouse.id)
        .order_by(StockMovement.created_at.desc())
    )
    result = await db.execute(stmt)
    rows = result.all()
    return [
        StockMovementWithMeta(
            id=row.id,
            inventory_id=row.inventory_id,
            product_id=row.product_id,
            product_name=row.product_name,
            variant_id=row.variant_id,
            warehouse_id=row.warehouse_id,
            warehouse_name=row.warehouse_name,
            quantity_change=row.quantity_change,
            reason=row.reason,
            reference=row.reference,
            amount=row.amount,
            created_at=row.created_at,
        )
        for row in rows
    ]
