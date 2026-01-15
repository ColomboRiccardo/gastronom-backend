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

### Data Available from 1C Scraper

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

### Source of Truth

The **physical shop (1C) is the master**. The ecommerce database follows/mirrors it.

---

## Stock Management Strategy

To handle the problem of concurrent purchases (online vs in-store), we use a **stock buffer** approach:

```
available_online = stock_quantity - stock_buffer
```

- Default buffer: **5 items** (configurable)
- This ensures the physical shop always has items to display
- Avoids the complexity of real-time inventory sync

---

## Products Module Design

Based on what we can scrape from 1C, here's the product model structure:

```python
Product:
├── id (UUID)              # Internal ID for ecommerce
├── barcode (string)       # External ID from 1C - used for sync matching
├── name (string)
├── description (text)
├── price (decimal)
├── weight (decimal)       # In grams
├── stock_quantity (int)   # Raw quantity from 1C
├── stock_buffer (int)     # Default 10, configurable per product?
├── nutritional_values (int) #kcal
├── total_carbs (int) #grams
├── total_fat (int) #grams
├── total_proteins (int) #grams
├── total_sugar (int) #grams
├── category_id (FK)
├── images (relation)
├── is_available (bool)    # Can be manually disabled
├── created_at / updated_at
└── last_synced_at         # When scraper last updated this product
```

### Key Decisions to Make

#### 1. Stock Buffer
- global default + per-product override if needed

## Authentication with Clerk

The authentication flow:

1. **Frontend** handles login/signup via Clerk's SDK
2. **Frontend** gets a JWT token from Clerk
3. **Backend** validates that JWT on protected routes
4. **Backend** extracts user ID from token, creates/updates local user record

Users are required to login

---

## Scraper Architecture

Three options were considered:

**Option A: Scraper writes directly to DB**
- Scraper has its own DB connection
- Simple, but harder to validate data / handle errors

**Option B: Scraper calls API endpoints** *(Chosen)*
- Scraper uses the same API as the frontend
- Better validation, logging, but more overhead

**Option C: Scraper pushes to a queue, backend processes**
- More complex, but handles failures gracefully
- Good if scraper runs frequently

Decision: **Option B** - Scraper will call backend API endpoints.

---

## Session Log

**2026-01-14:** Initial architecture discussion. Defined product model structure, stock buffer strategy, and authentication flow with Clerk.
