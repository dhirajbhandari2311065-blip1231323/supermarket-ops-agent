import asyncio
from app.tools.executor import ToolExecutor


async def main():
    print("--- 1. Adding Product via Tool ---")
    res1 = await ToolExecutor.add_product({
        "name": "Tata Salt 1kg",
        "unit": "packet",
        "cost_price": 20.00,
        "mrp": 28.00,
        "gst_rate": 5.00
    })
    print(res1)

    print("\n--- 2. Receiving Stock via Tool ---")
    res2 = await ToolExecutor.receive_stock({
        "product_name": "Tata Salt",
        "quantity": 50.0
    })
    print(res2)

    print("\n--- 3. Querying Stock via Tool ---")
    res3 = await ToolExecutor.query_stock({
        "product_name": "Tata Salt"
    })
    print(res3)

    print("\n--- 4. Recording Khata Credit via Tool ---")
    res4 = await ToolExecutor.record_khata_credit({
        "customer_name": "Suresh",
        "amount": 250.00,
        "notes": "Milk and grocery credit"
    })
    print(res4)

if __name__ == "__main__":
    asyncio.run(main())