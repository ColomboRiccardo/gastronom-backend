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

## Session Log

**2026-01-16:** Added initial SQLAlchemy concepts (FK order, Mapped syntax, UUID vs Integer).
