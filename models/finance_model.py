# models/finance_model.py
"""
Finance management models - provides flexible cash ledger system.

Architecture:
  - Uses dynamic enum system for transaction nature and category
  - CashBook: Named ledger owned by a doctor (independent balances)
  - CashBookCustomField: Extensible schema for per-book custom fields
  - FinanceTransaction: Single transaction with running balance snapshot
  - TransactionCustomFieldValue: Per-transaction custom field values (EAV pattern)
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List

import sqlalchemy as sa
from sqlmodel import SQLModel, Field, Relationship
from pydantic import field_serializer


# ============================================================================
# BASE MODELS (for API schemas)
# ============================================================================

class CashBookBase(SQLModel):
    """Base cash book model"""
    name: str = Field(max_length=150)
    description: Optional[str] = Field(default=None, max_length=255)
    is_active: bool = Field(default=True)


class CashBookCustomFieldBase(SQLModel):
    """Base custom field definition"""
    field_key: str = Field(max_length=100)
    field_label: str = Field(max_length=100)
    field_type: str = Field(max_length=20, default="text")  # text | number | date | boolean
    is_required: bool = Field(default=False)
    display_order: int = Field(default=0)
    is_active: bool = Field(default=True)


class FinanceTransactionBase(SQLModel):
    """Base transaction model"""
    transaction_date: date
    amount: Decimal = Field(max_digits=12, decimal_places=2)
    remarks: Optional[str] = Field(default=None, max_length=500)
    is_deleted: bool = Field(default=False)


class TransactionCustomFieldValueBase(SQLModel):
    """Base custom field value"""
    value: Optional[str] = Field(default=None)


# ============================================================================
# DATABASE MODELS (table=True)
# ============================================================================

class CashBook(CashBookBase, table=True):
    """DATABASE MODEL - named ledger owned by a doctor"""
    __tablename__ = "finance_cash_book"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    # Owner
    doctor_id: uuid.UUID = Field(
        foreign_key="user.id",
        nullable=False,
        index=True
    )

    # Audit
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)

    # Relationships
    doctor: Optional["User"] = Relationship(back_populates="cash_books")
    transactions: List["FinanceTransaction"] = Relationship(back_populates="cash_book")
    custom_fields: List["CashBookCustomField"] = Relationship(back_populates="cash_book")


class CashBookCustomField(CashBookCustomFieldBase, table=True):
    """DATABASE MODEL - schema for custom fields per cash book"""
    __tablename__ = "finance_cash_book_custom_field"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    # FK → Cash Book
    cash_book_id: uuid.UUID = Field(
        foreign_key="finance_cash_book.id",
        nullable=False,
        index=True
    )

    # Audit
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)

    # Relationships
    cash_book: Optional["CashBook"] = Relationship(back_populates="custom_fields")
    values: List["TransactionCustomFieldValue"] = Relationship(back_populates="field_definition")

    __table_args__ = (
        sa.UniqueConstraint(
            "cash_book_id",
            "field_key",
            name="uq_cash_book_custom_field_key"
        ),
        sa.Index('idx_cash_book_custom_field_display_order', 'cash_book_id', 'display_order'),
    )


class FinanceTransaction(FinanceTransactionBase, table=True):
    """
    DATABASE MODEL - single transaction with running balance snapshot.
    
    Note: nature_code and category_code are string enums validated against
    the dynamic enum system (TransactionNature, TransactionCategory enum types).
    """
    __tablename__ = "finance_transaction"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    # Core
    running_balance: Decimal = Field(max_digits=12, decimal_places=2)

    # Soft Delete
    deleted_at: Optional[datetime] = Field(default=None)
    deleted_by: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="user.id"
    )

    # Foreign Keys
    cash_book_id: uuid.UUID = Field(
        foreign_key="finance_cash_book.id",
        nullable=False,
        index=True
    )

    # Enum references (stored as strings, validated against dynamic enums)
    nature_code: str = Field(
        max_length=50,
        nullable=False,
        description="CASH_IN or CASH_OUT (from TransactionNature enum type)"
    )

    category_code: str = Field(
        max_length=100,
        nullable=False,
        description="Transaction category code (from TransactionCategory enum type)"
    )

    doctor_id: uuid.UUID = Field(
        foreign_key="user.id",
        nullable=False,
        index=True
    )

    # Relationships
    cash_book: Optional["CashBook"] = Relationship(back_populates="transactions")
    doctor: Optional["User"] = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "FinanceTransaction.doctor_id",
            "viewonly": True
        }
    )
    custom_field_values: List["TransactionCustomFieldValue"] = Relationship(back_populates="transaction")

    # Audit
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)

    __table_args__ = (
        sa.Index('idx_transaction_date', 'cash_book_id', 'transaction_date'),
        sa.Index('idx_transaction_deleted', 'is_deleted'),
        sa.Index('idx_transaction_nature_code', 'nature_code'),
        sa.Index('idx_transaction_category_code', 'category_code'),
    )


class TransactionCustomFieldValue(TransactionCustomFieldValueBase, table=True):
    """DATABASE MODEL - per-transaction custom field values (EAV pattern)"""
    __tablename__ = "finance_transaction_custom_field_value"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    # Foreign Keys
    transaction_id: uuid.UUID = Field(
        foreign_key="finance_transaction.id",
        nullable=False,
        index=True
    )

    field_id: uuid.UUID = Field(
        foreign_key="finance_cash_book_custom_field.id",
        nullable=False,
        index=True
    )

    # Audit
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)

    # Relationships
    transaction: Optional["FinanceTransaction"] = Relationship(back_populates="custom_field_values")
    field_definition: Optional["CashBookCustomField"] = Relationship(back_populates="values")

    __table_args__ = (
        sa.UniqueConstraint(
            "transaction_id",
            "field_id",
            name="uq_transaction_custom_field_value"
        ),
    )


# ============================================================================
# API RESPONSE MODELS
# ============================================================================

class CashBookCustomFieldPublic(CashBookCustomFieldBase):
    """Public custom field definition response"""
    id: uuid.UUID
    cash_book_id: uuid.UUID


class CashBookPublic(CashBookBase):
    """Public cash book response"""
    id: uuid.UUID
    doctor_id: uuid.UUID
    created_at: datetime
    updated_at: Optional[datetime]


class FinanceTransactionPublic(SQLModel):
    """Public transaction response"""
    id: uuid.UUID
    cash_book_id: uuid.UUID
    doctor_id: uuid.UUID
    transaction_date: date
    amount: Decimal
    remarks: Optional[str]
    running_balance: Decimal
    nature_code: str
    category_code: str
    is_deleted: bool
    created_at: datetime
    updated_at: Optional[datetime]

    @field_serializer('amount', 'running_balance')
    def serialize_decimal(self, value: Decimal, _info) -> Decimal:
        """Serialize Decimal fields to 2 decimal places"""
        if value is None:
            return None
        return Decimal(str(round(float(value), 2)))


class CashBooksPublic(SQLModel):
    """Response for list of cash books"""
    data: List[CashBookPublic]
    count: int


class TransactionsPublic(SQLModel):
    """Response for list of transactions"""
    data: List[FinanceTransactionPublic]
    count: int


# ============================================================================
# CREATE/UPDATE MODELS
# ============================================================================

class CashBookCreate(SQLModel):
    """Schema for creating cash book"""
    name: str = Field(max_length=150)
    description: Optional[str] = Field(default=None, max_length=255)


class CashBookUpdate(SQLModel):
    """Schema for updating cash book"""
    name: Optional[str] = Field(default=None, max_length=150)
    description: Optional[str] = Field(default=None, max_length=255)
    is_active: Optional[bool] = None


class CashBookCustomFieldCreate(SQLModel):
    """Schema for creating custom field"""
    field_key: str = Field(max_length=100)
    field_label: str = Field(max_length=100)
    field_type: str = Field(max_length=20, default="text")
    is_required: bool = Field(default=False)
    display_order: int = Field(default=0)


class CashBookCustomFieldUpdate(SQLModel):
    """Schema for updating custom field"""
    field_label: Optional[str] = Field(default=None, max_length=100)
    field_type: Optional[str] = Field(default=None, max_length=20)
    is_required: Optional[bool] = None
    display_order: Optional[int] = None


class FinanceTransactionCreate(SQLModel):
    """Schema for creating transaction"""
    cash_book_id: uuid.UUID
    nature_code: str = Field(max_length=50, description="CASH_IN or CASH_OUT - validated against TransactionNature enum")
    category_code: str = Field(max_length=100, description="Category code - validated against TransactionCategory enum")
    amount: Decimal = Field(gt=0)
    transaction_date: date
    remarks: Optional[str] = Field(default=None, max_length=500)
    custom_field_values: Optional[dict] = None

    @field_serializer('amount')
    def serialize_amount(self, value: Decimal, _info) -> Decimal:
        """Serialize amount to 2 decimal places"""
        if value is None:
            return None
        return Decimal(str(round(float(value), 2)))


class FinanceTransactionUpdate(SQLModel):
    """Schema for updating transaction"""
    amount: Optional[Decimal] = Field(default=None, gt=0)
    transaction_date: Optional[date] = None
    nature_code: Optional[str] = Field(default=None, max_length=50)
    category_code: Optional[str] = Field(default=None, max_length=100)

    @field_serializer('amount')
    def serialize_amount(self, value: Decimal, _info) -> Decimal:
        """Serialize amount to 2 decimal places"""
        if value is None:
            return None
        return Decimal(str(round(float(value), 2)))


class CashBookSummaryPublic(SQLModel):
    """Cash book financial summary response"""
    cash_book_id: uuid.UUID
    name: str
    total_cash_in: Decimal
    total_cash_out: Decimal
    net_balance: Decimal
    current_balance: Decimal
    transaction_count: int

    @field_serializer('total_cash_in', 'total_cash_out', 'net_balance', 'current_balance')
    def serialize_decimal(self, value: Decimal, _info) -> Decimal:
        """Serialize Decimal fields to 2 decimal places"""
        if value is None:
            return None
        return Decimal(str(round(float(value), 2)))


class DoctorFinanceSummaryPublic(SQLModel):
    """Doctor aggregate financial summary response"""
    total_cash_in: Decimal
    total_cash_out: Decimal
    net_balance: Decimal
    total_current_balance: Decimal
    transaction_count: int
    books: List[CashBookSummaryPublic]

    @field_serializer('total_cash_in', 'total_cash_out', 'net_balance', 'total_current_balance')
    def serialize_decimal(self, value: Decimal, _info) -> Decimal:
        """Serialize Decimal fields to 2 decimal places"""
        if value is None:
            return None
        return Decimal(str(round(float(value), 2)))
