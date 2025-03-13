from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class FileType(str, Enum):
    SUPPLIER = "supplier"
    STORE = "store"

class ColumnMapping(BaseModel):
    article_column: str
    price_column: str
    name_column: Optional[str] = None
    additional_columns: Optional[Dict[str, str]] = None

class FileInfo(BaseModel):
    id: Optional[str] = None
    original_filename: str
    stored_filename: str
    file_type: FileType
    encoding: str = "utf-8"
    separator: str = ","
    file_url: Optional[str] = None
    column_mapping: Optional[ColumnMapping] = None
    
class PriceUpdate(BaseModel):
    article: str
    old_price: float
    new_price: float
    supplier_name: Optional[str] = None
    store_name: Optional[str] = None
    
class MatchedItem(BaseModel):
    article: str
    supplier_price: float
    store_price: float
    price_diff: float
    price_diff_percent: float
    supplier_name: Optional[str] = None
    store_name: Optional[str] = None

class MissingInStoreItem(BaseModel):
    article: str
    supplier_price: float
    supplier_name: Optional[str] = None

class MissingInSupplierItem(BaseModel):
    article: str
    store_price: float
    store_name: Optional[str] = None

class ComparisonResult(BaseModel):
    matches: List[Dict[str, Any]]
    missing_in_store: List[Dict[str, Any]]
    missing_in_supplier: List[Dict[str, Any]]
    # Добавляем дополнительные поля для совместимости с фронтендом
    matches_data: Optional[List[MatchedItem]] = None
    total_items: Optional[int] = None
    items_only_in_file1: Optional[int] = None
    items_only_in_file2: Optional[int] = None
    mismatches: Optional[int] = None
    preview_data: Optional[List[Dict[str, Any]]] = None
    column_mapping: Optional[Dict[str, str]] = None 