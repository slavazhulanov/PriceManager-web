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

export interface ValidationErrorDetails {
  error_type: string;
  message?: string;
  original_count?: number;
  updated_count?: number;
  difference?: number;
  updates_verified?: number;
  updates_failed?: number;
  failed_examples?: Array<any>;
}

export interface ValidationResult {
  status: 'success' | 'failed';
  errors?: ValidationErrorDetails;
  original_row_count?: number;
  updated_row_count?: number;
  updates_verified?: number;
}

export interface UpdatedFileResponse {
  filename: string;
  download_url: string;
  count: number;
  success?: boolean;
  message?: string;
  validation?: ValidationResult;
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