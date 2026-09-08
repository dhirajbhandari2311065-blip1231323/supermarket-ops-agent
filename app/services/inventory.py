import re
from decimal import Decimal
from typing import Optional, List, Dict, Any
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import Product, Inventory, UnitType


class InventoryService:

    @staticmethod
    def normalize_name(name: str) -> str:
        """Trims, lowercases, and removes extra spaces/punctuation for flexible matching."""
        cleaned = re.sub(r'[^a-zA-Z0-9]', '', name)
        return cleaned.lower()

    @classmethod
    async def resolve_product(cls, db: AsyncSession, query: str) -> Dict[str, Any]:
        """
        Resolves a search query to matching products.
        Returns exact match, multiple options for clarification, or empty list.
        """
        normalized_query = cls.normalize_name(query)
        
        # 1. Direct search by string matching on product name
        stmt = select(Product).where(Product.name.ilike(f"%{query}%"))
        result = await db.execute(stmt)
        products = result.scalars().all()

        if not products:
            # Fallback to normalized matching across all catalog items
            all_stmt = select(Product)
            all_res = await db.execute(all_stmt)
            all_products = all_res.scalars().all()
            products = [
                p for p in all_products 
                if normalized_query in cls.normalize_name(p.name) or (hasattr(p, "sku") and p.sku and normalized_query in cls.normalize_name(p.sku))
            ]

        if len(products) == 1:
            prod = products[0]
            return {
                "status": "EXACT_MATCH",
                "product": {
                    "id": prod.id,
                    "sku": getattr(prod, "sku", None),
                    "name": prod.name,
                    "mrp": float(prod.mrp),
                    "cost_price": float(prod.cost_price),
                    "gst_rate": float(prod.gst_rate),
                    "unit": prod.unit.value if hasattr(prod.unit, "value") else str(prod.unit)
                }
            }
        elif len(products) > 1:
            return {
                "status": "AMBIGUOUS",
                "query": query,
                "matches": [
                    {
                        "id": p.id,
                        "name": p.name,
                        "mrp": float(p.mrp),
                        "unit": p.unit.value if hasattr(p.unit, "value") else str(p.unit)
                    } for p in products
                ],
                "message": f"Multiple items found matching '{query}'. Please specify which one."
            }
        else:
            return {
                "status": "NOT_FOUND",
                "query": query,
                "message": f"No product matching '{query}' was found in the inventory catalog."
            }

    @staticmethod
    async def add_or_update_product(
        db: AsyncSession,
        name: str,
        unit: UnitType,
        cost_price: Decimal,
        mrp: Decimal,
        gst_rate: Decimal,
        hsn_code: str = "0000",
        reorder_level: Decimal = Decimal("10.0")
    ) -> Product:
        """Adds a new product catalog entry or updates pricing if it exists."""
        stmt = select(Product).where(Product.name.ilike(name))
        result = await db.execute(stmt)
        product = result.scalar_one_or_none()

        if not product:
            product = Product(
                name=name,
                unit=unit,
                cost_price=cost_price,
                mrp=mrp,
                gst_rate=gst_rate,
                hsn_code=hsn_code,
                reorder_level=reorder_level
            )
            db.add(product)
            await db.flush()  # Assigns product.id

            inventory = Inventory(product_id=product.id, quantity_available=Decimal("0.00"))
            db.add(inventory)
        else:
            product.cost_price = cost_price
            product.mrp = mrp
            product.gst_rate = gst_rate
            product.unit = unit
            if hsn_code != "0000":
                product.hsn_code = hsn_code

        await db.commit()
        await db.refresh(product)
        return product

    @staticmethod
    async def receive_stock(db: AsyncSession, product_id: int, quantity: Decimal) -> Inventory:
        """Increments stock count for a given product."""
        stmt = select(Inventory).where(Inventory.product_id == product_id).with_for_update()
        result = await db.execute(stmt)
        inventory = result.scalar_one_or_none()

        if not inventory:
            raise ValueError(f"No inventory record found for product ID {product_id}")

        inventory.quantity_available += Decimal(str(quantity))
        await db.commit()
        await db.refresh(inventory)
        return inventory

    @staticmethod
    async def get_low_stock_products(db: AsyncSession) -> List[Dict[str, Any]]:
        """Finds items where current stock <= reorder_level."""
        stmt = (
            select(Product, Inventory)
            .join(Inventory, Product.id == Inventory.product_id)
            .where(Inventory.quantity_available <= Product.reorder_level)
        )
        result = await db.execute(stmt)
        low_stock_list = []
        for product, inventory in result:
            low_stock_list.append({
                "product_id": product.id,
                "name": product.name,
                "available": float(inventory.quantity_available),
                "reorder_level": float(product.reorder_level),
                "unit": product.unit.value if hasattr(product.unit, "value") else str(product.unit)
            })
        return low_stock_list