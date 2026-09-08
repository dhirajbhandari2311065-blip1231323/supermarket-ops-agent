from decimal import Decimal
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import Bill, BillItem, Product, Inventory, BillStatus, PaymentMode
from app.services.gst import calculate_item_gst


class InsufficientStockError(Exception):
    def __init__(self, product_name: str, requested: Decimal, available: Decimal):
        self.product_name = product_name
        self.requested = requested
        self.available = available
        super().__init__(f"Insufficient stock for '{product_name}'. Requested: {requested}, Available: {available}")


class BillingService:

    @staticmethod
    async def get_or_create_draft_bill(db: AsyncSession, bill_id: Optional[int] = None) -> Bill:
        """Retrieves an existing draft bill or initializes a new draft."""
        if bill_id:
            stmt = select(Bill).where(Bill.id == bill_id, Bill.status == BillStatus.DRAFT)
            result = await db.execute(stmt)
            bill = result.scalar_one_or_none()
            if bill:
                return bill

        bill = Bill(status=BillStatus.DRAFT)
        db.add(bill)
        await db.commit()
        await db.refresh(bill)
        return bill

    @staticmethod
    async def add_or_update_item(
        db: AsyncSession,
        bill_id: int,
        product_name: str,
        quantity: Decimal
    ) -> Dict[str, Any]:
        """
        Adds or updates an item in a draft bill.
        Checks stock availability immediately, but DOES NOT decrement stock until finalization.
        """
        # Find Product
        stmt = select(Product).where(Product.name.ilike(f"%{product_name}%"))
        result = await db.execute(stmt)
        product = result.scalar_one_or_none()

        if not product:
            raise ValueError(f"Product '{product_name}' not found in catalog.")

        # Check Inventory for Oversell Guard
        inv_stmt = select(Inventory).where(Inventory.product_id == product.id)
        inv_res = await db.execute(inv_stmt)
        inventory = inv_res.scalar_one_or_none()

        available_stock = inventory.quantity_available if inventory else Decimal("0.00")
        if quantity > available_stock:
            raise InsufficientStockError(
                product_name=product.name,
                requested=quantity,
                available=available_stock
            )

        # Calculate GST and Totals
        tax = calculate_item_gst(product.mrp, quantity, product.gst_rate)

        # Find existing item in bill or create new
        item_stmt = select(BillItem).where(BillItem.bill_id == bill_id, BillItem.product_id == product.id)
        item_res = await db.execute(item_stmt)
        item = item_res.scalar_one_or_none()

        if item:
            item.quantity = quantity
            item.item_subtotal = tax["subtotal"]
            item.cgst_amount = tax["cgst_amount"]
            item.sgst_amount = tax["sgst_amount"]
            item.item_total = tax["grand_total"]
        else:
            item = BillItem(
                bill_id=bill_id,
                product_id=product.id,
                product_name=product.name,
                quantity=quantity,
                unit_price=product.mrp,
                gst_rate=product.gst_rate,
                item_subtotal=tax["subtotal"],
                cgst_amount=tax["cgst_amount"],
                sgst_amount=tax["sgst_amount"],
                item_total=tax["grand_total"]
            )
            db.add(item)

        await db.flush()
        await BillingService._recalculate_bill_totals(db, bill_id)
        await db.commit()

        return {"product": product.name, "quantity": quantity, "item_total": tax["grand_total"]}

    @staticmethod
    async def remove_item(db: AsyncSession, bill_id: int, product_name: str) -> bool:
        """Removes an item from a draft bill."""
        stmt = (
            select(BillItem)
            .join(Product, BillItem.product_id == Product.id)
            .where(BillItem.bill_id == bill_id, Product.name.ilike(f"%{product_name}%"))
        )
        result = await db.execute(stmt)
        item = result.scalar_one_or_none()

        if item:
            await db.delete(item)
            await db.flush()
            await BillingService._recalculate_bill_totals(db, bill_id)
            await db.commit()
            return True
        return False

    @staticmethod
    async def _recalculate_bill_totals(db: AsyncSession, bill_id: int) -> None:
        """Recalculates top-level bill summaries."""
        stmt = select(Bill).where(Bill.id == bill_id)
        result = await db.execute(stmt)
        bill = result.scalar_one_or_none()

        items_stmt = select(BillItem).where(BillItem.bill_id == bill_id)
        items = (await db.execute(items_stmt)).scalars().all()

        subtotal = sum((item.item_subtotal for item in items), Decimal("0.00"))
        cgst = sum((item.cgst_amount for item in items), Decimal("0.00"))
        sgst = sum((item.sgst_amount for item in items), Decimal("0.00"))
        grand_total = sum((item.item_total for item in items), Decimal("0.00"))

        bill.subtotal = subtotal
        bill.cgst_total = cgst
        bill.sgst_total = sgst
        bill.grand_total = grand_total

    @staticmethod
    async def finalize_bill(
        db: AsyncSession,
        bill_id: int,
        payment_mode: PaymentMode,
        customer_name: Optional[str] = None,
        idempotency_key: Optional[str] = None
    ) -> Bill:
        """
        Finalizes a bill atomically:
        1. Checks Idempotency Key (prevents double finalization on Telegram retries)[cite: 1].
        2. Validates all stock again under database locks (`with_for_update`)[cite: 1].
        3. Decrements stock levels atomically[cite: 1].
        4. Updates bill status to FINALIZED[cite: 1].
        """
        # Idempotency Guard
        if idempotency_key:
            idem_stmt = select(Bill).where(Bill.idempotency_key == idempotency_key)
            existing_bill = (await db.execute(idem_stmt)).scalar_one_or_none()
            if existing_bill:
                return existing_bill  # Return previously finalized bill directly

        stmt = select(Bill).where(Bill.id == bill_id, Bill.status == BillStatus.DRAFT)
        bill = (await db.execute(stmt)).scalar_one_or_none()

        if not bill:
            raise ValueError(f"Draft bill #{bill_id} not found or already finalized.")

        items_stmt = select(BillItem).where(BillItem.bill_id == bill_id)
        items = (await db.execute(items_stmt)).scalars().all()

        if not items:
            raise ValueError("Cannot finalize an empty bill.")

        # Check stock and lock inventory rows
        for item in items:
            inv_stmt = select(Inventory).where(Inventory.product_id == item.product_id).with_for_update()
            inventory = (await db.execute(inv_stmt)).scalar_one_or_none()

            if not inventory or inventory.quantity_available < item.quantity:
                raise InsufficientStockError(
                    product_name=item.product_name,
                    requested=item.quantity,
                    available=inventory.quantity_available if inventory else Decimal("0.00")
                )

            # Atomically decrement inventory
            inventory.quantity_available -= item.quantity

        bill.status = BillStatus.FINALIZED
        bill.payment_mode = payment_mode
        bill.customer_name = customer_name
        bill.idempotency_key = idempotency_key
        bill.finalized_at = datetime.utcnow()

        await db.commit()
        await db.refresh(bill)
        return bill