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
    column_mapping: Optional[ColumnMapping] = None
    
class PriceUpdate(BaseModel):
    article: str
    old_price: float
    new_price: float
    supplier_name: Optional[str] = None
    store_name: Optional[str] = None
    
class ComparisonResult(BaseModel):
    matches: List[Dict[str, Any]]
    missing_in_store: List[Dict[str, Any]]
    missing_in_supplier: List[Dict[str, Any]] 