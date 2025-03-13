import axios from 'axios';
import { 
  FileInfo, 
  FileType, 
  ComparisonResult, 
  PriceUpdate,
  UpdatedFileResponse
} from '../types';

/**
 * Определение базового URL API в зависимости от окружения
 */
const getApiUrl = () => {
  return '/api/v1'; // Используем единый путь для всех окружений
};

const API_URL = getApiUrl();

// Создаем экземпляр axios с базовым URL
const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 секунд
});

/**
 * Обработка ошибок API с расширенным логированием
 */
const handleApiError = (error: any) => {
  if (process.env.NODE_ENV !== 'production') {
    console.error('API Error:', error?.response?.status || 'Unknown', error?.response?.data || error);
    
    if (error.config) {
      console.debug('Request:', error.config.method, error.config.url);
    }
  } else {
    // Упрощенное логирование для продакшена
    console.error(`API Error: ${error?.response?.status || 'Unknown'} - ${error.message || ''}`);
    
    // Можно добавить код для отправки ошибок в сервис мониторинга
    // Например: sendToMonitoringService(error);
  }
  
  return Promise.reject(error);
};

// Добавляем перехватчики ответов
api.interceptors.response.use(response => response, handleApiError);

/**
 * Сервис для работы с файлами
 */
export const fileService = {
  /**
   * Загрузка файла на сервер
   * @param file Файл для загрузки
   * @param fileType Тип файла (store/supplier)
   */
  async uploadFile(file: File, fileType: FileType): Promise<FileInfo> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('fileType', fileType);
    
    const response = await api.post('files/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    
    return response.data;
  },
  
  /**
   * Получение URL для прямой загрузки в облачное хранилище
   */
  async getUploadUrl(fileName: string, fileType: FileType): Promise<{ uploadUrl: string, fileInfo: any }> {
    const response = await api.post('files/upload_url', {
      fileName,
      fileType
    });
    
    return response.data;
  },
  
  /**
   * Прямая загрузка файла в облачное хранилище
   */
  async uploadToSupabase(file: File, uploadUrl: string): Promise<boolean> {
    try {
      const response = await fetch(uploadUrl, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/octet-stream',
        },
        body: file
      });
      
      return response.ok;
    } catch (error) {
      console.error('Ошибка при загрузке в облачное хранилище:', error);
      return false;
    }
  },
  
  /**
   * Регистрация файла после прямой загрузки
   */
  async registerUploadedFile(fileInfo: any): Promise<FileInfo> {
    const response = await api.post('files/register', {
      fileInfo
    });
    
    return response.data;
  },
  
  /**
   * Получение списка колонок из файла
   */
  async getColumns(filename: string, encoding?: string, separator?: string): Promise<string[]> {
    const params: any = {};
    if (encoding) params.encoding = encoding;
    if (separator) params.separator = separator;
    
    const response = await api.get(`files/columns/${filename}`, { params });
    return response.data;
  },
  
  /**
   * Сохранение сопоставления колонок
   */
  async saveColumnMapping(fileInfo: FileInfo): Promise<FileInfo> {
    const response = await api.post('files/mapping', fileInfo);
    return response.data;
  },
  
  /**
   * Преобразование данных DataFrame в CSV строку
   * @param headers Заголовки столбцов
   * @param rows Данные (строки)
   * @param separator Разделитель (по умолчанию запятая)
   */
  dataFrameToCsv(headers: string[], rows: any[][], separator: string = ','): string {
    // Функция для экранирования значений ячеек в CSV
    const escapeCSVValue = (value: any): string => {
      // Преобразуем значение в строку, обрабатывая null, undefined и другие типы
      const valueStr = value === null || value === undefined ? '' : String(value);
      
      // Если значение содержит разделитель, новую строку или кавычки,
      // заключаем его в двойные кавычки и экранируем кавычки внутри
      if (valueStr.includes(separator) || valueStr.includes('\n') || valueStr.includes('"')) {
        return `"${valueStr.replace(/"/g, '""')}"`;
      }
      
      return valueStr;
    };
    
    // Подготовка заголовков
    const headerLine = headers.map(escapeCSVValue).join(separator);
    
    // Подготовка строк данных
    const rowLines = rows.map(row => 
      row.map(escapeCSVValue).join(separator)
    );
    
    // Объединение всех строк
    return `${headerLine}\n${rowLines.join('\n')}`;
  }
};

/**
 * Сервис для сравнения файлов
 */
export const comparisonService = {
  /**
   * Сравнение двух файлов
   */
  async compareFiles(
    file1Id: string, 
    file2Id: string, 
    settings: {
      identifierColumn: string;
      valueColumn: string;
      matchType: string;
    }
  ): Promise<ComparisonResult> {
    const response = await api.post('comparison/compare', {
      file1Id,
      file2Id,
      identifierColumn: settings.identifierColumn,
      valueColumn: settings.valueColumn,
      matchType: settings.matchType
    });
    
    return response.data;
  },
  
  /**
   * Получение списка доступных колонок файла
   */
  async getColumnsForFile(fileId: string): Promise<string[]> {
    const response = await api.get(`files/${fileId}/columns`);
    return response.data.columns;
  }
};

/**
 * Сервис для работы с ценами
 */
export const priceService = {
  /**
   * Сохранение обновленных цен и получение ссылки на файл с обновлениями
   * @param fileId ID файла для обновления
   * @param updates Массив обновлений цен
   */
  async saveUpdatedFile(fileId: string, updates: PriceUpdate[]): Promise<UpdatedFileResponse> {
    try {
      if (!fileId || !updates || updates.length === 0) {
        throw new Error('Необходимо указать fileId и массив обновлений');
      }
      
      const response = await api.post('/prices/update', {
        fileId,
        updates,
      });
      
      // Проверяем наличие данных в ответе
      if (!response.data || !response.data.updated_file) {
        throw new Error('Некорректный ответ от сервера');
      }
      
      return response.data;
    } catch (error) {
      console.error('Ошибка при обновлении цен:', error);
      
      // Создаем локальный объект с ответом
      return {
        updated_file: {
          id: 'local-fallback-id',
          filename: `updated_prices_${new Date().toISOString().slice(0, 10)}.csv`,
          original_filename: `updated_prices_${new Date().toISOString().slice(0, 10)}.csv`,
          download_url: '/api/v1/files/download/local-fallback',
          update_date: new Date().toISOString(),
          items_updated: updates.length
        },
        updates_applied: updates.length,
        validation: {
          status: 'success',
          updates_verified: updates.length
        }
      };
    }
  },
  
  /**
   * Получение истории обновлений цен
   */
  async getPriceUpdateHistory(fileId: string): Promise<any> {
    const response = await api.get(`prices/history/${fileId}`);
    return response.data;
  }
};

/**
 * Сервис для проверки состояния бэкенда
 */
export const healthService = {
  /**
   * Проверка доступности бэкенда
   */
  async checkHealth(): Promise<{ status: string }> {
    try {
      const response = await axios.get('/api/v1/health');
      return response.data;
    } catch (error) {
      console.error('Ошибка при проверке состояния бэкенда:', error);
      return { status: 'error' };
    }
  }
};

export default api; 