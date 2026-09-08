from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum
from typing import List, Optional
from sqlalchemy import (
    String,
    Numeric,
    Integer,
    ForeignKey,
    DateTime,
    Enum,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class UnitType(str, PyEnum):
    KG = "kg"
    GRAM = "g"
    LITRE = "litre"
    ML = "ml"
    PACKET = "packet"
    DOZEN = "dozen"
    PIECE = "piece"


class BillStatus(str, PyEnum):
    DRAFT = "draft"
    FINALIZED = "finalized"
    CANCELLED = "cancelled"


class PaymentMode(str, PyEnum):
    CASH = "cash"
    UPI = "upi"
    CARD = "card"
    KHATA = "khata"


class LedgerType(str, PyEnum):
    CREDIT = "credit"      # Store gave goods on credit (increases customer debt)
    PAYMENT = "payment"    # Customer paid off debt (decreases customer debt)


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    hsn_code: Mapped[str] = mapped_column(String(20), nullable=False, default="0000")
    unit: Mapped[UnitType] = mapped_column(Enum(UnitType), nullable=False)
    cost_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    mrp: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    gst_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0.0) # e.g. 0.00, 5.00, 12.00, 18.00
    reorder_level: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=10.0)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    inventory: Mapped["Inventory"] = relationship("Inventory", back_populates="product", uselist=False, cascade="all, delete-orphan")


class Inventory(Base):
    __tablename__ = "inventory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False, unique=True)
    quantity_available: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0.00)
    
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    product: Mapped["Product"] = relationship("Product", back_populates="inventory")


class Bill(Base):
    __tablename__ = "bills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    status: Mapped[BillStatus] = mapped_column(Enum(BillStatus), default=BillStatus.DRAFT, nullable=False)
    payment_mode: Mapped[Optional[PaymentMode]] = mapped_column(Enum(PaymentMode), nullable=True)
    customer_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0.00, nullable=False)
    cgst_total: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0.00, nullable=False)
    sgst_total: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0.00, nullable=False)
    grand_total: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0.00, nullable=False)
    
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    finalized_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    items: Mapped[List["BillItem"]] = relationship("BillItem", back_populates="bill", cascade="all, delete-orphan")


class BillItem(Base):
    __tablename__ = "bill_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bill_id: Mapped[int] = mapped_column(ForeignKey("bills.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    gst_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    
    item_subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    cgst_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    sgst_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    item_total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    bill: Mapped["Bill"] = relationship("Bill", back_populates="items")


class KhataLedger(Base):
    __tablename__ = "khata_ledger"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    entry_type: Mapped[LedgerType] = mapped_column(Enum(LedgerType), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    bill_id: Mapped[Optional[int]] = mapped_column(ForeignKey("bills.id"), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class OwnerPreference(Base):
    __tablename__ = "owner_preferences"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())