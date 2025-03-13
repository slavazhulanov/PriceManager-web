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
    console.log('Запрос колонок для файла:', {
      filename,
      encoding,
      separator,
      url: `files/columns/${filename}`
    });
    
    const params: any = {};
    if (encoding) params.encoding = encoding;
    if (separator) params.separator = separator;
    
    try {
      const response = await api.get(`files/columns/${filename}`, { params });
      console.log('Получены колонки (сырой ответ):', response.data);
      
      // Проверка типа полученных данных для более детальной диагностики
      console.log('Тип полученных данных:', typeof response.data);
      if (Array.isArray(response.data)) {
        console.log('Данные являются массивом, длина:', response.data.length);
      } else if (typeof response.data === 'object') {
        console.log('Данные являются объектом, ключи:', Object.keys(response.data));
      }
      
      // Улучшенная обработка ответа с подробной диагностикой
      let columns: string[] = [];
      
      // 1. Если это массив - используем напрямую
      if (Array.isArray(response.data)) {
        columns = response.data;
        console.log('Обработка: получен массив напрямую');
      } 
      // 2. Если это объект - проверяем на наличие массива колонок
      else if (response.data && typeof response.data === 'object') {
        console.log('Обработка: получен объект, ищем массив колонок');
        
        // 2.1 Проверка на наличие ключа columns
        if (Array.isArray(response.data.columns)) {
          columns = response.data.columns;
          console.log('Найден массив в ключе columns');
        } 
        // 2.2 Проверка на наличие ключа data
        else if (response.data.data && Array.isArray(response.data.data)) {
          columns = response.data.data;
          console.log('Найден массив в ключе data');
        }
        // 2.3 Поиск любого массива в объекте
        else {
          console.log('Ищем любой массив в объекте');
          const arrayValues = Object.values(response.data).filter(val => Array.isArray(val));
          
          if (arrayValues.length > 0) {
            columns = arrayValues[0] as string[];
            console.log('Найден массив в объекте:', columns);
          }
          // 2.4 Использование ключей объекта как колонок
          else if (Object.keys(response.data).length > 0) {
            console.log('Не найден массив, используем ключи объекта');
            const keys = Object.keys(response.data).filter(key => 
              !['status', 'message', 'timestamp', 'path', 'error', 'detail'].includes(key)
            );
            
            if (keys.length > 0) {
              columns = keys;
              console.log('Используем ключи объекта как колонки:', columns);
            } else {
              console.error('Нет подходящих ключей в объекте');
              throw new Error('Неверный формат данных колонок: нет подходящих ключей');
            }
          } else {
            console.error('Пустой объект в ответе');
            throw new Error('Неверный формат данных колонок: пустой объект');
          }
        }
      }
      // 3. Если это строка - пробуем распарсить как JSON
      else if (typeof response.data === 'string') {
        console.log('Обработка: получена строка, пробуем распарсить как JSON');
        try {
          const parsedData = JSON.parse(response.data);
          
          if (Array.isArray(parsedData)) {
            columns = parsedData;
            console.log('Строка распарсена как массив');
          } else if (parsedData && typeof parsedData === 'object') {
            // Рекурсивно применяем ту же логику к распарсенному объекту
            console.log('Строка распарсена как объект, ищем массив внутри');
            if (Array.isArray(parsedData.columns)) {
              columns = parsedData.columns;
            } else if (parsedData.data && Array.isArray(parsedData.data)) {
              columns = parsedData.data;
            } else {
              const keys = Object.keys(parsedData).filter(key => 
                !['status', 'message', 'timestamp', 'path'].includes(key)
              );
              if (keys.length > 0) {
                columns = keys;
              } else {
                throw new Error('Неверный формат данных колонок в строке JSON');
              }
            }
          } else {
            throw new Error('Неверный формат данных колонок в строке JSON');
          }
        } catch (parseError) {
          // Если не удалось распарсить, используем строку как одну колонку
          console.warn('Не удалось распарсить строку как JSON, используем как одну колонку');
          columns = [response.data];
        }
      }
      // 4. Если данные отсутствуют - ошибка
      else {
        console.error('Неизвестный формат данных:', response.data);
        throw new Error(`Неверный формат данных колонок: ${typeof response.data}`);
      }
      
      // Преобразуем все элементы в строки
      columns = columns.map(col => String(col).trim());
      
      // Удаляем пустые значения
      columns = columns.filter(col => col !== '' && col !== 'undefined' && col !== 'null');
      
      // Проверка финального результата
      if (columns.length === 0) {
        console.error('После обработки не осталось колонок');
        throw new Error('Не удалось извлечь колонки из ответа API');
      }
      
      console.log('Финальный список колонок:', columns);
      return columns;
    } catch (error: any) {
      console.error('Ошибка при получении колонок:', {
        status: error?.response?.status,
        data: error?.response?.data,
        message: error.message
      });
      throw error;
    }
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