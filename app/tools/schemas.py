from decimal import Decimal
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from google.genai import types
from app.database.models import UnitType, PaymentMode


# --- Inventory Tool Schemas ---

class AddProductInput(BaseModel):
    name: str = Field(..., description="Name of the product SKU (e.g. 'Aashirvaad Atta 5kg', 'Maggi 70g')")
    unit: UnitType = Field(..., description="Unit type: 'kg', 'g', 'litre', 'ml', 'packet', 'dozen', or 'piece'")
    cost_price: Decimal = Field(..., description="Purchase/cost price per unit in INR")
    mrp: Decimal = Field(..., description="MRP / Selling price per unit in INR")
    gst_rate: Decimal = Field(..., description="GST tax rate percentage (0, 5, 12, or 18)")
    hsn_code: Optional[str] = Field("0000", description="HSN tax classification code")
    reorder_level: Optional[Decimal] = Field(Decimal("10.0"), description="Minimum stock threshold for reorder alerts")


class ReceiveStockInput(BaseModel):
    product_name: str = Field(..., description="Exact or partial name of the product SKU received")
    quantity: Decimal = Field(..., description="Quantity received to add to existing stock")


class QueryStockInput(BaseModel):
    product_name: Optional[str] = Field(None, description="Product name to query stock for. If omitted, lists low stock items.")


# --- Billing Tool Schemas ---

class UpdateBillItemInput(BaseModel):
    bill_id: Optional[int] = Field(None, description="Active draft bill ID. If null, a new draft bill is created.")
    product_name: str = Field(..., description="Product SKU name to add or edit")
    quantity: Decimal = Field(..., description="Quantity to set for this item")


class RemoveBillItemInput(BaseModel):
    bill_id: int = Field(..., description="Active draft bill ID")
    product_name: str = Field(..., description="Product name to remove from the bill")


class FinalizeBillInput(BaseModel):
    bill_id: int = Field(..., description="Active draft bill ID to finalize")
    payment_mode: PaymentMode = Field(..., description="Payment method used: 'cash', 'upi', 'card', or 'khata'")
    customer_name: Optional[str] = Field(None, description="Customer name (required if payment_mode is 'khata')")
    idempotency_key: Optional[str] = Field(None, description="Unique transaction idempotency key to avoid duplicate billing")


# --- Khata Tool Schemas ---

class KhataCreditInput(BaseModel):
    customer_name: str = Field(..., description="Name of the customer receiving goods on credit")
    amount: Decimal = Field(..., description="Credit amount in INR")
    bill_id: Optional[int] = Field(None, description="Associated bill ID if linked to a bill")
    notes: Optional[str] = Field(None, description="Optional notes regarding the credit entry")


class KhataPaymentInput(BaseModel):
    customer_name: str = Field(..., description="Name of the customer making a credit repayment")
    amount: Decimal = Field(..., description="Repayment amount in INR")
    notes: Optional[str] = Field(None, description="Optional notes regarding the payment")


class KhataBalanceInput(BaseModel):
    customer_name: str = Field(..., description="Customer name to look up total net credit balance")


# --- Preference Tool Schemas ---

class SetPreferenceInput(BaseModel):
    key: str = Field(..., description="Preference key (e.g. 'default_payment_mode', 'default_atta')")
    value: str = Field(..., description="Value to assign to the preference key")


# --- Gemini Tool Declarations ---

resolve_product_schema = types.FunctionDeclaration(
    name="resolve_product",
    description="Resolves a user product query to find matching SKUs or detect ambiguity when multiple products match (e.g. 'atta' -> Aashirvaad 5kg vs Loose Atta).",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "query": types.Schema(
                type=types.Type.STRING,
                description="The product name or keyword requested by the owner."
            )
        },
        required=["query"]
    )
)

add_product_schema = types.FunctionDeclaration(
    name="add_product",
    description="Add or update a product in the catalog with name, unit, cost_price, mrp, and gst_rate.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "name": types.Schema(type=types.Type.STRING, description="Product name"),
            "unit": types.Schema(
                type=types.Type.STRING,
                description="Unit type: 'kg', 'g', 'litre', 'ml', 'packet', 'dozen', or 'piece'",
                enum=["kg", "g", "litre", "ml", "packet", "dozen", "piece"]
            ),
            "cost_price": types.Schema(type=types.Type.NUMBER, description="Cost price in INR"),
            "mrp": types.Schema(type=types.Type.NUMBER, description="MRP / Selling price in INR"),
            "gst_rate": types.Schema(type=types.Type.NUMBER, description="GST % slab (0, 5, 12, 18)"),
            "hsn_code": types.Schema(type=types.Type.STRING, description="HSN tax classification code"),
            "reorder_level": types.Schema(type=types.Type.NUMBER, description="Minimum stock threshold for alerts")
        },
        required=["name", "unit", "cost_price", "mrp", "gst_rate"]
    )
)

receive_stock_schema = types.FunctionDeclaration(
    name="receive_stock",
    description="Receive and record new inventory stock for a product.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "product_name": types.Schema(type=types.Type.STRING, description="Name of the product SKU received"),
            "quantity": types.Schema(type=types.Type.NUMBER, description="Quantity received to add to existing stock")
        },
        required=["product_name", "quantity"]
    )
)

query_stock_schema = types.FunctionDeclaration(
    name="query_stock",
    description="Check current stock levels for a product or list low-stock items.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "product_name": types.Schema(type=types.Type.STRING, description="Product name to query stock for")
        }
    )
)

update_bill_item_schema = types.FunctionDeclaration(
    name="update_bill_item",
    description="Add or modify an item quantity in an active draft bill.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "bill_id": types.Schema(type=types.Type.INTEGER, description="Active draft bill ID"),
            "product_name": types.Schema(type=types.Type.STRING, description="Product SKU name to add or update"),
            "quantity": types.Schema(type=types.Type.NUMBER, description="Quantity requested")
        },
        required=["product_name", "quantity"]
    )
)

remove_bill_item_schema = types.FunctionDeclaration(
    name="remove_bill_item",
    description="Remove an item from an active draft bill.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "bill_id": types.Schema(type=types.Type.INTEGER, description="Active draft bill ID"),
            "product_name": types.Schema(type=types.Type.STRING, description="Product name to remove from bill")
        },
        required=["bill_id", "product_name"]
    )
)

finalize_bill_schema = types.FunctionDeclaration(
    name="finalize_bill",
    description="Finalize draft bill and complete sale transaction.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "bill_id": types.Schema(type=types.Type.INTEGER, description="Active draft bill ID to finalize"),
            "payment_mode": types.Schema(
                type=types.Type.STRING,
                description="Payment method used: 'cash', 'upi', 'card', or 'khata'",
                enum=["cash", "upi", "card", "khata"]
            ),
            "customer_name": types.Schema(type=types.Type.STRING, description="Customer name if payment_mode is khata"),
            "idempotency_key": types.Schema(type=types.Type.STRING, description="Unique transaction idempotency key")
        },
        required=["bill_id", "payment_mode"]
    )
)

record_khata_credit_schema = types.FunctionDeclaration(
    name="record_khata_credit",
    description="Record credit purchase for customer on Khata ledger.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "customer_name": types.Schema(type=types.Type.STRING, description="Name of the customer receiving credit"),
            "amount": types.Schema(type=types.Type.NUMBER, description="Credit amount in INR"),
            "bill_id": types.Schema(type=types.Type.INTEGER, description="Associated bill ID if linked"),
            "notes": types.Schema(type=types.Type.STRING, description="Optional credit notes")
        },
        required=["customer_name", "amount"]
    )
)

record_khata_payment_schema = types.FunctionDeclaration(
    name="record_khata_payment",
    description="Record a credit repayment made by a customer.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "customer_name": types.Schema(type=types.Type.STRING, description="Name of the customer paying back"),
            "amount": types.Schema(type=types.Type.NUMBER, description="Repayment amount in INR"),
            "notes": types.Schema(type=types.Type.STRING, description="Optional payment notes")
        },
        required=["customer_name", "amount"]
    )
)

get_khata_balance_schema = types.FunctionDeclaration(
    name="get_khata_balance",
    description="Get net credit balance owed by a customer.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "customer_name": types.Schema(type=types.Type.STRING, description="Customer name to look up balance for")
        },
        required=["customer_name"]
    )
)

set_owner_preference_schema = types.FunctionDeclaration(
    name="set_owner_preference",
    description="Save standing store owner preferences.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "key": types.Schema(type=types.Type.STRING, description="Preference key (e.g. 'default_payment_mode')"),
            "value": types.Schema(type=types.Type.STRING, description="Value to assign to the key")
        },
        required=["key", "value"]
    )
)


# --- Wrap all declarations in types.Tool ---

agent_tools = [
    types.Tool(
        function_declarations=[
            resolve_product_schema,
            add_product_schema,
            receive_stock_schema,
            query_stock_schema,
            update_bill_item_schema,
            remove_bill_item_schema,
            finalize_bill_schema,
            record_khata_credit_schema,
            record_khata_payment_schema,
            get_khata_balance_schema,
            set_owner_preference_schema,
        ]
    )
]