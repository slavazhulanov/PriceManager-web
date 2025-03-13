/**
 * Типы файлов для загрузки
 */
export type FileType = 'supplier' | 'store';

// Константы для типов файлов
export const FileTypes = {
  SUPPLIER: 'supplier' as FileType,
  STORE: 'store' as FileType
};

/**
 * Информация о загруженном файле
 */
export interface FileInfo {
  id: string;
  filename: string;
  original_filename: string;
  stored_filename?: string; // Имя файла в хранилище
  file_size: number;
  file_type: FileType;
  upload_date: string;
  columns?: string[];
  column_mapping?: ColumnMapping;
  encoding?: string;
  separator?: string;
  content_type?: string;
  download_url?: string;
  preview_data?: Array<Record<string, any>>;
}

/**
 * Результаты сравнения файлов
 */
export interface ComparisonResult {
  matches: number;
  mismatches: number;
  items_only_in_file1: number;
  items_only_in_file2: number;
  total_items: number;
  preview_data: PriceComparison[];
  column_mapping: {
    identifier: string;
    value: string;
  };
  matches_data?: MatchedItem[];
  missing_in_store?: MissingInStoreItem[];
  missing_in_supplier?: MissingInSupplierItem[];
}

/**
 * Результат сравнения цен
 */
export interface PriceComparison {
  id: string;
  identifier: string;
  name?: string;
  current_price: number | null;
  supplier_price: number | null;
  price_difference: number | null;
  price_difference_percent: number | null;
  status: 'match' | 'mismatch' | 'only_in_file1' | 'only_in_file2';
  columns: Record<string, any>;
}

/**
 * Обновление цены
 */
export interface PriceUpdate {
  id?: string; // Идентификатор товара (опционально)
  article: string; // Артикул товара
  old_price: number | null; // Старая цена
  new_price: number | null; // Новая цена
  update_reason?: string; // Причина обновления
  supplier_name?: string; // Название поставщика
  store_name?: string; // Название магазина
}

/**
 * Информация об обновленном файле
 */
export interface UpdatedFileInfo {
  id: string;
  filename: string;
  original_filename: string;
  download_url: string;
  update_date: string;
  items_updated: number;
}

/**
 * Ответ от API при обновлении файла
 */
export interface UpdatedFileResponse {
  updated_file: UpdatedFileInfo;
  updates_applied: number;
  validation?: {
    status: 'success' | 'failed';
    errors?: ValidationErrorDetails;
    updates_verified?: number;
  };
}

/**
 * Уровни логирования
 */
export type LogLevel = 'debug' | 'info' | 'warn' | 'error';

/**
 * Структура лога
 */
export interface LogEntry {
  timestamp: number;
  level: LogLevel;
  message: string;
  context?: Record<string, any>;
  source?: string;
  userId?: string;
  sessionId?: string;
  path?: string;
  component?: string;
  action?: string;
}

export interface ColumnMapping {
  article_column: string;
  price_column: string;
  name_column?: string;
  additional_columns?: Record<string, string>;
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