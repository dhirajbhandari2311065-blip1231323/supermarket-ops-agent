from decimal import Decimal
from typing import Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Product, Inventory
from app.services.inventory import InventoryService
from app.services.billing import BillingService, InsufficientStockError
from app.services.khata import KhataService
from app.services.preferences import PreferenceService
from app.tools.schemas import (
    AddProductInput, ReceiveStockInput, QueryStockInput,
    UpdateBillItemInput, RemoveBillItemInput, FinalizeBillInput,
    KhataCreditInput, KhataPaymentInput, KhataBalanceInput,
    SetPreferenceInput
)


class ToolExecutor:

    @classmethod
    async def execute_tool(cls, db: AsyncSession, chat_id: int, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatches model tool calls to underlying domain services."""
        if tool_name == "resolve_product":
            return await InventoryService.resolve_product(
                db,
                query=args.get("query")
            )
        elif tool_name == "add_product":
            return await cls.add_product(db, chat_id, args)
        elif tool_name == "receive_stock":
            return await cls.receive_stock(db, chat_id, args)
        elif tool_name == "query_stock":
            return await cls.query_stock(db, chat_id, args)
        elif tool_name == "update_bill_item":
            return await cls.update_bill_item(db, chat_id, args)
        elif tool_name == "remove_bill_item":
            return await cls.remove_bill_item(db, chat_id, args)
        elif tool_name == "finalize_bill":
            return await cls.finalize_bill(db, chat_id, args)
        elif tool_name == "record_khata_credit":
            return await cls.record_khata_credit(db, chat_id, args)
        elif tool_name == "record_khata_payment":
            return await cls.record_khata_payment(db, chat_id, args)
        elif tool_name == "get_khata_balance":
            return await cls.get_khata_balance(db, chat_id, args)
        elif tool_name == "set_owner_preference":
            return await cls.set_owner_preference(db, chat_id, args)
        else:
            return {
                "status": "error",
                "error_code": "UNKNOWN_TOOL",
                "message": f"Tool '{tool_name}' is not registered."
            }

    @staticmethod
    async def resolve_product(db: AsyncSession, chat_id: int, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        return await InventoryService.resolve_product(
            db,
            query=kwargs.get("query")
        )

    @staticmethod
    async def add_product(db: AsyncSession, chat_id: int, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        data = AddProductInput(**kwargs)
        product = await InventoryService.add_or_update_product(
            db=db,
            name=data.name,
            unit=data.unit,
            cost_price=data.cost_price,
            mrp=data.mrp,
            gst_rate=data.gst_rate,
            hsn_code=data.hsn_code or "0000",
            reorder_level=data.reorder_level or Decimal("10.0")
        )
        return {
            "status": "success",
            "message": f"Product '{product.name}' added/updated successfully.",
            "product_id": product.id,
            "mrp": float(product.mrp),
            "gst_rate": float(product.gst_rate)
        }

    @staticmethod
    async def receive_stock(db: AsyncSession, chat_id: int, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        data = ReceiveStockInput(**kwargs)
        stmt = select(Product).where(Product.name.ilike(f"%{data.product_name}%"))
        product = (await db.execute(stmt)).scalar_one_or_none()
        if not product:
            return {
                "status": "error",
                "error_code": "PRODUCT_NOT_FOUND",
                "message": f"Product matching '{data.product_name}' was not found in catalog."
            }

        inventory = await InventoryService.receive_stock(db, product.id, data.quantity)
        return {
            "status": "success",
            "product_name": product.name,
            "added_quantity": float(data.quantity),
            "total_available": float(inventory.quantity_available)
        }

    @staticmethod
    async def query_stock(db: AsyncSession, chat_id: int, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        data = QueryStockInput(**kwargs)
        if data.product_name:
            stmt = select(Product, Inventory).join(Inventory, Product.id == Inventory.product_id).where(Product.name.ilike(f"%{data.product_name}%"))
            results = (await db.execute(stmt)).all()
            if not results:
                return {"status": "error", "error_code": "PRODUCT_NOT_FOUND", "message": f"No product found matching '{data.product_name}'"}
            
            items = [
                {"product": p.name, "available": float(i.quantity_available), "unit": p.unit.value, "mrp": float(p.mrp)}
                for p, i in results
            ]
            return {"status": "success", "stock_data": items}
        else:
            low_stock = await InventoryService.get_low_stock_products(db)
            return {
                "status": "success",
                "low_stock_items": [
                    {"product": item["name"], "available": float(item["available"]), "reorder_level": float(item["reorder_level"])}
                    for item in low_stock
                ]
            }

    @staticmethod
    async def update_bill_item(db: AsyncSession, chat_id: int, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        data = UpdateBillItemInput(**kwargs)
        bill = await BillingService.get_or_create_draft_bill(db, data.bill_id)
        try:
            result = await BillingService.add_or_update_item(
                db=db,
                bill_id=bill.id,
                product_name=data.product_name,
                quantity=data.quantity
            )
            return {
                "status": "success",
                "bill_id": bill.id,
                "updated_item": result,
                "current_bill_subtotal": float(bill.subtotal),
                "current_bill_total": float(bill.grand_total)
            }
        except InsufficientStockError as e:
            return {
                "status": "error",
                "error_code": "INSUFFICIENT_STOCK",
                "product": e.product_name,
                "requested": float(e.requested),
                "available": float(e.available),
                "message": f"Cannot add {e.requested} units of {e.product_name}. Only {e.available} available in stock."
            }
        except ValueError as e:
            return {"status": "error", "error_code": "INVALID_PRODUCT", "message": str(e)}

    @staticmethod
    async def remove_bill_item(db: AsyncSession, chat_id: int, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        data = RemoveBillItemInput(**kwargs)
        removed = await BillingService.remove_item(db, data.bill_id, data.product_name)
        if removed:
            return {"status": "success", "bill_id": data.bill_id, "message": f"Removed '{data.product_name}' from bill #{data.bill_id}"}
        return {"status": "error", "message": f"Item '{data.product_name}' not found in bill #{data.bill_id}"}

    @staticmethod
    async def finalize_bill(db: AsyncSession, chat_id: int, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        data = FinalizeBillInput(**kwargs)
        try:
            bill = await BillingService.finalize_bill(
                db=db,
                bill_id=data.bill_id,
                payment_mode=data.payment_mode,
                customer_name=data.customer_name,
                idempotency_key=data.idempotency_key
            )
            
            # If paid via Khata, record Khata ledger entry automatically
            if data.payment_mode == "khata" and data.customer_name:
                await KhataService.add_credit_entry(
                    db=db,
                    customer_name=data.customer_name,
                    amount=bill.grand_total,
                    bill_id=bill.id,
                    notes=f"Bill #{bill.id} purchase on credit"
                )

            return {
                "status": "success",
                "bill_id": bill.id,
                "payment_mode": bill.payment_mode.value,
                "subtotal": float(bill.subtotal),
                "cgst": float(bill.cgst_total),
                "sgst": float(bill.sgst_total),
                "grand_total": float(bill.grand_total),
                "message": f"Bill #{bill.id} finalized successfully!"
            }
        except InsufficientStockError as e:
            return {
                "status": "error",
                "error_code": "INSUFFICIENT_STOCK",
                "product": e.product_name,
                "requested": float(e.requested),
                "available": float(e.available),
                "message": f"Finalization failed: Insufficient stock for {e.product_name}."
            }
        except ValueError as e:
            return {"status": "error", "error_code": "FINALIZATION_FAILED", "message": str(e)}

    @staticmethod
    async def record_khata_credit(db: AsyncSession, chat_id: int, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        data = KhataCreditInput(**kwargs)
        entry = await KhataService.add_credit_entry(
            db=db, customer_name=data.customer_name, amount=data.amount, bill_id=data.bill_id, notes=data.notes
        )
        balance = await KhataService.get_customer_balance(db, data.customer_name)
        return {
            "status": "success",
            "customer": entry.customer_name,
            "added_credit": float(entry.amount),
            "total_outstanding_balance": float(balance)
        }

    @staticmethod
    async def record_khata_payment(db: AsyncSession, chat_id: int, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        data = KhataPaymentInput(**kwargs)
        entry = await KhataService.add_payment_entry(
            db=db, customer_name=data.customer_name, amount=data.amount, notes=data.notes
        )
        balance = await KhataService.get_customer_balance(db, data.customer_name)
        return {
            "status": "success",
            "customer": entry.customer_name,
            "payment_received": float(entry.amount),
            "total_outstanding_balance": float(balance)
        }

    @staticmethod
    async def get_khata_balance(db: AsyncSession, chat_id: int, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        data = KhataBalanceInput(**kwargs)
        balance = await KhataService.get_customer_balance(db, data.customer_name)
        history = await KhataService.get_ledger_history(db, data.customer_name)
        return {
            "status": "success",
            "customer": data.customer_name,
            "outstanding_balance": float(balance),
            "transaction_count": len(history)
        }

    @staticmethod
    async def set_owner_preference(db: AsyncSession, chat_id: int, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        data = SetPreferenceInput(**kwargs)
        pref = await PreferenceService.set_preference(db, data.key, data.value)
        return {
            "status": "success",
            "key": pref.key,
            "value": pref.value,
            "message": f"Owner preference '{pref.key}' set to '{pref.value}'."
        }