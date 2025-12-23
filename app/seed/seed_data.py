import asyncio
from datetime import date

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.models.catalog import Category, Product, ProductVariant, Tag
from app.models.config import GuaranteeConfig, LogisticsConfig, Season
from app.models.stock import Inventory, Warehouse, StockMovement, StockMovementReason
from app.models.user import User, UserRole
from app.services.auth import create_user

settings = get_settings()


async def get_or_create_tag(session: AsyncSessionLocal, name: str) -> Tag:
    tag = (await session.execute(select(Tag).where(Tag.name == name))).scalars().first()
    if not tag:
        tag = Tag(name=name)
        session.add(tag)
        await session.commit()
        await session.refresh(tag)
    return tag


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        # Users
        if not (await session.execute(select(User).where(User.email == settings.admin_email))).scalars().first():
            await create_user(session, settings.admin_email, settings.admin_password, "Admin", UserRole.admin)
        if not (await session.execute(select(User).where(User.email == settings.operator_email))).scalars().first():
            await create_user(session, settings.operator_email, settings.operator_password, "Operator", UserRole.operator)
        if not (await session.execute(select(User).where(User.email == settings.client_email))).scalars().first():
            await create_user(session, settings.client_email, settings.client_password, "Cliente", UserRole.client)

        # Warehouses
        result_wh = await session.execute(select(Warehouse))
        primary = result_wh.scalars().first()
        if not primary:
            primary = Warehouse(name="Deposito Central", address="Calle Falsa 123")
            session.add(primary)
            await session.commit()
            await session.refresh(primary)

        # Categories and tags
        categories = {
            "Vajilla": "Platos, copas, cubiertos",
            "Mobiliario": "Mesas, sillas, livings",
            "Decoración": "Manteles, centros de mesa y ambientación",
        }
        for name, desc in categories.items():
            if not (await session.execute(select(Category).where(Category.name == name))).scalars().first():
                session.add(Category(name=name, description=desc))
        await session.commit()

        tag_elegante = await get_or_create_tag(session, "elegante")
        tag_rustico = await get_or_create_tag(session, "rústico")
        tag_basico = await get_or_create_tag(session, "básico")
        tag_premium = await get_or_create_tag(session, "premium")

        # Products (idempotente por nombre)
        cat_vajilla = (await session.execute(select(Category).where(Category.name == "Vajilla"))).scalars().first()
        cat_mob = (await session.execute(select(Category).where(Category.name == "Mobiliario"))).scalars().first()
        cat_deco = (await session.execute(select(Category).where(Category.name == "Decoración"))).scalars().first()

        products_payload = [
            {
                "name": "Copa Bordeaux",
                "description": "Copa de vidrio templado",
                "category_id": cat_vajilla.id if cat_vajilla else None,
                "base_price": 120,
                "units_per_box": 12,
                "requires_guarantee": True,
                "piece_type": "copa",
                "condition_status": "A",
                "tags": [tag_elegante],
                "variants": [ProductVariant(color="Transparente", material="Vidrio", price_override=130)],
                "stock": 100,
            },
            {
                "name": "Vaso Old Fashioned",
                "description": "Vaso bajo para whisky o tragos cortos",
                "category_id": cat_vajilla.id if cat_vajilla else None,
                "base_price": 90,
                "units_per_box": 24,
                "requires_guarantee": True,
                "piece_type": "vaso",
                "condition_status": "A",
                "tags": [tag_basico],
                "variants": [],
                "stock": 120,
            },
            {
                "name": "Plato playo porcelana",
                "description": "Plato de porcelana blanca de 26cm",
                "category_id": cat_vajilla.id if cat_vajilla else None,
                "base_price": 110,
                "units_per_box": 12,
                "requires_guarantee": True,
                "piece_type": "plato",
                "condition_status": "A",
                "tags": [tag_elegante],
                "variants": [],
                "stock": 150,
            },
            {
                "name": "Silla Crossback",
                "description": "Silla de madera con terminación natural",
                "category_id": cat_mob.id if cat_mob else None,
                "base_price": 1800,
                "units_per_box": 1,
                "requires_guarantee": True,
                "piece_type": "silla",
                "condition_status": "A",
                "tags": [tag_rustico],
                "variants": [ProductVariant(color="Natural", material="Madera", price_override=None)],
                "stock": 60,
            },
            {
                "name": "Mesa rectangular 1.80m",
                "description": "Mesa de madera para 6-8 personas",
                "category_id": cat_mob.id if cat_mob else None,
                "base_price": 5200,
                "units_per_box": 1,
                "requires_guarantee": True,
                "piece_type": "mesa",
                "condition_status": "A",
                "tags": [tag_rustico],
                "variants": [],
                "stock": 25,
            },
            {
                "name": "Mantel lino blanco",
                "description": "Mantel de lino 2.40m, ideal mesas rectangulares",
                "category_id": cat_deco.id if cat_deco else None,
                "base_price": 700,
                "units_per_box": 1,
                "requires_guarantee": False,
                "piece_type": "mantel",
                "condition_status": "A",
                "tags": [tag_premium],
                "variants": [],
                "stock": 80,
            },
        ]

        for payload in products_payload:
            exists = (await session.execute(select(Product).where(Product.name == payload["name"]))).scalars().first()
            if exists:
                product = exists
            else:
                product = Product(
                    name=payload["name"],
                    description=payload["description"],
                    category_id=payload["category_id"],
                    base_price=payload["base_price"],
                    units_per_box=payload["units_per_box"],
                    requires_guarantee=payload["requires_guarantee"],
                    piece_type=payload["piece_type"],
                    condition_status=payload["condition_status"],
                )
                product.tags.extend(payload["tags"])
                for variant in payload["variants"]:
                    product.variants.append(variant)
                session.add(product)
                await session.commit()
                await session.refresh(product)

            inventory = (await session.execute(select(Inventory).where(Inventory.product_id == product.id))).scalars().first()
            if not inventory:
                inventory = Inventory(product_id=product.id, warehouse_id=primary.id, available=payload["stock"])
                session.add(inventory)
                await session.commit()
                await session.refresh(inventory)

            has_movement = (await session.execute(select(StockMovement).where(StockMovement.inventory_id == inventory.id))).scalars().first()
            if not has_movement:
                movement = StockMovement(
                    inventory_id=inventory.id,
                    quantity_change=inventory.available,
                    reason=StockMovementReason.adjustment,
                    reference="seed",
                )
                session.add(movement)
                await session.commit()

        # Config
        if not (await session.execute(select(LogisticsConfig))).scalars().first():
            session.add(LogisticsConfig(base_fee=2000, hourly_vehicle_fee=1500, default_tolls=0))
        if not (await session.execute(select(GuaranteeConfig))).scalars().first():
            session.add(GuaranteeConfig(percentage=0.15, apply_tax=True, tax_rate=0.21))
        if not (await session.execute(select(Season))).scalars().first():
            session.add(
                Season(
                    name="Temporada Alta",
                    start_date=date(date.today().year, 12, 1),
                    end_date=date(date.today().year + 1, 2, 28),
                    high_season=True,
                    deposit_ratio=0.5,
                )
            )
        await session.commit()


if __name__ == "__main__":
    asyncio.run(seed())
