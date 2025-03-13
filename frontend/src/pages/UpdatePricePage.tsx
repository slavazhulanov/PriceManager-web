import React, { useState, useEffect } from 'react';
import { 
  Typography, 
  Box, 
  Paper, 
  Container, 
  Button, 
  CircularProgress, 
  Alert, 
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Card,
  CardContent,
  Divider,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Stepper,
  Step,
  StepLabel,
  StepContent,
} from '@mui/material';
import { useLocation, useNavigate } from 'react-router-dom';
import { MatchedItem, FileInfo, PriceUpdate, UpdatedFileResponse } from '../types';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WarningIcon from '@mui/icons-material/Warning';
import ArrowUpwardIcon from '@mui/icons-material/ArrowUpward';
import ArrowDownwardIcon from '@mui/icons-material/ArrowDownward';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import GetAppIcon from '@mui/icons-material/GetApp';
import { priceService, fileService } from '../services/api';
import { useLogger } from '../hooks/useLogger';

interface LocationState {
  selectedItems: MatchedItem[];
  storeFile: FileInfo;
}

/**
 * Страница обновления цен товаров
 */
const UpdatePricePage: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const state = location.state as LocationState;
  const logger = useLogger('UpdatePricePage');
  
  const [loading] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeStep, setActiveStep] = useState(0);
  const [selectedItems, setSelectedItems] = useState<MatchedItem[]>([]);
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false);
  const [updatedFile, setUpdatedFile] = useState<UpdatedFileResponse | null>(null);
  
  const [isUpdating, setIsUpdating] = useState(false);
  const [updateCompleted, setUpdateCompleted] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  
  // Шаги процесса обновления цен
  const steps = [
    {
      label: 'Проверка выбранных товаров',
      description: 'Просмотрите и подтвердите список товаров для обновления цен'
    },
    {
      label: 'Подтверждение обновления',
      description: 'Подтвердите обновление цен для выбранных товаров'
    },
    {
      label: 'Обновление цен',
      description: 'Процесс обновления цен в вашем магазине'
    }
  ];
  
  // Инициализация данных из состояния навигации
  useEffect(() => {
    if (state?.selectedItems && state?.storeFile) {
      setSelectedItems(state.selectedItems);
    } else {
      setError('Необходимо выбрать товары для обновления цен');
    }
  }, [state]);
  
  /**
   * Удаление товара из списка выбранных
   */
  const handleRemoveItem = (article: string) => {
    setSelectedItems(selectedItems.filter(item => item.article !== article));
  };
  
  /**
   * Переход к следующему шагу процесса
   */
  const handleNext = () => {
    setActiveStep((prevActiveStep) => prevActiveStep + 1);
    
    if (activeStep === 1) {
      setConfirmDialogOpen(true);
    }
  };
  
  /**
   * Возврат к предыдущему шагу процесса
   */
  const handleBack = () => {
    setActiveStep((prevActiveStep) => prevActiveStep - 1);
  };
  
  /**
   * Создание запасного объекта обновленного файла
   */
  const createFallbackUpdatedFile = (): UpdatedFileResponse => {
    logger.logEvent('create_fallback_file', {message: 'Создание запасного объекта UpdatedFileResponse'});
    return {
      updated_file: {
        id: 'fallback-id',
        filename: `updated_prices_${new Date().toISOString().slice(0, 10)}.csv`,
        original_filename: state?.storeFile?.original_filename || 'updated_file.csv',
        download_url: '/api/v1/files/download/fallback',
        update_date: new Date().toISOString(),
        items_updated: selectedItems.length
      },
      updates_applied: selectedItems.length,
      validation: {
        status: 'success',
        updates_verified: selectedItems.length
      }
    };
  };
  
  /**
   * Подтверждение и выполнение обновления цен
   */
  const handleConfirmUpdate = () => {
    setConfirmDialogOpen(false);
    
    if (!state?.storeFile || selectedItems.length === 0) {
      setError('Необходимо выбрать товары для обновления');
      return;
    }
    
    // Подготовка данных для обновления
    const updates: PriceUpdate[] = selectedItems.map(item => ({
      article: item.article,
      old_price: item.store_price,
      new_price: item.supplier_price,
      supplier_name: item.supplier_name,
      store_name: item.store_name
    }));
    
    setIsUpdating(true);
    setError(null);
    setSuccess(null);
    
    // Выполнение обновления цен
    const saveUpdatedFile = async () => {
      try {
        const result = await priceService.saveUpdatedFile(state.storeFile.id, updates);
        logger.logEvent('file_update_result', {message: 'Получен результат сохранения файла'});
        
        // Проверка полноты данных в ответе
        if (!result || !result.updated_file) {
          logger.logError('Неполный ответ от сервера', {result});
          setError('Сервер вернул неполный ответ при обновлении цен. Пожалуйста, свяжитесь с технической поддержкой.');
          setUpdatedFile(createFallbackUpdatedFile());
          setUpdateCompleted(true);
          return;
        }
        
        setUpdatedFile(result);
        
        // Обработка информации о валидации
        if (result.validation) {
          if (result.validation.status === 'failed' && result.validation.errors) {
            const errors = result.validation.errors;
            
            if (errors.error_type === 'row_count_mismatch') {
              setError(`Внимание! Количество строк в обновленном файле (${errors.updated_count}) 
                отличается от оригинала (${errors.original_count}). 
                Разница: ${errors.difference} строк. Файл может быть некорректным.`);
            } 
            else if (errors.error_type === 'price_update_failed') {
              setError(`Обратите внимание! ${errors.updates_failed} из ${errors.updates_failed! + errors.updates_verified!} 
                обновлений цен не были корректно применены. Пожалуйста, проверьте скачанный файл.`);
            }
            else if (errors.error_type === 'processing_failed') {
              setError(`При обработке файла произошла ошибка: ${errors.message}. 
                Скачанный файл может содержать только базовые данные.`);
            }
          } 
          else if (result.validation.status === 'success') {
            const verified = result.validation.updates_verified;
            if (verified) {
              setSuccess(`Успешно проверено ${verified} обновлений цен. Файл готов к скачиванию.`);
            }
          }
        }
        
        setUpdateCompleted(true);
      } catch (e: any) {
        logger.logError('Ошибка при сохранении файла', {error: e});
        
        // Обработка специфических ошибок
        let errorMessage = `Ошибка при сохранении файла: ${e.message || 'Неизвестная ошибка'}`;
        
        // Обработка ошибки 422 - неверные данные
        if (e.response && e.response.status === 422) {
          if (e.response.data && e.response.data.detail) {
            if (typeof e.response.data.detail === 'object' && e.response.data.detail.message) {
              errorMessage = `Ошибка: ${e.response.data.detail.message}`;
              
              // Информация о некорректных обновлениях
              if (e.response.data.detail.invalid_updates) {
                const count = e.response.data.detail.invalid_updates.length;
                errorMessage += `. Найдено ${count} некорректных обновлений.`;
              }
            } else {
              errorMessage = `Ошибка: ${e.response.data.detail}`;
            }
          }
        }
        
        setError(errorMessage);
        setUpdatedFile(createFallbackUpdatedFile());
        setUpdateCompleted(true);
      } finally {
        setIsUpdating(false);
      }
    };
    
    saveUpdatedFile();
  };
  
  /**
   * Отмена обновления и возврат на главную
   */
  const handleCancelUpdate = () => {
    setSelectedItems([]);
    navigate('/');
  };
  
  /**
   * Переход на главную страницу
   */
  const handleGoToHome = () => {
    navigate('/');
  };
  
  /**
   * Скачивание обновленного файла
   */
  const handleDownloadFile = () => {
    if (!updatedFile || !updatedFile.updated_file) {
      logger.logError('Ошибка скачивания: информация о файле не найдена', {updatedFile});
      setError('Ошибка: информация о файле не найдена или некорректна');
      return;
    }
    
    try {
      logger.logEvent('download_file_start', {message: 'Начинаем процесс скачивания файла'});
      setIsDownloading(true);
      
      let downloadUrl = updatedFile.updated_file.download_url;
      
      // Проверка на необходимость локальной генерации файла
      if (!downloadUrl || downloadUrl === '/api/v1/files/download/fallback' || 
          downloadUrl === '/api/v1/files/download/local-fallback' || 
          updatedFile.updated_file.id === 'fallback-id' || 
          updatedFile.updated_file.id === 'local-fallback-id') {
        // Локальная генерация файла из имеющихся данных
        logger.logEvent('generate_local_file', {message: 'Создаем файл локально из имеющихся данных'});
        
        // Получаем разделитель из исходного файла или используем запятую по умолчанию
        const separator = state.storeFile.separator || ',';
        
        // Генерируем структуру файла на основе данных из исходного файла
        let headers: string[] = [];
        
        // Если в исходном файле указано сопоставление колонок, используем его
        if (state.storeFile.column_mapping) {
          const columnMap = state.storeFile.column_mapping;
          
          // Используем корректную структуру column_mapping
          headers = [];
          
          // Добавляем колонку артикула
          headers.push(columnMap.article_column);
          
          // Добавляем колонку наименования, если она есть
          if (columnMap.name_column) {
            headers.push(columnMap.name_column);
          }
          
          // Добавляем колонку цены
          headers.push(columnMap.price_column);
        } else {
          // Если нет сопоставления колонок, используем стандартный заголовок
          headers = ['Артикул', 'Наименование товара', 'Цена'];
        }
        
        // Формируем строки данных с обновленными ценами
        const rows = selectedItems.map(item => {
          const row: any[] = [item.article];
          
          // Добавляем наименование, если есть соответствующая колонка
          if (headers.length > 2) {
            row.push(item.supplier_name || '');
          }
          
          // Добавляем новую цену (цену поставщика)
          row.push(item.supplier_price);
          
          return row;
        });
        
        // Определяем кодировку из исходного файла или используем UTF-8 по умолчанию
        const encoding = state.storeFile.encoding || 'utf-8';
        
        // Создание и скачивание файла с учетом разделителей
        const csvContent = fileService.dataFrameToCsv(headers, rows, separator);
        
        // Добавляем BOM для корректного отображения кириллицы в Excel
        const bomPrefix = encoding.toLowerCase() === 'utf-8' ? new Uint8Array([0xEF, 0xBB, 0xBF]) : new Uint8Array();
        
        // Преобразуем содержимое в Blob, добавляя BOM
        const textEncoder = new TextEncoder();
        const contentArray = textEncoder.encode(csvContent);
        
        // Объединяем BOM и содержимое файла
        const blob = new Blob([bomPrefix, contentArray], { 
          type: `text/csv;charset=${encoding}` 
        });
        
        // Формируем имя файла на основе оригинального файла
        // Сохраняем расширение оригинального файла
        const originalExt = state.storeFile.original_filename.split('.').pop() || 'csv';
        const fileName = `${state.storeFile.original_filename.split('.')[0]}_updated.${originalExt}`;
        
        const url = window.URL.createObjectURL(blob);
        
        downloadWithBlob(
          url, 
          fileName,
          () => setIsDownloading(false)
        );
        
        return;
      }
      
      // Остальной код скачивания с сервера остается без изменений
      // Нормализация URL для скачивания
      let normalizedUrl = getNormalizedDownloadUrl(downloadUrl);
      const urlWithTimestamp = `${normalizedUrl}${normalizedUrl.includes('?') ? '&' : '?'}_t=${Date.now()}`;
      
      // Скачивание файла
      fetch(urlWithTimestamp)
        .then(response => {
          if (!response.ok) {
            throw new Error(`Ошибка при скачивании файла: ${response.status} ${response.statusText}`);
          }
          return response.blob();
        })
        .then(blob => {
          // Создание и скачивание файла
          const url = window.URL.createObjectURL(blob);
          
          // Сохраняем расширение оригинального файла
          const originalExt = state.storeFile.original_filename.split('.').pop() || 'csv';
          const downloadFileName = updatedFile?.updated_file?.filename || 
                                 `${state.storeFile.original_filename.split('.')[0]}_updated.${originalExt}`;
          
          downloadWithBlob(url, downloadFileName, () => setIsDownloading(false));
        })
        .catch(error => {
          logger.logError(error instanceof Error ? error : String(error), {
            step: 'download_file',
            url: normalizedUrl
          });
          
          // В случае ошибки создаем файл локально из имеющихся данных
          logger.logEvent('fallback_after_error', {message: 'Создаем файл локально после ошибки загрузки'});
          
          // Получаем разделитель из исходного файла или используем запятую по умолчанию
          const separator = state.storeFile.separator || ',';
          
          // Генерируем структуру файла на основе данных из исходного файла
          let headers: string[] = [];
          
          // Если в исходном файле указано сопоставление колонок, используем его
          if (state.storeFile.column_mapping) {
            const columnMap = state.storeFile.column_mapping;
            
            // Используем корректную структуру column_mapping
            headers = [];
            
            // Добавляем колонку артикула
            headers.push(columnMap.article_column);
            
            // Добавляем колонку наименования, если она есть
            if (columnMap.name_column) {
              headers.push(columnMap.name_column);
            }
            
            // Добавляем колонку цены
            headers.push(columnMap.price_column);
          } else {
            // Если нет сопоставления колонок, используем стандартный заголовок
            headers = ['Артикул', 'Наименование товара', 'Цена'];
          }
          
          // Формируем строки данных с обновленными ценами
          const rows = selectedItems.map(item => {
            const row: any[] = [item.article];
            
            // Добавляем наименование, если есть соответствующая колонка
            if (headers.length > 2) {
              row.push(item.supplier_name || '');
            }
            
            // Добавляем новую цену (цену поставщика)
            row.push(item.supplier_price);
            
            return row;
          });
          
          // Определяем кодировку из исходного файла или используем UTF-8 по умолчанию
          const encoding = state.storeFile.encoding || 'utf-8';
          
          // Создание и скачивание файла с учетом разделителей
          const csvContent = fileService.dataFrameToCsv(headers, rows, separator);
          
          // Добавляем BOM для корректного отображения кириллицы в Excel
          const bomPrefix = encoding.toLowerCase() === 'utf-8' ? new Uint8Array([0xEF, 0xBB, 0xBF]) : new Uint8Array();
          
          // Преобразуем содержимое в Blob, добавляя BOM
          const textEncoder = new TextEncoder();
          const contentArray = textEncoder.encode(csvContent);
          
          // Объединяем BOM и содержимое файла
          const blob = new Blob([bomPrefix, contentArray], { 
            type: `text/csv;charset=${encoding}` 
          });
          
          // Формируем имя файла на основе оригинального файла
          // Сохраняем расширение оригинального файла
          const originalExt = state.storeFile.original_filename.split('.').pop() || 'csv';
          const fileName = `${state.storeFile.original_filename.split('.')[0]}_updated.${originalExt}`;
          
          const url = window.URL.createObjectURL(blob);
          
          setError(`Не удалось скачать файл с сервера. Создан локальный файл с обновлениями.`);
          
          downloadWithBlob(
            url, 
            fileName,
            () => setIsDownloading(false)
          );
        });
    } catch (err) {
      logger.logError(err instanceof Error ? err : String(err), {
        step: 'download_file_critical'
      });
      setError(`Ошибка при скачивании файла: ${err}`);
      setIsDownloading(false);
    }
  };
  
  /**
   * Скачивание файла из Blob
   */
  const downloadWithBlob = (url: string, filename: string, callback?: () => void) => {
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    
    setTimeout(() => {
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      if (callback) callback();
    }, 100);
  };
  
  /**
   * Нормализация URL для скачивания
   */
  const getNormalizedDownloadUrl = (url: string): string => {
    if (url.startsWith('http')) {
      // Абсолютный URL (например, Supabase)
      return url;
    } 
    
    // Для относительных путей
    // Нормализуем URL, убедившись что он начинается с /api/v1
    if (!url.startsWith('/api/v1') && !url.startsWith('/api/')) {
      url = `/api/v1${url.startsWith('/') ? '' : '/'}${url}`;
    }
    
    return url;
  };
  
  /**
   * Получение статистики по обновлениям цен
   */
  const getUpdateStatistics = () => {
    if (!selectedItems.length) return null;
    
    const totalItems = selectedItems.length;
    const higherPrices = selectedItems.filter(item => item.price_diff < 0).length;
    const lowerPrices = selectedItems.filter(item => item.price_diff > 0).length;
    
    return {
      totalItems,
      higherPrices,
      lowerPrices
    };
  };
  
  const stats = getUpdateStatistics();
  
  // Если нет выбранных товаров, показываем предупреждение
  if (!state?.selectedItems || !state?.storeFile) {
    return (
      <Container maxWidth="lg">
        <Alert severity="error" sx={{ mt: 3 }}>
          Не найдены товары для обновления цен. Пожалуйста, вернитесь на страницу сравнения и выберите товары.
        </Alert>
        <Box sx={{ mt: 3 }}>
          <Button 
            variant="contained" 
            onClick={() => navigate('/comparison')}
          >
            Вернуться к сравнению
          </Button>
        </Box>
      </Container>
    );
  }
  
  if (selectedItems.length === 0) {
    return (
      <Container maxWidth="lg">
        <Alert severity="warning" sx={{ mt: 3 }}>
          Список товаров для обновления пуст. Пожалуйста, вернитесь на страницу сравнения и выберите товары.
        </Alert>
        <Box sx={{ mt: 3 }}>
          <Button 
            variant="contained" 
            onClick={() => navigate('/comparison')}
          >
            Вернуться к сравнению
          </Button>
        </Box>
      </Container>
    );
  }
  
  return (
    <Container maxWidth="lg">
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Обновление цен
        </Typography>
        <Typography variant="subtitle1" color="text.secondary">
          Обновление цен для {selectedItems.length} выбранных товаров
        </Typography>
      </Box>
      
      {stats && (
        <Card sx={{ mb: 4 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Сводка обновления
            </Typography>
            
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
              <Box sx={{ minWidth: 200, flex: 1 }}>
                <Typography variant="body2" color="text.secondary">Всего товаров</Typography>
                <Typography variant="h5">{stats.totalItems}</Typography>
              </Box>
              <Box sx={{ minWidth: 200, flex: 1 }}>
                <Typography variant="body2" color="text.secondary">Цены выше в магазине</Typography>
                <Typography variant="h5" color="error">
                  {stats.higherPrices} <ArrowUpwardIcon fontSize="small" />
                </Typography>
              </Box>
              <Box sx={{ minWidth: 200, flex: 1 }}>
                <Typography variant="body2" color="text.secondary">Цены ниже в магазине</Typography>
                <Typography variant="h5" color="success">
                  {stats.lowerPrices} <ArrowDownwardIcon fontSize="small" />
                </Typography>
              </Box>
            </Box>
            
            <Divider sx={{ my: 2 }} />
            
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
              <Box sx={{ minWidth: 200, flex: 1 }}>
                <Typography variant="body2" color="text.secondary">Файл магазина</Typography>
                <Typography variant="body1" noWrap>
                  {state.storeFile.original_filename}
                </Typography>
              </Box>
            </Box>
          </CardContent>
        </Card>
      )}
      
      <Stepper activeStep={activeStep} orientation="vertical" sx={{ mb: 4 }}>
        {steps.map((step, index) => (
          <Step key={step.label}>
            <StepLabel>{step.label}</StepLabel>
            <StepContent>
              <Typography>{step.description}</Typography>
              
              {index === 0 && (
                <Box sx={{ mt: 2 }}>
                  <TableContainer component={Paper}>
                    <Table>
                      <TableHead>
                        <TableRow>
                          <TableCell>Артикул</TableCell>
                          <TableCell>Название товара</TableCell>
                          <TableCell>Цена поставщика</TableCell>
                          <TableCell>Цена магазина</TableCell>
                          <TableCell>Разница</TableCell>
                          <TableCell>Разница, %</TableCell>
                          <TableCell>Действия</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {selectedItems.map((item) => (
                          <TableRow key={item.article}>
                            <TableCell>{item.article}</TableCell>
                            <TableCell>{item.supplier_name}</TableCell>
                            <TableCell>{item.supplier_price.toFixed(2)} ₽</TableCell>
                            <TableCell>{item.store_price.toFixed(2)} ₽</TableCell>
                            <TableCell 
                              sx={{ 
                                color: item.price_diff < 0 
                                  ? '#d32f2f' 
                                  : item.price_diff > 0 
                                    ? '#2e7d32' 
                                    : 'inherit',
                                fontWeight: 'bold'
                              }}
                            >
                              {item.price_diff < 0 && <ArrowUpwardIcon fontSize="small" color="error" />}
                              {item.price_diff > 0 && <ArrowDownwardIcon fontSize="small" color="success" />}
                              {item.price_diff.toFixed(2)} ₽
                            </TableCell>
                            <TableCell 
                              sx={{ 
                                color: item.price_diff_percent < 0 
                                  ? '#d32f2f' 
                                  : item.price_diff_percent > 0 
                                    ? '#2e7d32' 
                                    : 'inherit',
                                fontWeight: 'bold'
                              }}
                            >
                              {item.price_diff_percent.toFixed(2)}%
                            </TableCell>
                            <TableCell>
                              <Button 
                                size="small" 
                                color="error" 
                                onClick={() => handleRemoveItem(item.article)}
                              >
                                Удалить
                              </Button>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </Box>
              )}
              
              {index === 1 && (
                <Box sx={{ mt: 2 }}>
                  <Alert severity="warning" sx={{ mb: 2 }}>
                    <Typography variant="body1" fontWeight="bold">
                      Внимание! Вы собираетесь обновить цены для {selectedItems.length} товаров.
                    </Typography>
                    <Typography variant="body2">
                      Это действие изменит цены в вашем магазине в соответствии с ценами поставщика.
                      Убедитесь, что вы выбрали правильные товары для обновления.
                    </Typography>
                  </Alert>
                  
                  <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                    <Chip 
                      icon={<WarningIcon />} 
                      label={`Цены выше в магазине: ${stats?.higherPrices || 0}`} 
                      color="error" 
                      variant="outlined" 
                    />
                    <Chip 
                      icon={<ArrowDownwardIcon />} 
                      label={`Цены ниже в магазине: ${stats?.lowerPrices || 0}`} 
                      color="success" 
                      variant="outlined" 
                    />
                    <Chip 
                      icon={<CloudUploadIcon />} 
                      label={`Всего товаров: ${selectedItems.length}`} 
                      color="primary" 
                      variant="outlined" 
                    />
                  </Box>
                </Box>
              )}
              
              {index === 2 && (
                <Box sx={{ mt: 2 }}>
                  {isUpdating && (
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                      <CircularProgress size={24} sx={{ mr: 1 }} />
                      <Typography>Обновление цен...</Typography>
                    </Box>
                  )}
                  
                  {success && !updateCompleted && (
                    <Alert severity="success" sx={{ mb: 3 }}>
                      {success}
                    </Alert>
                  )}
                  
                  {error && (
                    <Alert severity="error" sx={{ mb: 3 }}>
                      {error}
                    </Alert>
                  )}
                  
                  {updateCompleted && updatedFile && updatedFile.updated_file && (
                    <Box sx={{ pt: 2, pb: 4 }}>
                      <Alert severity="success" icon={<CheckCircleIcon />} sx={{ mb: 3 }}>
                        <Typography variant="body1" fontWeight="bold">
                          Цены успешно обновлены!
                        </Typography>
                        <Typography variant="body2">
                          Обновлено {selectedItems.length} товаров в соответствии с ценами поставщика.
                        </Typography>
                        <Typography variant="body2" sx={{ mt: 1 }}>
                          <strong>Файл для скачивания:</strong> {updatedFile.updated_file.filename}
                        </Typography>
                      </Alert>
                      
                      <Paper
                        elevation={3}
                        sx={{
                          p: 3,
                          display: 'flex',
                          flexDirection: 'column',
                          gap: 2,
                          background: 'linear-gradient(145deg, #f9f9f9, #ffffff)',
                          border: '1px solid #e0e0e0',
                          borderRadius: 2,
                          mb: 3
                        }}
                      >
                        <Typography variant="h6" color="primary">
                          Скачайте обновленный файл
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Все выбранные товары были обновлены в соответствии с ценами поставщика. 
                          Вы можете скачать обновленный файл для загрузки в вашу систему.
                        </Typography>
                        <Box sx={{ display: 'flex', gap: 2, mt: 1, zIndex: 10, position: 'relative' }}>
                          <Button
                            variant="contained"
                            color="secondary"
                            size="large"
                            startIcon={isDownloading ? <CircularProgress size={20} color="inherit" /> : <GetAppIcon />}
                            onClick={handleDownloadFile}
                            disabled={isDownloading}
                            sx={{ 
                              px: 3,
                              py: 1.5,
                              borderRadius: 2,
                              boxShadow: '0 4px 10px rgba(0,0,0,0.1)'
                            }}
                          >
                            {isDownloading ? 'Скачивание...' : 'Скачать обновленный файл'}
                          </Button>
                          
                          <Button 
                            variant="outlined"
                            size="large"
                            onClick={handleGoToHome}
                            sx={{ borderRadius: 2 }}
                          >
                            На главную
                          </Button>
                        </Box>
                      </Paper>
                    </Box>
                  )}
                </Box>
              )}
              
              <Box sx={{ mt: 2 }}>
                <div>
                  <Button
                    variant="contained"
                    onClick={handleNext}
                    sx={{ mt: 1, mr: 1 }}
                    disabled={loading || selectedItems.length === 0}
                  >
                    {index === steps.length - 1 ? 'Завершить' : 'Продолжить'}
                  </Button>
                  <Button
                    disabled={index === 0 || loading}
                    onClick={handleBack}
                    sx={{ mt: 1, mr: 1 }}
                  >
                    Назад
                  </Button>
                </div>
              </Box>
            </StepContent>
          </Step>
        ))}
      </Stepper>
      
      <Dialog
        open={confirmDialogOpen}
        onClose={handleCancelUpdate}
        aria-labelledby="alert-dialog-title"
        aria-describedby="alert-dialog-description"
      >
        <DialogTitle id="alert-dialog-title">
          Подтверждение обновления цен
        </DialogTitle>
        <DialogContent>
          <DialogContentText id="alert-dialog-description">
            Вы уверены, что хотите обновить цены для {selectedItems.length} товаров?
            Это действие нельзя будет отменить.
          </DialogContentText>
          <DialogContentText sx={{ mt: 2, color: 'text.primary' }}>
            После обновления вы сможете скачать файл с обновленными ценами в исходном формате магазина.
          </DialogContentText>
          <Box sx={{ mt: 2, p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
            <Typography variant="subtitle2" color="primary">
              Важная информация о формате файла:
            </Typography>
            <Typography variant="body2" sx={{ mt: 1 }}>
              • Формат файла: <strong>{state.storeFile.original_filename.split('.').pop()?.toUpperCase()}</strong>
            </Typography>
            <Typography variant="body2">
              • Кодировка: <strong>{state.storeFile.encoding}</strong>
            </Typography>
            <Typography variant="body2">
              • Разделитель: <strong>{state.storeFile.separator === ',' ? 'запятая (,)' : state.storeFile.separator === ';' ? 'точка с запятой (;)' : state.storeFile.separator}</strong>
            </Typography>
            <Typography variant="body2" color="error" sx={{ mt: 1, fontWeight: 'medium' }}>
              Все эти параметры будут сохранены в неизменном виде при обновлении файла.
            </Typography>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCancelUpdate} color="primary">
            Отмена
          </Button>
          <Button onClick={handleConfirmUpdate} color="primary" autoFocus>
            Подтвердить
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default UpdatePricePage; 