# Development Notes

Learning notes and explanations captured during development.

---

## SQLAlchemy & Database Concepts

### 1. Why model creation order matters (Foreign Keys)

In relational databases, when you have a **foreign key** (FK), the table you're referencing **must exist first**.

Our Product model has:
```python
category_id: ForeignKey("categories.id")
```

This means:
- Product table has a column `category_id`
- That column points to `categories.id`
- PostgreSQL will **reject** creating the Product table if `categories` table doesn't exist yet

**Order matters:**
```
categories (create first)
    ↓
products (references categories.id)
    ↓
product_images (references products.id)
```

This applies to:
- Creating models (code order doesn't strictly matter, but helps clarity)
- **Migrations** (must run in correct order)
- Inserting data (can't add a product with `category_id=5` if category 5 doesn't exist)

---

### 2. SQLAlchemy 2.0 syntax: `Mapped` and `mapped_column`

This is **SQLAlchemy 2.0** syntax (released 2023). Older tutorials use different syntax.

**Old way (SQLAlchemy 1.x):**
```python
class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    price = Column(Numeric(10, 2))
```

**New way (SQLAlchemy 2.0):**
```python
class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
```

**What's the difference?**

`Mapped[str]` is a **type hint**. It tells:
- Python/your IDE: "this attribute is a string"
- SQLAlchemy: "this column cannot be NULL" (because `str`, not `str | None`)

`Mapped[Decimal | None]` means:
- Can be `Decimal` or `None`
- SQLAlchemy infers `nullable=True`

**Why the change?**
- Better IDE autocomplete
- Catches type errors before runtime
- Cleaner, more Pythonic
- Aligns with modern Python typing (3.9+)

**The pattern:**
```python
column_name: Mapped[PythonType] = mapped_column(SQLType, ...options)
```

---

### 3. UUID vs auto-increment Integer for primary keys

**Auto-increment Integer:**
```python
id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
# Creates: 1, 2, 3, 4, 5...
```

**UUID:**
```python
id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
# Creates: "550e8400-e29b-41d4-a716-446655440000", ...
```

**Comparison:**

| Aspect | Integer | UUID |
|--------|---------|------|
| Size | 4 bytes | 16 bytes |
| Guessable | Yes (id=1, id=2...) | No |
| Merge databases | Conflicts! | No conflicts |
| Generate before insert | No (DB assigns) | Yes (app can generate) |
| URL exposure | `/product/1` leaks info | `/product/550e8400...` safe |

**Why UUID for Gastronom:**
1. **Security**: URLs like `/order/5` tell attackers "there are only 5 orders". UUID doesn't leak this.
2. **Future-proofing**: If you ever merge databases (e.g., multiple shops), UUIDs won't collide.
3. **Distributed sync**: The scraper can generate IDs before inserting - useful for batch operations.

**Trade-off:** UUIDs are larger and slightly slower for joins. For a shop with ~1000 products, this doesn't matter.

---

## Model Examples

### Self-referential Foreign Key (Category hierarchy)

For a Category that can have a parent Category:

```python
class Category(Base):
    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Self-referential FK
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id"),  # Points to same table
        nullable=True  # NULL = top-level category
    )

    # Relationships
    parent: Mapped["Category | None"] = relationship(
        "Category",
        remote_side=[id],  # Required for self-referential
        back_populates="children"
    )
    children: Mapped[list["Category"]] = relationship(
        "Category",
        back_populates="parent"
    )
```

**Key points:**
- `ForeignKey("categories.id")` - references its own table
- `remote_side=[id]` - tells SQLAlchemy which side is the "parent"
- `nullable=True` - top-level categories have no parent

---

### 5. What goes in `Mapped[...]`? (Python types vs SQLAlchemy types)

**The rule:** `Mapped` takes **Python types**, not SQLAlchemy types.

There are two "worlds":
1. **Python world** - `str`, `int`, `uuid.UUID`, `Decimal`, `datetime`
2. **SQLAlchemy world** - `String`, `Integer`, `UUID`, `Numeric`, `DateTime`

```python
column: Mapped[PythonType] = mapped_column(SQLAlchemyType, ...)
```

**Common mistake:**
```python
# WRONG - UUID here is SQLAlchemy type:
id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ...)

# RIGHT - uuid.UUID is Python type:
id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ...)
```

**Quick reference:**

| Python Type | SQLAlchemy Type | Example |
|-------------|-----------------|---------|
| `str` | `String(n)` or `Text` | `Mapped[str] = mapped_column(String(255))` |
| `int` | `Integer` | `Mapped[int] = mapped_column(Integer)` |
| `bool` | `Boolean` | `Mapped[bool] = mapped_column(Boolean)` |
| `uuid.UUID` | `UUID(as_uuid=True)` | `Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))` |
| `Decimal` | `Numeric(p, s)` | `Mapped[Decimal] = mapped_column(Numeric(10, 2))` |
| `datetime` | `DateTime` | `Mapped[datetime] = mapped_column(DateTime)` |

**Nullable version:** Add `| None` to Python type:
```python
Mapped[str | None]      # Can be string or NULL
Mapped[Decimal | None]  # Can be Decimal or NULL
```

**Standard imports for models:**
```python
import uuid
from decimal import Decimal
from datetime import datetime
from sqlalchemy import String, Integer, Text, Boolean, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
```

---

### 6. Why Decimal instead of Float? (Money precision)

**Float has precision problems:**
```python
>>> 0.1 + 0.2
0.30000000000000004  # NOT 0.3!

>>> 19.99 * 3
59.970000000000006   # NOT 59.97!
```

This happens because floats are stored in binary, and some decimal numbers (like 0.1) can't be represented exactly in binary - just like 1/3 can't be written exactly in decimal (0.333...).

**For money, this is unacceptable:**
```python
# Float disaster:
price = 19.99
quantity = 1000
total = price * quantity  # 19989.999999999996 instead of 19990.00

# After many transactions, you're missing cents/euros
```

**Decimal is exact:**
```python
from decimal import Decimal

>>> Decimal("0.1") + Decimal("0.2")
Decimal('0.3')  # Exact!

>>> Decimal("19.99") * 3
Decimal('59.97')  # Exact!
```

**Rule:** Always use `Decimal` for money, prices, quantities you sell by weight.

---

### 7. What is Numeric(precision, scale)?

`Numeric(precision, scale)` is the SQLAlchemy type for exact decimal numbers in the database.

- **precision** = total number of digits
- **scale** = digits after decimal point

```python
Numeric(10, 2)  # Up to 99999999.99 (10 digits total, 2 after decimal)
Numeric(6, 3)   # Up to 999.999 (6 digits total, 3 after decimal)
```

**Examples for Gastronom:**

| Use Case | Type | Max Value |
|----------|------|-----------|
| Price in € | `Numeric(10, 2)` | €99,999,999.99 |
| Weight in kg | `Numeric(10, 3)` | 9,999,999.999 kg |
| Stock quantity | `Numeric(10, 3)` | 9,999,999.999 units |
| Percentage | `Numeric(5, 2)` | 999.99% |

**In PostgreSQL**, `Numeric` becomes the `NUMERIC` or `DECIMAL` type (they're identical in Postgres).

**Don't confuse:**
- `Numeric` = SQLAlchemy type (for database)
- `Decimal` = Python type (for code)
- `DECIMAL` = Also SQLAlchemy type, but just use `Numeric`

---

## Session Log

**2026-01-16:** Added initial SQLAlchemy concepts (FK order, Mapped syntax, UUID vs Integer).
**2026-01-18:** Added Mapped type reference (Python vs SQLAlchemy types), Decimal vs Float explanation, Numeric precision/scale guide.
