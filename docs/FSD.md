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

### Stock & Batches (Future - needs verification with shop owner)

| Concept | Notes |
|---------|-------|
| `stock_expiry_date` | Expiry date - but products come in **batches** with different expiry dates |
| Quantity | Not in current sample - needed for orders |
| Batch tracking | Same product can have multiple batches with different expiry dates |

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
├── price (decimal)           # ext_sales_price (parsed)
├── weight (int)              # In grams (parsed from ext_weight)
├── unit (string)             # pcs., kg, etc.
├── vendor (string)           # vendorname
├── packing_type (string)     # Box, Single, etc.
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
├── category_id (FK)          # maingroup
├── subcategory_id (FK)       # catalog_level_2
│
├── # Stock
├── stock_quantity (int)      # Raw quantity from 1C
├── stock_buffer (int)        # Default 5, per-product override
│
├── # Relations
├── images (relation)
│
├── # Status
├── is_available (bool)       # Can be manually disabled
├── created_at (datetime)
├── updated_at (datetime)
└── last_synced_at (datetime) # When scraper last updated this
```

### Category Model (Hierarchical)

```python
Category:
├── id (UUID)
├── name (string)             # "Sausage", "Raw sausage"
├── parent_id (FK, nullable)  # NULL for top-level (maingroup)
└── slug (string)             # URL-friendly name
```

### Future: Batch/Inventory Model (Phase 2)

```python
ProductBatch:
├── id (UUID)
├── product_id (FK)
├── quantity (int)
├── expiry_date (date)
├── received_at (datetime)
└── is_active (bool)
```

**Note:** Batch tracking needs discussion with shop owner. Key questions:
- How are batches tracked in 1C?
- Do we need FIFO (first expiry, first out) for online orders?
- Should expiring-soon products be discounted automatically?

---

## Authentication with Clerk

The authentication flow:

1. **Frontend** handles login/signup via Clerk's SDK
2. **Frontend** gets a JWT token from Clerk
3. **Backend** validates that JWT on protected routes
4. **Backend** extracts user ID from token, creates/updates local user record

Users are required to login (no guest checkout).

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

---

## Open Questions (To verify with shop owner)

1. **Price field:** Use `ext_sales_price` or `baseprice`?
2. **Batch tracking:** How does 1C track product batches/expiry dates?
3. **Quantity field:** Where does stock quantity come from in 1C?
4. **Sync frequency:** Is hourly sync sufficient for stock updates?

---

## Session Log

**2026-01-14:** Initial architecture discussion. Defined product model structure, stock buffer strategy, and authentication flow with Clerk. Added complete 1C field mapping, batch tracking considerations, and dual sync mechanism (browser extension + hourly automated sync).
