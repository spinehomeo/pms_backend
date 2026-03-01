# routes/finance.py
"""
Finance management API endpoints - cash ledger system for doctors.
Uses the unified dynamic enum system for transaction nature and category.

Architecture:
- Doctor-owned cash books (independent ledgers)
- Extensible custom fields per book
- Flexible transaction recording using dynamic enum validation
- Running balance tracking
- Financial summaries and reports
"""

import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Path
from sqlmodel import Session, select, desc, asc

from api.deps import CurrentUser, SessionDep
from models.users_model import User
from models.finance_model import (
    # Database models
    CashBook,
    CashBookCustomField,
    FinanceTransaction,
    TransactionCustomFieldValue,
    # API schemas
    CashBookPublic,
    CashBooksPublic,
    CashBookCustomFieldPublic,
    FinanceTransactionPublic,
    TransactionsPublic,
    CashBookSummaryPublic,
    DoctorFinanceSummaryPublic,
    # Create/Update schemas
    CashBookCreate,
    CashBookUpdate,
    CashBookCustomFieldCreate,
    CashBookCustomFieldUpdate,
    FinanceTransactionCreate,
    FinanceTransactionUpdate,
)
from models.login_model import Message
from utils.enum_service import EnumService

router = APIRouter(prefix="/finance", tags=["💰 Finance"])


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _get_last_balance(session: Session, cash_book_id: uuid.UUID) -> Decimal:
    """Internal - get last non-deleted transaction balance in a cash book"""
    statement = (
        select(FinanceTransaction)
        .where(FinanceTransaction.cash_book_id == cash_book_id)
        .where(FinanceTransaction.is_deleted == False)
        .order_by(
            desc(FinanceTransaction.transaction_date),
            desc(FinanceTransaction.created_at),
        )
        .limit(1)
    )

    result = session.exec(statement).first()
    return result.running_balance if result else Decimal("0.00")


def _recalculate_running_balances(session: Session, cash_book_id: uuid.UUID) -> int:
    """Internal - recalculate all running balances in a cash book"""
    transactions = session.exec(
        select(FinanceTransaction)
        .where(FinanceTransaction.cash_book_id == cash_book_id)
        .where(FinanceTransaction.is_deleted == False)
        .order_by(
            asc(FinanceTransaction.transaction_date),
            asc(FinanceTransaction.created_at),
        )
    ).all()

    if not transactions:
        return 0

    running = Decimal("0.00")
    count = 0
    from datetime import datetime

    for txn in transactions:
        if txn.nature_code == "CASH_IN":
            running += txn.amount
        elif txn.nature_code == "CASH_OUT":
            running -= txn.amount

        # Round to 2 decimal places
        txn.running_balance = Decimal(str(round(float(running), 2)))
        txn.updated_at = datetime.utcnow()
        session.add(txn)
        count += 1

    session.commit()
    return count


# ============================================================================
# CASH BOOK - CRUD
# ============================================================================

@router.post("/cash-books", response_model=CashBookPublic)
def create_cash_book(
    payload: CashBookCreate,
    session: SessionDep,
    current_user: CurrentUser,
) -> CashBook:
    """
    Create a new named cash book for the current doctor.

    A cash book is an independent ledger with its own running balance.
    Doctors can maintain multiple books (e.g., Medicine, Equipment, General).

    Args:
        name: Display name for the ledger (e.g., "Medicine Book")
        description: Optional description of what this book tracks

    Returns:
        The created cash book with ID

    Raises:
        400: Doctor must be an active user
        401: User must be authenticated
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can create cash books")

    cash_book = CashBook(
        doctor_id=current_user.id,
        name=payload.name,
        description=payload.description,
    )

    session.add(cash_book)
    session.commit()
    session.refresh(cash_book)

    return cash_book


@router.get("/cash-books", response_model=CashBooksPublic)
def list_cash_books(
    session: SessionDep,
    current_user: CurrentUser,
    active_only: bool = Query(True, description="Only return active books"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> CashBooksPublic:
    """
    List all cash books owned by the current doctor.

    Args:
        active_only: If True, only returns active books (default: True)
        skip: Number of records to skip (pagination)
        limit: Maximum records to return (pagination)

    Returns:
        List of cash books with total count
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can list cash books")

    statement = select(CashBook).where(CashBook.doctor_id == current_user.id)

    if active_only:
        statement = statement.where(CashBook.is_active == True)

    statement = statement.order_by(asc(CashBook.name)).offset(skip).limit(limit)

    books = session.exec(statement).all()
    count = session.exec(
        select(CashBook).where(CashBook.doctor_id == current_user.id)
    ).all()

    return CashBooksPublic(data=books, count=len(count))


@router.get("/cash-books/{cash_book_id}", response_model=CashBookPublic)
def get_cash_book(
    session: SessionDep,
    current_user: CurrentUser,
    cash_book_id: uuid.UUID = Path(...),
) -> CashBook:
    """
    Retrieve a single cash book by ID.

    Args:
        cash_book_id: UUID of the cash book

    Returns:
        The cash book details

    Raises:
        404: Cash book not found
        403: Cash book does not belong to current user
    """
    cash_book = session.get(CashBook, cash_book_id)

    if not cash_book:
        raise HTTPException(status_code=404, detail="Cash book not found")

    if cash_book.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot access this cash book")

    return cash_book


@router.patch("/cash-books/{cash_book_id}", response_model=CashBookPublic)
def update_cash_book(
    payload: CashBookUpdate,
    session: SessionDep,
    current_user: CurrentUser,
    cash_book_id: uuid.UUID = Path(...),
) -> CashBook:
    """
    Update a cash book's name, description, or active status.

    Args:
        cash_book_id: UUID of the cash book
        name: Optional new name
        description: Optional new description
        is_active: Optional active status

    Returns:
        Updated cash book

    Raises:
        404: Cash book not found
        403: Cash book does not belong to current user
    """
    cash_book = session.get(CashBook, cash_book_id)

    if not cash_book:
        raise HTTPException(status_code=404, detail="Cash book not found")

    if cash_book.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot access this cash book")

    if payload.name is not None:
        cash_book.name = payload.name

    if payload.description is not None:
        cash_book.description = payload.description

    if payload.is_active is not None:
        cash_book.is_active = payload.is_active

    from datetime import datetime
    cash_book.updated_at = datetime.utcnow()

    session.add(cash_book)
    session.commit()
    session.refresh(cash_book)

    return cash_book


@router.delete("/cash-books/{cash_book_id}", response_model=Message)
def delete_cash_book(
    session: SessionDep,
    current_user: CurrentUser,
    cash_book_id: uuid.UUID = Path(...),
) -> Message:
    """
    Hard-delete a cash book.

    ⚠️ Deletes all associated transactions.
    Prefer deactivating (is_active=False) for audit safety.

    Args:
        cash_book_id: UUID of the cash book to delete

    Returns:
        Success message

    Raises:
        404: Cash book not found
        403: Cash book does not belong to current user
    """
    cash_book = session.get(CashBook, cash_book_id)

    if not cash_book:
        raise HTTPException(status_code=404, detail="Cash book not found")

    if cash_book.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot access this cash book")

    # Delete custom fields and their values
    custom_fields = session.exec(
        select(CashBookCustomField).where(CashBookCustomField.cash_book_id == cash_book_id)
    ).all()

    for field in custom_fields:
        session.delete(field)

    # Delete transactions
    transactions = session.exec(
        select(FinanceTransaction).where(FinanceTransaction.cash_book_id == cash_book_id)
    ).all()

    for txn in transactions:
        session.delete(txn)

    session.delete(cash_book)
    session.commit()

    return Message(message="Cash book deleted successfully")


# ============================================================================
# CUSTOM FIELDS - per Cash Book
# ============================================================================

@router.post("/cash-books/{cash_book_id}/custom-fields", response_model=CashBookCustomFieldPublic)
def add_custom_field(
    payload: CashBookCustomFieldCreate,
    session: SessionDep,
    current_user: CurrentUser,
    cash_book_id: uuid.UUID = Path(...),
) -> CashBookCustomField:
    """
    Add a custom field definition to a cash book.

    Custom fields allow capturing additional data per transaction.
    Example: Medicine Book → supplier_name, invoice_number, expiry_date

    Args:
        cash_book_id: Target cash book UUID
        field_key: Machine-readable identifier (e.g., "supplier_name")
        field_label: Human-readable label (e.g., "Supplier Name")
        field_type: one of: text, number, date, boolean (default: text)
        is_required: If True, field must be provided when creating transactions
        display_order: Ascending sort order for UI

    Returns:
        The created custom field definition

    Raises:
        404: Cash book not found
        403: Cash book does not belong to current user
        400: Field key already exists in this cash book
    """
    cash_book = session.get(CashBook, cash_book_id)

    if not cash_book:
        raise HTTPException(status_code=404, detail="Cash book not found")

    if cash_book.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot access this cash book")

    # Check for duplicate key
    existing = session.exec(
        select(CashBookCustomField)
        .where(CashBookCustomField.cash_book_id == cash_book_id)
        .where(CashBookCustomField.field_key == payload.field_key)
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Field key '{payload.field_key}' already exists in this cash book"
        )

    field = CashBookCustomField(
        cash_book_id=cash_book_id,
        field_key=payload.field_key,
        field_label=payload.field_label,
        field_type=payload.field_type,
        is_required=payload.is_required,
        display_order=payload.display_order,
    )

    session.add(field)
    session.commit()
    session.refresh(field)

    return field


@router.get("/cash-books/{cash_book_id}/custom-fields", response_model=list[CashBookCustomFieldPublic])
def list_custom_fields(
    session: SessionDep,
    current_user: CurrentUser,
    cash_book_id: uuid.UUID = Path(...),
    active_only: bool = Query(True),
) -> list[CashBookCustomField]:
    """
    List custom field definitions for a cash book.

    Ordered by display_order ascending.

    Args:
        cash_book_id: Target cash book UUID
        active_only: If True, only returns active fields (default: True)

    Returns:
        List of custom field definitions

    Raises:
        404: Cash book not found
        403: Cash book does not belong to current user
    """
    cash_book = session.get(CashBook, cash_book_id)

    if not cash_book:
        raise HTTPException(status_code=404, detail="Cash book not found")

    if cash_book.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot access this cash book")

    statement = (
        select(CashBookCustomField)
        .where(CashBookCustomField.cash_book_id == cash_book_id)
    )

    if active_only:
        statement = statement.where(CashBookCustomField.is_active == True)

    statement = statement.order_by(asc(CashBookCustomField.display_order))

    return session.exec(statement).all()


@router.patch("/custom-fields/{field_id}", response_model=CashBookCustomFieldPublic)
def update_custom_field(
    payload: CashBookCustomFieldUpdate,
    session: SessionDep,
    current_user: CurrentUser,
    field_id: uuid.UUID = Path(...),
) -> CashBookCustomField:
    """
    Update a custom field definition.

    Cannot change field_key; only label, type, required flag, and order.

    Args:
        field_id: UUID of the custom field
        field_label: New display label
        field_type: New field type
        is_required: New required status
        display_order: New display order

    Returns:
        Updated custom field

    Raises:
        404: Field not found
        403: Field does not belong to current user's cash book
    """
    field = session.get(CashBookCustomField, field_id)

    if not field:
        raise HTTPException(status_code=404, detail="Custom field not found")

    # Verify access
    cash_book = session.get(CashBook, field.cash_book_id)
    if not cash_book or cash_book.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot access this field")

    if payload.field_label is not None:
        field.field_label = payload.field_label

    if payload.field_type is not None:
        field.field_type = payload.field_type

    if payload.is_required is not None:
        field.is_required = payload.is_required

    if payload.display_order is not None:
        field.display_order = payload.display_order

    from datetime import datetime
    field.updated_at = datetime.utcnow()

    session.add(field)
    session.commit()
    session.refresh(field)

    return field


@router.delete("/custom-fields/{field_id}", response_model=Message)
def deactivate_custom_field(
    session: SessionDep,
    current_user: CurrentUser,
    field_id: uuid.UUID = Path(...),
) -> Message:
    """
    Soft-delete a custom field (deactivate).

    Hidden from UI but historical values preserved.

    Args:
        field_id: UUID of the custom field

    Returns:
        Success message

    Raises:
        404: Field not found
        403: Field does not belong to current user's cash book
    """
    field = session.get(CashBookCustomField, field_id)

    if not field:
        raise HTTPException(status_code=404, detail="Custom field not found")

    # Verify access
    cash_book = session.get(CashBook, field.cash_book_id)
    if not cash_book or cash_book.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot access this field")

    field.is_active = False
    from datetime import datetime
    field.updated_at = datetime.utcnow()

    session.add(field)
    session.commit()

    return Message(message="Custom field deactivated successfully")


# ============================================================================
# TRANSACTIONS - CRUD & BALANCE
# ============================================================================

# ============================================================================
# TRANSACTIONS - CRUD & BALANCE
# ============================================================================

@router.post("/transactions", response_model=FinanceTransactionPublic)
def create_transaction(
    payload: FinanceTransactionCreate,
    session: SessionDep,
    current_user: CurrentUser,
) -> FinanceTransaction:
    """
    Record a new transaction in a cash book.
    
    Uses dynamic enum system for validation:
    - nature_code: CASH_IN or CASH_OUT (from TransactionNature enum type)
    - category_code: MEDICINE_PURCHASE, CONSULTATION, etc. (from TransactionCategory enum type)

    Args:
        cash_book_id: Target cash book UUID
        nature_code: "CASH_IN" or "CASH_OUT"
        category_code: Transaction category code
        amount: Positive decimal value
        transaction_date: Date of transaction
        remarks: Optional free-text note
        custom_field_values: Optional dict of { field_key: value }

    Returns:
        The created transaction with running balance

    Raises:
        400: Cash book not active, invalid nature/category, required fields missing
        403: Cash book does not belong to current user
        404: Cash book not found
    """
    # Validate cash book
    cash_book = session.get(CashBook, payload.cash_book_id)

    if not cash_book:
        raise HTTPException(status_code=404, detail="Cash book not found")

    if cash_book.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot access this cash book")

    if not cash_book.is_active:
        raise HTTPException(status_code=400, detail="Cannot add transactions to inactive cash book")

    # Validate nature_code against TransactionNature enum
    if not EnumService.validate_value(session, "TransactionNature", payload.nature_code):
        allowed = [opt.value for opt in EnumService.get_enum_options(session, "TransactionNature")]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid nature code '{payload.nature_code}'. Allowed values: {allowed}"
        )

    # Validate category_code against TransactionCategory enum
    if not EnumService.validate_value(session, "TransactionCategory", payload.category_code):
        allowed = [opt.value for opt in EnumService.get_enum_options(session, "TransactionCategory")]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category code '{payload.category_code}'. Allowed values: {allowed}"
        )

    # Compute running balance
    last_balance = _get_last_balance(session, payload.cash_book_id)

    if payload.nature_code == "CASH_IN":
        new_balance = last_balance + payload.amount
    elif payload.nature_code == "CASH_OUT":
        new_balance = last_balance - payload.amount
    else:
        raise HTTPException(status_code=400, detail="Nature must be CASH_IN or CASH_OUT")

    # Round to 2 decimal places
    new_balance = Decimal(str(round(float(new_balance), 2)))

    from datetime import datetime
    transaction = FinanceTransaction(
        cash_book_id=payload.cash_book_id,
        doctor_id=current_user.id,
        nature_code=payload.nature_code,
        category_code=payload.category_code,
        amount=payload.amount,
        transaction_date=payload.transaction_date,
        running_balance=new_balance,
        remarks=payload.remarks,
        created_at=datetime.utcnow(),
    )

    session.add(transaction)
    session.flush()

    # Save custom field values
    if payload.custom_field_values:
        for field_key, value in payload.custom_field_values.items():
            field_def = session.exec(
                select(CashBookCustomField)
                .where(CashBookCustomField.cash_book_id == payload.cash_book_id)
                .where(CashBookCustomField.field_key == field_key)
            ).first()

            if field_def:
                cfv = TransactionCustomFieldValue(
                    transaction_id=transaction.id,
                    field_id=field_def.id,
                    value=str(value) if value is not None else None,
                    created_at=datetime.utcnow(),
                )
                session.add(cfv)

    session.commit()
    session.refresh(transaction)

    return transaction


@router.get("/transactions", response_model=TransactionsPublic)
def list_transactions(
    session: SessionDep,
    current_user: CurrentUser,
    cash_book_id: uuid.UUID = Query(...),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    nature_code: Optional[str] = Query(None),
    category_code: Optional[str] = Query(None),
    include_deleted: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> TransactionsPublic:
    """
    List transactions for a cash book with optional filters.

    Args:
        cash_book_id: Required - target cash book UUID
        start_date: Optional - filter >= this date
        end_date: Optional - filter <= this date
        nature_code: Optional - filter by "CASH_IN" or "CASH_OUT"
        category_code: Optional - filter by category code
        include_deleted: If True, includes soft-deleted transactions
        skip: Pagination offset
        limit: Pagination limit

    Returns:
        List of transactions with total count

    Raises:
        404: Cash book not found
        403: Cash book does not belong to current user
    """
    cash_book = session.get(CashBook, cash_book_id)

    if not cash_book:
        raise HTTPException(status_code=404, detail="Cash book not found")

    if cash_book.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot access this cash book")

    statement = select(FinanceTransaction).where(FinanceTransaction.cash_book_id == cash_book_id)

    if not include_deleted:
        statement = statement.where(FinanceTransaction.is_deleted == False)

    if start_date:
        statement = statement.where(FinanceTransaction.transaction_date >= start_date)

    if end_date:
        statement = statement.where(FinanceTransaction.transaction_date <= end_date)

    if nature_code:
        statement = statement.where(FinanceTransaction.nature_code == nature_code)

    if category_code:
        statement = statement.where(FinanceTransaction.category_code == category_code)

    statement = statement.order_by(desc(FinanceTransaction.transaction_date), desc(FinanceTransaction.created_at))

    transactions = session.exec(statement.offset(skip).limit(limit)).all()
    count = session.exec(statement).all()

    return TransactionsPublic(data=transactions, count=len(count))


@router.get("/transactions/{transaction_id}", response_model=FinanceTransactionPublic)
def get_transaction(
    session: SessionDep,
    current_user: CurrentUser,
    transaction_id: uuid.UUID = Path(...),
) -> FinanceTransaction:
    """
    Retrieve a single transaction.

    Args:
        transaction_id: UUID of the transaction

    Returns:
        Transaction details

    Raises:
        404: Transaction not found
        403: Transaction does not belong to current user
    """
    transaction = session.get(FinanceTransaction, transaction_id)

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Verify access via cash book
    cash_book = session.get(CashBook, transaction.cash_book_id)
    if not cash_book or cash_book.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot access this transaction")

    return transaction


@router.patch("/transactions/{transaction_id}", response_model=FinanceTransactionPublic)
def update_transaction(
    payload: FinanceTransactionUpdate,
    session: SessionDep,
    current_user: CurrentUser,
    transaction_id: uuid.UUID = Path(...),
) -> FinanceTransaction:
    """
    Update an existing transaction.

    If amount or nature changes, all subsequent transactions
    in the same cash book have their balances recalculated.

    Args:
        transaction_id: UUID of the transaction
        amount: New amount (optional)
        transaction_date: New date (optional)
        nature_code: New nature (optional)
        category_code: New category (optional)
        remarks: New remarks (optional)
        custom_field_values: Update custom field values (optional)

    Returns:
        Updated transaction

    Raises:
        404: Transaction not found
        403: Transaction does not belong to current user
    """
    transaction = session.get(FinanceTransaction, transaction_id)

    if not transaction or transaction.is_deleted:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Verify access
    cash_book = session.get(CashBook, transaction.cash_book_id)
    if not cash_book or cash_book.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot access this transaction")

    balance_affecting_change = False
    from datetime import datetime

    if payload.amount is not None:
        transaction.amount = payload.amount
        balance_affecting_change = True

    if payload.transaction_date is not None:
        transaction.transaction_date = payload.transaction_date

    if payload.nature_code is not None:
        if not EnumService.validate_value(session, "TransactionNature", payload.nature_code):
            allowed = [opt.value for opt in EnumService.get_enum_options(session, "TransactionNature")]
            raise HTTPException(
                status_code=400,
                detail=f"Invalid nature code '{payload.nature_code}'. Allowed values: {allowed}"
            )
        transaction.nature_code = payload.nature_code
        balance_affecting_change = True

    if payload.category_code is not None:
        if not EnumService.validate_value(session, "TransactionCategory", payload.category_code):
            allowed = [opt.value for opt in EnumService.get_enum_options(session, "TransactionCategory")]
            raise HTTPException(
                status_code=400,
                detail=f"Invalid category code '{payload.category_code}'. Allowed values: {allowed}"
            )
        transaction.category_code = payload.category_code

    if payload.remarks is not None:
        transaction.remarks = payload.remarks

    # Upsert custom field values
    if payload.custom_field_values:
        for field_key, value in payload.custom_field_values.items():
            field_def = session.exec(
                select(CashBookCustomField)
                .where(CashBookCustomField.cash_book_id == transaction.cash_book_id)
                .where(CashBookCustomField.field_key == field_key)
            ).first()

            if field_def:
                existing = session.exec(
                    select(TransactionCustomFieldValue)
                    .where(TransactionCustomFieldValue.transaction_id == transaction.id)
                    .where(TransactionCustomFieldValue.field_id == field_def.id)
                ).first()

                if existing:
                    existing.value = str(value) if value is not None else None
                    existing.updated_at = datetime.utcnow()
                    session.add(existing)
                else:
                    session.add(TransactionCustomFieldValue(
                        transaction_id=transaction.id,
                        field_id=field_def.id,
                        value=str(value) if value is not None else None,
                        created_at=datetime.utcnow(),
                    ))

    transaction.updated_at = datetime.utcnow()
    session.add(transaction)
    session.commit()

    if balance_affecting_change:
        _recalculate_running_balances(session, transaction.cash_book_id)

    session.refresh(transaction)
    return transaction


@router.delete("/transactions/{transaction_id}", response_model=Message)
def soft_delete_transaction(
    session: SessionDep,
    current_user: CurrentUser,
    transaction_id: uuid.UUID = Path(...),
) -> Message:
    """
    Soft-delete a transaction (mark as deleted but preserve data).

    Excluded from balance calculations going forward.
    All subsequent transactions have balances recalculated.

    Args:
        transaction_id: UUID of the transaction to delete

    Returns:
        Success message

    Raises:
        404: Transaction not found or already deleted
        403: Transaction does not belong to current user
    """
    transaction = session.get(FinanceTransaction, transaction_id)

    if not transaction or transaction.is_deleted:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Verify access
    cash_book = session.get(CashBook, transaction.cash_book_id)
    if not cash_book or cash_book.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot access this transaction")

    from datetime import datetime
    transaction.is_deleted = True
    transaction.deleted_at = datetime.utcnow()
    transaction.deleted_by = current_user.id
    transaction.updated_at = datetime.utcnow()

    session.add(transaction)
    session.commit()

    # Recalculate balances
    _recalculate_running_balances(session, transaction.cash_book_id)

    return Message(message="Transaction deleted successfully")


# ============================================================================
# BALANCE & SUMMARY REPORTS
# ============================================================================

@router.get("/cash-books/{cash_book_id}/current-balance", response_model=dict)
def get_cash_book_balance(
    session: SessionDep,
    current_user: CurrentUser,
    cash_book_id: uuid.UUID = Path(...),
) -> dict:
    """
    Get the current running balance for a cash book.

    Args:
        cash_book_id: UUID of the cash book

    Returns:
        Dict with current_balance (Decimal)

    Raises:
        404: Cash book not found
        403: Cash book does not belong to current user
    """
    cash_book = session.get(CashBook, cash_book_id)

    if not cash_book:
        raise HTTPException(status_code=404, detail="Cash book not found")

    if cash_book.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot access this cash book")

    balance = _get_last_balance(session, cash_book_id)
    return {"cash_book_id": cash_book_id, "current_balance": balance}


@router.get("/cash-books/{cash_book_id}/summary", response_model=CashBookSummaryPublic)
def get_cash_book_summary(
    session: SessionDep,
    current_user: CurrentUser,
    cash_book_id: uuid.UUID = Path(...),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
) -> CashBookSummaryPublic:
    """
    Get financial summary for a single cash book.

    Args:
        cash_book_id: UUID of the cash book
        start_date: Optional - only count transactions >= this date
        end_date: Optional - only count transactions <= this date

    Returns:
        Summary with totals and balances

    Raises:
        404: Cash book not found
        403: Cash book does not belong to current user
    """
    cash_book = session.get(CashBook, cash_book_id)

    if not cash_book:
        raise HTTPException(status_code=404, detail="Cash book not found")

    if cash_book.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot access this cash book")

    # Get transactions for the period
    statement = (
        select(FinanceTransaction)
        .where(FinanceTransaction.cash_book_id == cash_book_id)
        .where(FinanceTransaction.is_deleted == False)
    )

    if start_date:
        statement = statement.where(FinanceTransaction.transaction_date >= start_date)

    if end_date:
        statement = statement.where(FinanceTransaction.transaction_date <= end_date)

    transactions = session.exec(statement).all()

    total_in = Decimal("0.00")
    total_out = Decimal("0.00")

    for txn in transactions:
        if txn.nature_code == "CASH_IN":
            total_in += txn.amount
        elif txn.nature_code == "CASH_OUT":
            total_out += txn.amount

    # Round all totals to 2 decimal places
    total_in = Decimal(str(round(float(total_in), 2)))
    total_out = Decimal(str(round(float(total_out), 2)))
    net_balance = Decimal(str(round(float(total_in - total_out), 2)))
    current_balance = Decimal(str(round(float(_get_last_balance(session, cash_book_id)), 2)))

    return CashBookSummaryPublic(
        cash_book_id=cash_book_id,
        name=cash_book.name,
        total_cash_in=total_in,
        total_cash_out=total_out,
        net_balance=net_balance,
        current_balance=current_balance,
        transaction_count=len(transactions),
    )


@router.get("/summary", response_model=DoctorFinanceSummaryPublic)
def get_doctor_summary(
    session: SessionDep,
    current_user: CurrentUser,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
) -> DoctorFinanceSummaryPublic:
    """
    Get consolidated financial summary across ALL cash books for current doctor.

    Args:
        start_date: Optional - only count transactions >= this date
        end_date: Optional - only count transactions <= this date

    Returns:
        Aggregated summary with per-book breakdown

    Raises:
        None - returns empty summary if no books exist
    """
    books = session.exec(
        select(CashBook).where(CashBook.doctor_id == current_user.id)
    ).all()

    grand_in = Decimal("0.00")
    grand_out = Decimal("0.00")
    grand_bal = Decimal("0.00")
    grand_count = 0
    book_summaries = []

    for book in books:
        # Get transactions in this book for the period
        statement = (
            select(FinanceTransaction)
            .where(FinanceTransaction.cash_book_id == book.id)
            .where(FinanceTransaction.is_deleted == False)
        )

        if start_date:
            statement = statement.where(FinanceTransaction.transaction_date >= start_date)

        if end_date:
            statement = statement.where(FinanceTransaction.transaction_date <= end_date)

        transactions = session.exec(statement).all()

        total_in = Decimal("0.00")
        total_out = Decimal("0.00")

        for txn in transactions:
            if txn.nature_code == "CASH_IN":
                total_in += txn.amount
            elif txn.nature_code == "CASH_OUT":
                total_out += txn.amount

        current_bal = _get_last_balance(session, book.id)

        # Round to 2 decimal places for book-level totals
        total_in = Decimal(str(round(float(total_in), 2)))
        total_out = Decimal(str(round(float(total_out), 2)))
        net_balance = Decimal(str(round(float(total_in - total_out), 2)))
        current_bal = Decimal(str(round(float(current_bal), 2)))

        grand_in += total_in
        grand_out += total_out
        grand_bal += current_bal
        grand_count += len(transactions)

        book_summaries.append(CashBookSummaryPublic(
            cash_book_id=book.id,
            name=book.name,
            total_cash_in=total_in,
            total_cash_out=total_out,
            net_balance=net_balance,
            current_balance=current_bal,
            transaction_count=len(transactions),
        ))

    # Round grand totals to 2 decimal places
    grand_in = Decimal(str(round(float(grand_in), 2)))
    grand_out = Decimal(str(round(float(grand_out), 2)))
    grand_net = Decimal(str(round(float(grand_in - grand_out), 2)))
    grand_bal = Decimal(str(round(float(grand_bal), 2)))

    return DoctorFinanceSummaryPublic(
        total_cash_in=grand_in,
        total_cash_out=grand_out,
        net_balance=grand_net,
        total_current_balance=grand_bal,
        transaction_count=grand_count,
        books=book_summaries,
    )
