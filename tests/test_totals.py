from datetime import date
from decimal import Decimal

from app.models.cart import Cart, CartItem
from app.models.config import GuaranteeConfig, LogisticsConfig, Season
from app.services.order import calculate_totals


def test_totals_calculation_with_guarantee_and_logistics():
    cart = Cart(event_start=date(2024, 1, 1), event_end=date(2024, 1, 3), logistics_hours=2, tolls=0)
    cart.items = [
        CartItem(quantity=2, days=3, price_per_day=Decimal("100"), requires_guarantee=True, units_per_box=12),
    ]
    logistics = LogisticsConfig(base_fee=100, hourly_vehicle_fee=50, default_tolls=20)
    guarantee = GuaranteeConfig(percentage=Decimal("0.15"), apply_tax=True, tax_rate=Decimal("0.21"))
    season = Season(name="Alta", start_date=date(2023, 12, 15), end_date=date(2024, 1, 15), high_season=True, deposit_ratio=Decimal("0.5"))

    totals = calculate_totals(cart, logistics, guarantee, [season])

    assert totals["days"] == 3
    assert totals["subtotal"] == Decimal("600.00")
    assert totals["guarantee_amount"] == Decimal("108.90")  # 600 * 0.15 * 1.21
    assert totals["logistics_cost"] == Decimal("220.00")  # base + hourly*2 + default tolls
    assert totals["total"] == Decimal("928.90")
    assert totals["reservation_required"] == Decimal("464.45")
    assert totals["requires_guarantee"] is True
