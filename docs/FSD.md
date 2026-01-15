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
- Description
- Catalogue/Categories
- Nutritional values
- Price
- Weight
- Barcode
- Quantity (stock)
- Pictures

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

## Open Questions

1. Category hierarchy (flat possibly)

---

## Session Log

**2026-01-14:** Initial architecture discussion. Defined product model structure, stock buffer strategy, and authentication flow with Clerk.
