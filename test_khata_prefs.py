import asyncio
from decimal import Decimal
from app.database.connection import init_db, AsyncSessionLocal
from app.services.khata import KhataService
from app.services.preferences import PreferenceService


async def main():
    await init_db()
    async with AsyncSessionLocal() as db:
        print("--- 1. Testing Khata Credit & Payment Ledger ---")
        customer = "Ramesh Kumar"

        # Add ₹500 credit
        await KhataService.add_credit_entry(db, customer, Decimal("500.00"), notes="Grocery shopping credit")
        bal1 = await KhataService.get_customer_balance(db, customer)
        print(f"Added ₹500 credit. {customer} balance: ₹{bal1}")

        # Pay ₹300 repayment
        await KhataService.add_payment_entry(db, customer, Decimal("300.00"), notes="Partial UPI payment")
        bal2 = await KhataService.get_customer_balance(db, customer)
        print(f"Received ₹300 payment. {customer} balance: ₹{bal2}")

        # Fetch ledger history
        history = await KhataService.get_ledger_history(db, customer)
        print(f"Ledger entries for {customer}: {len(history)} items found.")

        print("\n--- 2. Testing Owner Persistent Preferences ---")
        await PreferenceService.set_preference(db, "default_payment_mode", "upi")
        await PreferenceService.set_preference(db, "default_atta", "Aashirvaad Atta 5kg")

        payment_pref = await PreferenceService.get_preference(db, "default_payment_mode")
        atta_pref = await PreferenceService.get_preference(db, "default_atta")

        print(f"Saved Preference -> default_payment_mode: {payment_pref}")
        print(f"Saved Preference -> default_atta: {atta_pref}")

if __name__ == "__main__":
    asyncio.run(main())