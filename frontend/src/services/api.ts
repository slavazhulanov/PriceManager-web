import axios from 'axios';
import { 
  FileInfo, 
  FileType, 
  ComparisonResult, 
  PriceUpdate,
  UpdatedFileResponse
} from '../types';

// Определение базового URL API в зависимости от окружения
const getApiUrl = () => {
  // В продакшн на Vercel мы используем API с префиксом /api
  if (process.env.NODE_ENV === 'production') {
    return '/api/v1';
  }
  // В локальной разработке используем полный URL
  return 'http://localhost:8000/api/v1';
};

const API_URL = getApiUrl();

// Создаем экземпляр axios с базовым URL
const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  // Устанавливаем таймаут для запросов
  timeout: 30000, // 30 секунд
});

// Обработчик ошибок API
const handleApiError = (error: any) => {
  if (error.response) {
    // Сервер вернул ответ со статусом отличным от 2xx
    console.error('API Error Response:', error.response.data);
    console.error('Status:', error.response.status);
    return Promise.reject(
      error.response.data?.detail || 
      error.response.data?.message || 
      `Ошибка сервера (${error.response.status})`
    );
  } else if (error.request) {
    // Запрос был отправлен, но ответ не получен
    console.error('API Request Error:', error.request);
    return Promise.reject('Не удалось получить ответ от сервера. Проверьте подключение к сети.');
  } else {
    // Произошла ошибка при настройке запроса
    console.error('API Error:', error.message);
    return Promise.reject(error.message || 'Произошла неизвестная ошибка');
  }
};

// Добавляем перехватчики ответов
api.interceptors.response.use(
  (response) => response,
  (error) => handleApiError(error)
);

// Сервис для работы с файлами
export const fileService = {
  // Загрузка файла
  async uploadFile(file: File, fileType: FileType): Promise<FileInfo> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('file_type', fileType);
    
    const response = await api.post('files/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    
    return response.data;
  },
  
  // Получение URL для прямой загрузки в Supabase
  async getUploadUrl(fileName: string, fileType: FileType): Promise<{ uploadUrl: string, fileInfo: any }> {
    const response = await api.post('files/upload_url', {
      fileName,
      fileType
    });
    
    return response.data;
  },
  
  // Прямая загрузка файла в Supabase по полученному URL
  async uploadToSupabase(file: File, uploadUrl: string): Promise<boolean> {
    try {
      // Используем fetch вместо axios для загрузки напрямую
      const response = await fetch(uploadUrl, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/octet-stream',
        },
        body: file
      });
      
      if (!response.ok) {
        console.error('Ошибка при загрузке в Supabase:', response.statusText);
        return false;
      }
      
      return true;
    } catch (error) {
      console.error('Ошибка при загрузке в Supabase:', error);
      return false;
    }
  },
  
  // Регистрация файла после прямой загрузки в Supabase
  async registerUploadedFile(fileInfo: any): Promise<FileInfo> {
    const response = await api.post('files/register', {
      fileInfo
    });
    
    return response.data;
  },
  
  // Получение списка колонок из файла
  async getColumns(filename: string, encoding?: string, separator?: string): Promise<string[]> {
    const params: any = {};
    if (encoding) params.encoding = encoding;
    if (separator) params.separator = separator;
    
    const response = await api.get(`files/columns/${filename}`, { params });
    return response.data;
  },
  
  // Сохранение сопоставления колонок
  async saveColumnMapping(fileInfo: FileInfo): Promise<FileInfo> {
    const response = await api.post('files/mapping', fileInfo);
    return response.data;
  },
};

// Сервис для работы со сравнением прайс-листов
export const comparisonService = {
  // Сравнение прайс-листов
  async compareFiles(supplierFile: FileInfo, storeFile: FileInfo): Promise<ComparisonResult> {
    const response = await api.post('comparison/compare', {
      supplier_file: supplierFile,
      store_file: storeFile,
    });
    
    return response.data;
  },
};

// Сервис для работы с обновлением цен
export const priceService = {
  // Загрузка файла
  async uploadFile(file: File, fileType: FileType): Promise<FileInfo> {
    return fileService.uploadFile(file, fileType);
  },
  
  // Получение списка колонок из файла
  async getColumns(filename: string, encoding?: string, separator?: string): Promise<string[]> {
    return fileService.getColumns(filename, encoding, separator);
  },
  
  // Сохранение маппинга колонок
  async saveColumnMapping(fileInfo: FileInfo): Promise<FileInfo> {
    return fileService.saveColumnMapping(fileInfo);
  },

  // Сравнение файлов
  async compareFiles(supplierFile: FileInfo, storeFile: FileInfo): Promise<ComparisonResult> {
    return comparisonService.compareFiles(supplierFile, storeFile);
  },

  // Обновление цен
  async updatePrices(updates: PriceUpdate[], storeFile: FileInfo): Promise<PriceUpdate[]> {
    const response = await api.post('prices/update', {
      updates,
      store_file: storeFile,
    });

    return response.data;
  },
  
  // Сохранение обновленного файла
  async saveUpdatedFile(storeFile: FileInfo, updates: PriceUpdate[]): Promise<UpdatedFileResponse> {
    // Добавляем в запрос информацию о необходимости сохранения оригинального формата файла
    const response = await api.post('prices/save', {
      store_file: storeFile,
      updates,
      preserve_format: true, // Флаг для явного указания необходимости сохранения формата
      format_info: {
        encoding: storeFile.encoding,
        separator: storeFile.separator,
        file_extension: storeFile.original_filename.split('.').pop() || 'xlsx'
      }
    });
    
    return response.data;
  },
}; 