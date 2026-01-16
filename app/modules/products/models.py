## Product:
#  id (UUID)                                    # Internal ID for ecommerce
#  external_id (int)                            # prodid from 1C - primary sync key
#  barcode (string)                             # EAN barcode - secondary sync key
#  lackmann_number (string)                     # extartnr - lackmann's article number
#  name (string)                                # shorttext
#  name_display (string)                        # ext_print_productname (optional)
#  ingredients (text)                           # ext_zutaten
#  packing_type (string)                        # Box, Single, etc.
## Units & Pricing
#  selling_unit (enum)                          # How customer orders: "pcs" | "kg" | "g"
#  pricing_unit (enum)                          # How price is calculated: "pcs" | "kg"
#  price_per_pricing_unit_synced (decimal)      # From 1C
#  price_per_pricing_unit_override (decimal)    # Owner override (nullable)
#  weight_per_unit_grams (int, nullable)        # For piece-based: grams per piece
#  average_weight_grams (int, nullable)         # For discrete weight-priced (fish): avg weight
## Stock (from 1C)
#  stock_amount_synced (decimal)                # Raw amount from 1C (pieces or kg)
#  stock_amount_override (decimal)              # Owner override (nullable)
#  stock_buffer (decimal)                       # Default 5, per-product override
## Nutritional (per 100g)
#  kcal (int)
#  kilojoules (int)
#  proteins (decimal)
#  fat (decimal)
#  saturated_fat (decimal)
#  carbs (decimal)
#  sugar (decimal)
#  salt (decimal)
## Categories
#  category_id (FK)                             # Points to leaf category (see Category model)
## Relations
#  images (relation)
## Status
#  is_available (bool)                          # Can be manually disabled by owner
#  created_at (datetime)
#  updated_at (datetime)
#  last_synced_at (datetime)                    # When scraper last updated this

import uuid
from sqlalchemy import String, ForeignKey, Integer, Text, Enum, Float, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

class Product(Base):
    __tablename__ ="products"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_id: Mapped[int] = mapped_column(Integer, nullable=False)
    barcode: Mapped[str] = mapped_column(String(255), nullable=False)
    lackmann_number: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    name_display:  Mapped[str] = mapped_column(String(255), nullable=False)
    ingredients: Mapped[str] = mapped_column(Text)
    packing_type: Mapped[str] = mapped_column(String(255))
    