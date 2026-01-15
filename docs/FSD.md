# Gastronom Backend - Feature Specification Document

## Overview

This document outlines the architecture decisions and specifications for the Gastronom backend, an ecommerce platform for eastern european products.

---

## Context

### Physical Shop Integration

The physical shop uses **1C**, a Russian business management software. Key constraints:
- Runs on an old PC with limited resources
- We cannot modify the 1C system
- We can scrape all necessary data from it
- Data shown below is already formatted/cleaned from raw 1C output

### Data Available from 1C Scraper (Sample)

```json
{
    "extartnr": "203",
    "shorttext": "Salami SK Moskowskaja",
    "baseprice": 2.89,
    "prodid": 584,
    "cdate": "2025-11-20 11:06:02.292051",
    "maingroup": "Sausage",
    "catalog_level_2": "Raw sausage",
    "ext_zutaten": "100g made from 130g pork and beef. Ingredients: pork, beef, bacon, cooking salt, seasonings, dextrose, flavour enhancer: monosodium glutamate, spice extracts, antioxidants: ascorbic acid, ripening cultures, preservative: sodium nitrite, smoke. Sausage casing is not edible.",
    "ext_kilojoule": 1895,
    "ext_kilokal": 457,
    "ext_eiweiss": "25",
    "ext_fett": "39",
    "ext_gesfett": "17",
    "ext_kohlenhydrate": "1,0",
    "ext_zucker": "<0,5",
    "ext_speisesalz": "3,4",
    "ext_print_content_num": 1,
    "ext_print_content_unit": "pcs.",
    "ext_print_compare_num": 1,
    "ext_print_compare_unit": "kg",
    "ext_print_multiplier": 4,
    "ext_print_productname": "Salami Russian recipe",
    "unit": "pcs.",
    "unit_short": "STK",
    "unit_price": 2.89,
    "packing": "Box",
    "vendorname": "Lackmann Fleisch- und Feinkostfabrik GmbH",
    "ext_calc_weight_per_box": "4.000 kg",
    "ext_contents_per_large_unit": "62",
    "barcode": "4250370502031",
    "stock_expiry_date": "2 Feb 2026",
    "ext_weight": "0.250 kg",
    "ext_sales_price": "EUR 3.99",
    "currentdeliverysizeshortname": "Box",
    "inner_gastroport_base_unit": "pcs."
}
```

### Source of Truth

The **physical shop (1C) is the master**. The ecommerce database follows/mirrors it.

---

## 1C Field Mapping to Database

### Product Table (Initial Indexing)

| 1C Field | DB Field | Notes |
|----------|----------|-------|
| `prodid` | `external_id` | 1C internal ID, used for sync matching |
| `barcode` | `barcode` | EAN barcode, also used for matching |
| `extartnr` | `article_number` | Shop's article number |
| `shorttext` | `name` | Product name (German) |
| `ext_print_productname` | `name_display` | Display name (English) - optional |
| `ext_zutaten` | `ingredients` | Ingredients/description text |
| `ext_sales_price` | `price` | Retail price (⚠️ needs verification vs baseprice) |
| `baseprice` | - | Base/wholesale price (⚠️ TBD with shop owner) |
| `ext_weight` | `weight` | Weight in grams (parse from "0.250 kg") |
| `unit` | `unit` | Selling unit (pcs., kg, etc.) |
| `maingroup` | `category_id` | Level 1 category (FK) |
| `catalog_level_2` | `subcategory_id` | Level 2 category (FK) |
| `vendorname` | `vendor` | Supplier/manufacturer |
| `packing` | `packing_type` | Box, Single, etc. |
| `cdate` | `created_at` | When added to 1C |

### Nutritional Values

| 1C Field | DB Field | Notes |
|----------|----------|-------|
| `ext_kilokal` | `kcal` | Calories per 100g |
| `ext_kilojoule` | `kilojoules` | Energy in kJ |
| `ext_eiweiss` | `proteins` | Protein in grams |
| `ext_fett` | `fat` | Total fat in grams |
| `ext_gesfett` | `saturated_fat` | Saturated fat in grams |
| `ext_kohlenhydrate` | `carbs` | Carbohydrates in grams |
| `ext_zucker` | `sugar` | Sugar in grams |
| `ext_speisesalz` | `salt` | Salt in grams |

### Stock & Expiry (Simplified)

| 1C Field | Usage | Notes |
|----------|-------|-------|
| `stock_expiry_date` | Ignored | Staff handles expiry manually during packing |
| Quantity | From separate sync | Hourly sync will provide stock quantity |

**Note:** Batch tracking not needed - see "Batch/Expiry Tracking" section below.

---

## Stock Management Strategy

To handle the problem of concurrent purchases (online vs in-store), we use a **stock buffer** approach:

```
available_online = stock_quantity - stock_buffer
```

- Default buffer: **5 items** (configurable)
- This ensures the physical shop always has items to display
- Avoids the complexity of real-time inventory sync
- Stock buffer: global default + per-product override if needed

---

## Products Module Design

### Product Model (Phase 1 - Initial Indexing)

```python
Product:
├── id (UUID)                 # Internal ID for ecommerce
├── external_id (int)         # prodid from 1C - primary sync key
├── barcode (string)          # EAN barcode - secondary sync key
├── article_number (string)   # extartnr - shop's article number
├── name (string)             # shorttext
├── name_display (string)     # ext_print_productname (optional)
├── ingredients (text)        # ext_zutaten
├── vendor (string)           # vendorname
├── packing_type (string)     # Box, Single, etc.
│
├── # Units & Pricing
├── selling_unit (enum)           # How customer orders: "pcs" | "kg" | "g"
├── pricing_unit (enum)           # How price is calculated: "pcs" | "kg"
├── price_per_pricing_unit_synced (decimal)   # From 1C
├── price_per_pricing_unit_override (decimal) # Owner override (nullable)
├── weight_per_unit_grams (int, nullable)     # For piece-based: grams per piece
├── average_weight_grams (int, nullable)      # For discrete weight-priced (fish): avg weight
│
├── # Stock (from 1C)
├── stock_amount_synced (decimal)   # Raw amount from 1C (pieces or kg)
├── stock_amount_override (decimal) # Owner override (nullable)
├── stock_buffer (decimal)          # Default 5, per-product override
│
├── # Nutritional (per 100g)
├── kcal (int)
├── kilojoules (int)
├── proteins (decimal)
├── fat (decimal)
├── saturated_fat (decimal)
├── carbs (decimal)
├── sugar (decimal)
├── salt (decimal)
│
├── # Categories
├── category_id (FK)          # Points to leaf category (see Category model)
│
├── # Relations
├── images (relation)
│
├── # Status
├── is_available (bool)       # Can be manually disabled by owner
├── created_at (datetime)
├── updated_at (datetime)
└── last_synced_at (datetime) # When scraper last updated this
```

### Product Types & Pricing Logic

Three product types based on `selling_unit` and `pricing_unit`:

| Type | Example | selling_unit | pricing_unit | avg_weight | Display Price |
|------|---------|--------------|--------------|------------|---------------|
| Piece-based | Salami | pcs | pcs | NULL | €3.99/piece |
| Weight-based (continuous) | Cheese | kg | kg | NULL | €12.99/kg |
| Weight-priced discrete | Fish | pcs | kg | 350g | €5.25/piece* |

*Fish: €15.00/kg × 0.35kg = €5.25/piece (based on average weight)

**Effective price calculation:**
```python
def get_display_price(product):
    base_price = product.price_override ?? product.price_synced

    if product.selling_unit == product.pricing_unit:
        return base_price  # Simple case

    if product.selling_unit == "pcs" and product.pricing_unit == "kg":
        # Fish case: price per piece = price per kg × average weight
        return base_price * (product.average_weight_grams / 1000)
```

**Frontend display:**
- Piece-based: "€3.99" with "Add to cart" button
- Weight-based: "€12.99/kg" with weight selector (100g, 250g, 500g...)
- Fish: "~€5.25/piece (avg 350g)" with quantity selector

**Stock calculation:**
```python
effective_stock = (stock_amount_override ?? stock_amount_synced) - stock_buffer
```

**Override logic:**
- 1C syncs `price_per_pricing_unit_synced` and `stock_amount_synced` hourly
- Owner can set overrides in admin dashboard
- Override takes precedence; set to NULL to revert to 1C value

### ProductImage Model

```python
ProductImage:
├── id (UUID)
├── product_id (FK)
├── url (string)              # S3 URL
├── position (int)            # Display order (0 = first)
├── is_primary (bool)         # Main image for listings
├── alt_text (string)         # Accessibility
└── uploaded_at (datetime)
```

### Category Model (Hierarchical)

```python
Category:
├── id (UUID)
├── name (string)             # "Sausage", "Raw sausage"
├── parent_id (FK, nullable)  # NULL for top-level (maingroup)
└── slug (string)             # URL-friendly name
```

### Batch/Expiry Tracking - NOT NEEDED

**Decision:** Batch tracking is deferred indefinitely. Not needed for Phase 1 (or likely Phase 2).

**Reasoning (discussed with shop owner):**
- 1C only provides batch expiry dates, NOT quantity-per-batch (e.g., "3 batches expiring X, Y, Z" but not "10 units expire X, 20 units expire Y")
- Shop staff packs all orders - they manually select appropriate expiry dates
- Products move fast - close-to-expiry items are rare
- Items close to expiry are churned from 1C before becoming a problem
- Scale is small enough for manual coordination
- If expiry date is problematic for an order, staff contacts customer directly

**What we track instead:** Just total `stock_quantity`. The stock buffer (quantity - 5) ensures physical shop always has items to handle edge cases.

**Future consideration:** If scale increases significantly, revisit batch tracking. Would require 1C to provide quantity-per-batch data.

---

## Product Search & Filtering

How customers find products on the frontend.

### Search

**Full-text search** on:
- `name` (primary)
- `name_display`
- `ingredients`
- `vendor`

**Implementation options:**
- **Phase 1:** PostgreSQL `ILIKE` or `tsvector` (built-in, good enough for ~1000 products)
- **Phase 2:** Elasticsearch/Meilisearch if search performance becomes an issue

### Filters

| Filter | Type | Example |
|--------|------|---------|
| Category | Single/Multi select | "Sausage", "Dairy" |
| Price range | Min/Max slider | €0 - €50 |
| In stock | Toggle | Only show available |
| Vendor | Multi select | "Lackmann", etc. |

**Optional filters (Phase 2):**
| Filter | Type | Notes |
|--------|------|-------|
| Nutritional | Range | "< 500 kcal", "Low sugar" |
| Dietary | Tags | "Vegetarian", "Gluten-free" (would need new field) |
| Weight range | Min/Max | For weight-based products |

### Sorting

| Sort option | Field |
|-------------|-------|
| Name A-Z | `name` ASC |
| Name Z-A | `name` DESC |
| Price low-high | effective_price ASC |
| Price high-low | effective_price DESC |
| Newest | `created_at` DESC |

### API Endpoint

```
GET /api/products
    ?search=salami
    &category=sausage
    &min_price=0
    &max_price=20
    &in_stock=true
    &sort=price_asc
    &page=1
    &per_page=20
```

Returns paginated product list with total count for frontend pagination.

---

## Authentication with Clerk

The authentication flow:

1. **Frontend** handles login/signup via Clerk's SDK (supports Google, Facebook, email)
2. **Frontend** gets a JWT token from Clerk
3. **Backend** validates that JWT on protected routes
4. **Backend** extracts user ID from token, creates/updates local user record

Users are required to login (no guest checkout).

### User Model

```python
User:
├── id (UUID)
├── clerk_id (string)            # From Clerk JWT - unique
├── email (string)
├── name (string)
├── phone_number (string)        # For delivery coordination
├── auth_provider (string)       # "google", "facebook", "email" - for analytics
│
├── # Orders & Spending
├── orders (relation)            # Order history
├── total_spent (decimal)        # Cumulative spending - drives fidelity discount
├── order_count (int)            # Number of completed orders
│
├── # Fidelity Program
├── fidelity_enabled (bool)      # Is user enrolled in fidelity program
├── fidelity_discount (decimal)  # Cached current discount % (computed from total_spent)
│
├── # Delivery
├── addresses (relation)         # Multiple addresses
├── default_address_id (FK)      # Primary delivery address
├── delivery_distance_km (decimal)   # Last calculated distance from shop
├── delivery_time_minutes (int)      # Last calculated travel time
├── delivery_eligible (bool)         # Within delivery range?
├── delivery_checked_at (datetime)   # When delivery was last verified
│
├── # Legal/GDPR
├── marketing_consent (bool)     # Opted in to promotional emails
├── privacy_accepted_at (datetime)
│
├── # Admin
├── notes (text)                 # Staff notes about customer
├── is_active (bool)             # Soft disable without deleting
├── is_admin (bool)              # Admin privileges
│
├── # Timestamps
├── created_at (datetime)
└── last_login_at (datetime)
```

### Address Model

```python
Address:
├── id (UUID)
├── user_id (FK)
├── label (string)               # "Home", "Work", "Mom's house"
├── street (string)
├── house_number (string)
├── apartment (string)           # Optional - floor, apt number
├── city (string)
├── postal_code (string)
├── country (string)             # Default: Germany
├── latitude (decimal)           # For distance calculation
├── longitude (decimal)          # For distance calculation
├── delivery_instructions (text) # "Ring twice", "Leave at door"
├── is_default (bool)
└── created_at (datetime)
```

### Order Model

```python
Order:
├── id (UUID)
├── order_number (string)        # Human-readable: "GAS-2026-00042"
├── user_id (FK)
│
├── # Status
├── status (enum)                # pending, confirmed, processing, shipped, delivered, cancelled
├── payment_status (enum)        # pending, paid, failed, refunded
│
├── # Pricing (all computed at order time)
├── subtotal (decimal)           # Sum of line items before discount
├── discount_percent (decimal)   # Fidelity % applied (snapshot)
├── discount_amount (decimal)    # Actual discount in €
├── delivery_fee (decimal)       # Delivery charge
├── total (decimal)              # Final amount: subtotal - discount + delivery_fee
│
├── # Payment
├── payment_method (enum)        # paypal, card, cash_on_delivery
├── payment_reference (string)   # Transaction ID from PayPal/Stripe (nullable)
│
├── # Delivery Address (SNAPSHOT - not FK, copied at order time)
├── delivery_name (string)
├── delivery_phone (string)
├── delivery_street (string)
├── delivery_house_number (string)
├── delivery_apartment (string)
├── delivery_city (string)
├── delivery_postal_code (string)
├── delivery_instructions (text)
│
├── # Relations
├── items (relation)             # OrderItem list
│
├── # Admin
├── admin_notes (text)           # Staff notes on this order
├── fulfilled_by (FK, nullable)  # Which admin fulfilled it
├── cancelled_by (FK, nullable)  # Which admin cancelled it
├── cancellation_reason (text)
│
├── # Timestamps
├── created_at (datetime)
├── confirmed_at (datetime)
├── shipped_at (datetime)
├── delivered_at (datetime)
└── cancelled_at (datetime)
```

### OrderItem Model

```python
OrderItem:
├── id (UUID)
├── order_id (FK)
├── product_id (FK)
│
├── # Product Snapshot (captured at order time)
├── product_name (string)        # In case product name changes
├── product_barcode (string)     # For packing/verification
├── selling_unit (string)        # "pcs", "kg", "g" at order time
├── unit_price (decimal)         # Price per selling unit at order time
│
├── # Quantity (interpretation depends on selling_unit)
├── quantity (decimal)           # 3 (pieces) or 0.5 (kg)
└── line_total (decimal)         # unit_price × quantity
```

**OrderItem examples:**

| Product | selling_unit | quantity | unit_price | line_total |
|---------|--------------|----------|------------|------------|
| 3× Salami | pcs | 3 | €3.99 | €11.97 |
| 500g Cheese | kg | 0.5 | €12.99 | €6.50 |
| 2× Fish | pcs | 2 | €5.25* | €10.50 |

*Fish unit_price is pre-calculated from avg_weight × price_per_kg

### Order Status Flow

```
┌─────────┐     ┌───────────┐     ┌────────────┐     ┌─────────┐     ┌───────────┐
│ pending │ ──▶ │ confirmed │ ──▶ │ processing │ ──▶ │ shipped │ ──▶ │ delivered │
└─────────┘     └───────────┘     └────────────┘     └─────────┘     └───────────┘
                     │
                     ▼
               ┌───────────┐
               │ cancelled │
               └───────────┘
```

- **pending**: Order created, awaiting payment confirmation
- **confirmed**: Payment received (or COD accepted), ready to process
- **processing**: Staff is picking/packing the order
- **shipped**: Out for delivery
- **delivered**: Customer received it
- **cancelled**: Order cancelled (refund if applicable)

### Stock Deduction

**When to deduct stock?**

Option A: At order creation (pending) → Risk: unpaid orders hold stock
Option B: At confirmation (payment received) → **Recommended**

We deduct `stock_quantity` when order moves to `confirmed`. If cancelled, we restore it.

### Payment & Refunds

| Payment Method | Refund Process |
|----------------|----------------|
| PayPal | API refund via PayPal |
| Card (Stripe) | API refund via Stripe |
| Cash on Delivery | N/A - no payment collected yet |

**Phase 1:** Manual refunds - admin marks as refunded, processes externally
**Phase 2:** Automated refunds via payment provider APIs

### Fidelity Program Logic

The shop has a spending-based discount program. Discount is derived from `total_spent`:

| Total Spent | Discount |
|-------------|----------|
| < €1000     | 0%       |
| €1000       | 5%       |
| €1500       | ~12.5%   |
| €2000+      | 20% (cap)|

```python
def calculate_fidelity_discount(total_spent: float) -> float:
    if total_spent < 1000:
        return 0
    if total_spent >= 2000:
        return 20  # Cap at 20%
    # Linear scale: 5% at €1000 → 20% at €2000
    return 5 + ((total_spent - 1000) / 1000) * 15
```

**Configuration:** Thresholds stored in settings table (not hardcoded) so owner can adjust.

**Note:** Feature is optional. Owner may or may not enable it for online store.

### Delivery Range Calculation

Shop is in a coastal city between sea and mountains. Straight-line distance is unreliable.

**Approach:**
1. When user adds/updates address, call a routing API (Google Maps, OpenRouteService, etc.)
2. Calculate actual driving time from shop to address
3. Store `delivery_time_minutes` and `delivery_distance_km`
4. Mark `delivery_eligible` based on threshold (e.g., < 45 minutes)
5. Re-check periodically or when address changes

**Open question:** What's the delivery time threshold? 30 min? 45 min? 1 hour?

---

## Scraper Architecture

Decision: **Option B** - Scraper will call backend API endpoints.

### Two Sync Mechanisms

#### 1. Browser Extension (Manual Product Indexing)
- Used for initial product indexing
- Points to backend API endpoint
- Operator selects products in 1C interface, extension scrapes and sends to API
- Good for adding new products, bulk imports

#### 2. Automated Hourly Sync (Stock & Price Updates)
- Scheduled job (cron or similar)
- Syncs from 1C to ecommerce database
- Updates: stock quantities, prices, availability
- Frequency: **every hour** (configurable)
- Needs: dedicated sync endpoint or batch update API

### API Endpoints Needed for Scraper

```
POST /api/products/sync           # Single product upsert
POST /api/products/sync/batch     # Batch upsert (multiple products)
POST /api/stock/sync              # Stock-only update (hourly sync)
```

### Sync Edge Cases

#### 1. Product Deleted from 1C
**Decision:** Soft delete - set `is_available = false`, keep record.

- Product stays in database (order history intact)
- Becomes unavailable for purchase
- Admin can see "missing from 1C" flag
- Can be re-enabled if product reappears in 1C

#### 2. Sync Fails Mid-Batch
**Decision:** Partial success with logging.

- Save products that succeeded
- Log failures with error details
- Alert admin if failure rate > threshold (e.g., >10%)
- Failed products retain previous values
- Retry failed ones on next sync

#### 3. Parsing Errors (Weight, Price)
**Decision:** Parse defensively, never overwrite good data with bad.

```python
def parse_weight(raw: str) -> int | None:
    """Parse '0.250 kg' → 250 (grams)"""
    try:
        # Handle "0.250 kg", "250 g", "0,250 kg" etc.
        cleaned = raw.lower().replace(",", ".").strip()
        if "kg" in cleaned:
            return int(float(cleaned.replace("kg", "").strip()) * 1000)
        if "g" in cleaned:
            return int(float(cleaned.replace("g", "").strip()))
        return None
    except:
        return None

# Usage: only update if parse succeeds
new_weight = parse_weight(raw_value)
if new_weight is not None:
    product.weight_per_unit_grams = new_weight
# else: keep existing value, log warning
```

**Price:** Comes directly from 1C as number now (not string), no parsing needed.

---

## Admin Dashboard

The owner and staff need a dashboard to manage orders, products, and customers.

**Access:** Single admin role for owner and staff (no role hierarchy needed for now).

### Order Management

| Feature | Description |
|---------|-------------|
| View orders | List with filters: status, date range, customer |
| Order details | Items, totals, customer info, delivery address |
| Update status | Move through: pending → confirmed → processing → shipped → delivered |
| Cancel order | Set cancellation reason, trigger refund if applicable |
| Add notes | Staff notes visible only in admin |
| Print packing slip | Generate PDF for warehouse |

### Product Management

| Feature | Description |
|---------|-------------|
| View products | List with search, filter by category, stock status |
| Edit price | Set `price_override` (or clear to use 1C price) |
| Edit stock | Set `stock_override` (or clear to use 1C stock) |
| Edit buffer | Adjust `stock_buffer` per product |
| Toggle availability | Enable/disable `is_available` |
| View sync status | See `last_synced_at`, flag stale products |
| Force re-sync | Trigger immediate sync for a product |

### Customer Management

| Feature | Description |
|---------|-------------|
| View customers | List with search, filter by fidelity status |
| Customer details | Order history, total spent, addresses |
| Add notes | Staff notes ("VIP customer", "problematic") |
| Disable account | Set `is_active = false` |
| View fidelity | Current discount %, spending history |

### Inventory Alerts

| Alert | Trigger |
|-------|---------|
| Low stock | `effective_stock < threshold` (e.g., < 5) |
| Out of stock | `effective_stock <= 0` |
| Sync stale | `last_synced_at` older than 2 hours |
| Expiring soon | Batch expiry within 7 days (Phase 2) |

### Settings (Owner only?)

| Setting | Description |
|---------|-------------|
| Fidelity program | Enable/disable, adjust thresholds |
| Default stock buffer | Global default for new products |
| Delivery threshold | Max delivery time in minutes |
| Sync frequency | How often to sync from 1C |

### Reports (Phase 2)

- Sales by period (day/week/month)
- Top selling products
- Revenue trends
- Customer acquisition
- Inventory turnover

---

## Open Questions (To verify with shop owner)

1. **Price field:** Use `ext_sales_price` or `baseprice`? *(Needs verification)*
2. ~~**Batch tracking:** How does 1C track product batches/expiry dates?~~ → **RESOLVED:** Not needed, staff handles manually
3. **Quantity field:** Where does stock quantity come from in 1C? *(Needs verification)*
4. **Sync frequency:** Is hourly sync sufficient for stock updates? *(Needs verification)*
5. **Delivery time threshold:** What's the cutoff? 30 min? 45 min? 1 hour? *(Needs verification)*

---

## Session Log

**2026-01-14:** Initial architecture discussion. Defined product model structure, stock buffer strategy, and authentication flow with Clerk. Added complete 1C field mapping, batch tracking considerations, and dual sync mechanism (browser extension + hourly automated sync).

**2026-01-14 (continued):** Added User model with social login support (Google, Facebook via Clerk), fidelity program (spending-based discount 5-20%), delivery range calculation (routing API for coastal/mountain geography), Address model with lat/long for distance calc, GDPR fields, admin notes.

**2026-01-14 (continued):** Added Order and OrderItem models with full status flow (pending→confirmed→processing→shipped→delivered/cancelled). Address snapshot in orders. Stock deduction at confirmation. Payment methods (PayPal, card, COD) with manual refunds for Phase 1. Updated Product model with price_override and stock_override for owner control over 1C synced values. Added ProductImage model. Added comprehensive Admin Dashboard spec covering order management, product management, customer management, inventory alerts, settings, and Phase 2 reports.

**2026-01-14 (continued):** Resolved batch/expiry tracking - NOT NEEDED (staff handles manually, 1C doesn't provide quantity-per-batch). Added three product types: piece-based (salami), weight-based continuous (cheese), and weight-priced discrete (fish with average weight). Separated selling_unit from pricing_unit. Added sync edge cases (soft delete for removed products, partial success for failed syncs, defensive parsing). Added Product Search & Filtering section with full-text search, category/price/stock filters, sorting options, and API endpoint spec.
