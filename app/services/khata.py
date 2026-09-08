from decimal import Decimal
from typing import Dict, Any, List, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import KhataLedger, LedgerType


class KhataService:

    @staticmethod
    async def add_credit_entry(
        db: AsyncSession,
        customer_name: str,
        amount: Decimal,
        bill_id: Optional[int] = None,
        notes: Optional[str] = None
    ) -> KhataLedger:
        """Records goods bought on credit (increases debt)."""
        entry = KhataLedger(
            customer_name=customer_name.strip().title(),
            entry_type=LedgerType.CREDIT,
            amount=Decimal(str(amount)),
            bill_id=bill_id,
            notes=notes or "Purchased on credit"
        )
        db.add(entry)
        await db.commit()
        await db.refresh(entry)
        return entry

    @staticmethod
    async def add_payment_entry(
        db: AsyncSession,
        customer_name: str,
        amount: Decimal,
        notes: Optional[str] = None
    ) -> KhataLedger:
        """Records debt repayment by customer (decreases debt)."""
        entry = KhataLedger(
            customer_name=customer_name.strip().title(),
            entry_type=LedgerType.PAYMENT,
            amount=Decimal(str(amount)),
            notes=notes or "Credit balance settlement"
        )
        db.add(entry)
        await db.commit()
        await db.refresh(entry)
        return entry

    @staticmethod
    async def get_customer_balance(db: AsyncSession, customer_name: str) -> Decimal:
        """Calculates current net balance owed by customer."""
        customer = customer_name.strip().title()

        # Total Credits (Debt added)
        credit_stmt = (
            select(func.coalesce(func.sum(KhataLedger.amount), Decimal("0.00")))
            .where(KhataLedger.customer_name == customer, KhataLedger.entry_type == LedgerType.CREDIT)
        )
        credit_total = (await db.execute(credit_stmt)).scalar() or Decimal("0.00")

        # Total Payments (Debt settled)
        payment_stmt = (
            select(func.coalesce(func.sum(KhataLedger.amount), Decimal("0.00")))
            .where(KhataLedger.customer_name == customer, KhataLedger.entry_type == LedgerType.PAYMENT)
        )
        payment_total = (await db.execute(payment_stmt)).scalar() or Decimal("0.00")

        return credit_total - payment_total

    @staticmethod
    async def get_ledger_history(db: AsyncSession, customer_name: str) -> List[Dict[str, Any]]:
        """Retrieves transactional history for a customer."""
        customer = customer_name.strip().title()
        stmt = (
            select(KhataLedger)
            .where(KhataLedger.customer_name == customer)
            .order_by(KhataLedger.created_at.desc())
        )
        entries = (await db.execute(stmt)).scalars().all()
        return [
            {
                "id": e.id,
                "type": e.entry_type.value,
                "amount": e.amount,
                "notes": e.notes,
                "date": e.created_at.strftime("%Y-%m-%d %H:%M")
            }
            for e in entries
        ]