import asyncio
from decimal import Decimal
from app.database.connection import init_db, AsyncSessionLocal
from app.database.models import UnitType, PaymentMode
from app.services.inventory import InventoryService
from app.services.billing import BillingService, InsufficientStockError


async def main():
    await init_db()
    async with AsyncSessionLocal() as db:
        print("--- 1. Testing Catalog & Inventory ---")
        product = await InventoryService.add_or_update_product(
            db=db,
            name="Maggi 70g",
            unit=UnitType.PACKET,
            cost_price=Decimal("12.00"),
            mrp=Decimal("14.00"),
            gst_rate=Decimal("12.00")
        )
        print(f"Added product: {product.name} (ID: {product.id})")

        inv = await InventoryService.receive_stock(db, product.id, Decimal("10.00"))
        print(f"Stock added. Available stock: {inv.quantity_available}")

        print("\n--- 2. Testing Multi-turn Billing & Oversell Guard ---")
        bill = await BillingService.get_or_create_draft_bill(db)
        print(f"Created Draft Bill #{bill.id}")

        res = await BillingService.add_or_update_item(db, bill.id, "Maggi", Decimal("3.00"))
        print(f"Added to bill: {res}")

        try:
            print("Attempting to over-sell 15 packets...")
            await BillingService.add_or_update_item(db, bill.id, "Maggi", Decimal("15.00"))
        except InsufficientStockError as e:
            print(f"SUCCESS: Oversell Guard Triggered -> {e}")

        print("\n--- 3. Testing Bill Finalization & Stock Decrement ---")
        finalized_bill = await BillingService.finalize_bill(
            db=db,
            bill_id=bill.id,
            payment_mode=PaymentMode.UPI,
            idempotency_key="TEST_TXN_001"
        )
        print(f"Bill #{finalized_bill.id} Finalized! Total: ₹{finalized_bill.grand_total}")

        inv_after = await InventoryService.receive_stock(db, product.id, Decimal("0.00"))
        print(f"Stock remaining in DB after sale: {inv_after.quantity_available}")

if __name__ == "__main__":
    asyncio.run(main())