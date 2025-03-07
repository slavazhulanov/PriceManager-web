export enum FileType {
  SUPPLIER = "supplier",
  STORE = "store"
}

export interface ColumnMapping {
  article_column: string;
  price_column: string;
  name_column?: string;
  additional_columns?: Record<string, string>;
}

export interface FileInfo {
  id?: string;
  original_filename: string;
  stored_filename: string;
  file_type: FileType;
  encoding: string;
  separator: string;
  column_mapping?: ColumnMapping;
}

export interface PriceUpdate {
  article: string;
  old_price: number;
  new_price: number;
  supplier_name?: string;
  store_name?: string;
}

export interface MatchedItem {
  article: string;
  supplier_price: number;
  store_price: number;
  price_diff: number;
  price_diff_percent: number;
  supplier_name?: string;
  store_name?: string;
}

export interface MissingInStoreItem {
  article: string;
  supplier_price: number;
  supplier_name?: string;
}

export interface MissingInSupplierItem {
  article: string;
  store_price: number;
  store_name?: string;
}

export interface ComparisonResult {
  matches: MatchedItem[];
  missing_in_store: MissingInStoreItem[];
  missing_in_supplier: MissingInSupplierItem[];
} 