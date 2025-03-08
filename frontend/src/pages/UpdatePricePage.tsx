import React, { useState } from 'react';
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
  IconButton
} from '@mui/material';
import { useLocation, useNavigate } from 'react-router-dom';
import { MatchedItem, FileInfo, PriceUpdate } from '../types';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WarningIcon from '@mui/icons-material/Warning';
import ArrowUpwardIcon from '@mui/icons-material/ArrowUpward';
import ArrowDownwardIcon from '@mui/icons-material/ArrowDownward';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import GetAppIcon from '@mui/icons-material/GetApp';
import { priceService } from '../services/api';

interface LocationState {
  selectedItems: MatchedItem[];
  storeFile: FileInfo;
}

// Интерфейс для данных о скачиваемом файле
interface UpdatedFileInfo {
  filename: string;
  download_url: string;
  count: number;
}

const UpdatePricePage: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const state = location.state as LocationState;
  
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeStep, setActiveStep] = useState(0);
  const [selectedItems, setSelectedItems] = useState<MatchedItem[]>(
    state?.selectedItems || []
  );
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false);
  // Добавляем состояние для обновленного файла
  const [updatedFile, setUpdatedFile] = useState<UpdatedFileInfo | null>(null);
  
  // Состояние для отслеживания статуса обновления
  const [isUpdating, setIsUpdating] = useState(false);
  const [updateCompleted, setUpdateCompleted] = useState(false);
  const [errorOccurred, setErrorOccurred] = useState(false);
  const [openDialog, setOpenDialog] = useState(false);
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
  
  // Обработчик удаления товара из списка
  const handleRemoveItem = (article: string) => {
    setSelectedItems(selectedItems.filter(item => item.article !== article));
  };
  
  // Обработчик перехода к следующему шагу
  const handleNext = () => {
    setActiveStep((prevActiveStep) => prevActiveStep + 1);
    
    if (activeStep === 1) {
      // Если это шаг подтверждения, открываем диалог
      setConfirmDialogOpen(true);
    }
  };
  
  // Обработчик возврата к предыдущему шагу
  const handleBack = () => {
    setActiveStep((prevActiveStep) => prevActiveStep - 1);
  };
  
  // Обработчик подтверждения обновления цен
  const handleConfirmUpdate = () => {
    console.log('Начало обработки подтверждения обновления');
    setIsUpdating(true);
    setUpdateCompleted(false);
    
    // Закрываем диалог подтверждения
    setConfirmDialogOpen(false);
    
    console.log('Отправка данных для обновления:', {
      storeFile: state.storeFile,
      updates: selectedItems.map(item => ({
        article: item.article,
        old_price: item.store_price,
        new_price: item.supplier_price,
        supplier_name: item.supplier_name,
        store_name: item.store_name
      }))
    });
    
    priceService.saveUpdatedFile(state.storeFile!, selectedItems.map(item => ({
      article: item.article,
      old_price: item.store_price,
      new_price: item.supplier_price,
      supplier_name: item.supplier_name,
      store_name: item.store_name
    })))
      .then(response => {
        console.log('Успешный ответ от сервера:', response);
        setUpdatedFile(response);
        setUpdateCompleted(true);
        setIsUpdating(false);
        setSuccess(true); // Устанавливаем флаг успешного завершения для отображения финального шага
      })
      .catch((error) => {
        console.error('Ошибка при обновлении цен:', error);
        setErrorOccurred(true);
        setIsUpdating(false);
      });
  };
  
  // Обработчик отмены обновления цен
  const handleCancelUpdate = () => {
    setConfirmDialogOpen(false);
  };
  
  // Обработчик возврата к сравнению
  const handleBackToComparison = () => {
    navigate('/comparison');
  };
  
  // Обработчик возврата на главную страницу
  const handleGoToHome = () => {
    navigate('/');
  };
  
  // Функция для скачивания обновленного файла
  const handleDownloadFile = () => {
    if (!updatedFile) {
      console.error('Ошибка скачивания: информация о файле не найдена');
      setError('Ошибка: информация о файле не найдена');
      return;
    }
    
    try {
      console.log('=== Начало процесса скачивания файла ===');
      console.log('Информация о файле:', updatedFile);
      
      setIsDownloading(true);
      
      // Получаем URL для скачивания
      let downloadUrl = updatedFile.download_url;
      
      // Проверяем, является ли это абсолютным URL (например, от Supabase)
      if (downloadUrl.startsWith('http')) {
        console.log('Обнаружен абсолютный URL (вероятно, Supabase):', downloadUrl);
        // Используем URL как есть
      } else if (downloadUrl.includes('/mocks/')) {
        console.log('Обнаружен мок-URL, используем специальный эндпоинт');
        // Если это мок-URL, используем специальный эндпоинт на бэкенде
        const baseApiUrl = process.env.REACT_APP_API_URL || '/api/v1';
        downloadUrl = `${baseApiUrl.replace(/\/api\/v1$/, '')}/api/v1/files/download/sample`;
      } else {
        // Для относительных URL добавляем базовый URL API
        const baseApiUrl = process.env.REACT_APP_API_URL 
          ? process.env.REACT_APP_API_URL.replace(/\/api\/v1$/, '')
          : 'http://localhost:8000';
          
        downloadUrl = `${baseApiUrl}${downloadUrl.startsWith('/') ? '' : '/'}${downloadUrl}`;
      }
      
      console.log('Итоговый URL для скачивания:', downloadUrl);
      console.log('Начало fetch-запроса...');
      
      // Добавляем временную метку для предотвращения кеширования
      const urlWithTimestamp = `${downloadUrl}${downloadUrl.includes('?') ? '&' : '?'}_t=${Date.now()}`;
      
      // Используем fetch для получения содержимого файла
      fetch(urlWithTimestamp)
        .then(response => {
          console.log('Получен ответ от сервера:', {
            status: response.status,
            statusText: response.statusText,
            headers: Array.from(response.headers).reduce((obj, [key, value]) => {
              obj[key] = value;
              return obj;
            }, {} as Record<string, string>),
            type: response.type,
            url: response.url
          });
          
          if (!response.ok) {
            throw new Error(`Ошибка при скачивании файла: ${response.status} ${response.statusText}`);
          }
          
          console.log('Преобразование ответа в blob...');
          return response.blob();
        })
        .then(blob => {
          console.log('Получен blob:', {
            size: blob.size,
            type: blob.type
          });
          
          // Создаем объект Blob с указанием правильного MIME-типа для CSV
          const csvBlob = new Blob([blob], { type: 'text/csv;charset=utf-8' });
          console.log('Создан новый blob с типом text/csv:', {
            size: csvBlob.size,
            type: csvBlob.type
          });
          
          // Создаем URL для blob
          const url = window.URL.createObjectURL(csvBlob);
          console.log('Создан URL для blob:', url);
          
          // Определяем имя файла для скачивания
          let downloadFileName = updatedFile.filename;
          // Если имя файла содержит "mock", используем более подходящее имя
          if (downloadFileName.includes('mock')) {
            downloadFileName = `updated_prices_${new Date().toISOString().slice(0, 10)}.csv`;
          }
          
          // Создаем ссылку для скачивания
          const link = document.createElement('a');
          link.href = url;
          link.setAttribute('download', downloadFileName);
          
          console.log('Создана ссылка для скачивания:', {
            href: link.href,
            download: link.download
          });
          
          // Добавляем, кликаем и удаляем
          document.body.appendChild(link);
          console.log('Запуск скачивания...');
          link.click();
          
          // Удаляем ссылку и освобождаем URL
          setTimeout(() => {
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);
            setIsDownloading(false);
            console.log('Скачивание завершено, ресурсы освобождены');
            console.log('=== Конец процесса скачивания файла ===');
          }, 100);
        })
        .catch(error => {
          console.error('=== Ошибка при скачивании файла ===');
          console.error('Детали ошибки:', error);
          console.error('Информация о запросе:', {
            url: downloadUrl,
            fileInfo: updatedFile
          });
          
          // Если ошибка связана с Supabase, попробуем скачать через бэкенд
          if (downloadUrl.includes('supabase') && typeof error === 'object' && error !== null) {
            console.log('Ошибка в Supabase, пробуем скачать через бэкенд-прокси...');
            
            // Формируем URL для скачивания через бэкенд
            const baseApiUrl = process.env.REACT_APP_API_URL || '/api/v1';
            const proxyUrl = `${baseApiUrl}/files/proxy-download?url=${encodeURIComponent(downloadUrl)}`;
            
            console.log('Повторная попытка через прокси:', proxyUrl);
            
            // Оповещаем пользователя
            setError('Пробуем альтернативный способ скачивания...');
            
            // Создаем ссылку для скачивания через прокси
            const link = document.createElement('a');
            link.href = proxyUrl;
            link.setAttribute('download', updatedFile.filename);
            document.body.appendChild(link);
            link.click();
            
            // Удаляем ссылку
            setTimeout(() => {
              document.body.removeChild(link);
              setIsDownloading(false);
            }, 100);
            
            return;
          }
          
          setError(`Ошибка при скачивании файла: ${error.message}`);
          setIsDownloading(false);
          console.log('=== Процесс скачивания прерван из-за ошибки ===');
        });
    } catch (err) {
      console.error('=== Критическая ошибка при скачивании файла ===');
      console.error('Необработанное исключение:', err);
      console.error('Стек вызовов:', new Error().stack);
      
      setError(`Ошибка при скачивании файла: ${err}`);
      setIsDownloading(false);
      console.log('=== Процесс скачивания прерван из-за критической ошибки ===');
    }
  };
  
  // Расчет статистики обновления
  const getUpdateStatistics = () => {
    if (!selectedItems.length) return null;
    
    const totalItems = selectedItems.length;
    // Удаляем расчет суммарной и средней разницы
    //const totalDiff = selectedItems.reduce((sum, item) => sum + item.price_diff, 0);
    //const averageDiffPercent = selectedItems.reduce((sum, item) => sum + Math.abs(item.price_diff_percent), 0) / totalItems;
    
    // Количество товаров с ценой выше в магазине
    const higherPrices = selectedItems.filter(item => item.price_diff < 0).length;
    // Количество товаров с ценой ниже в магазине
    const lowerPrices = selectedItems.filter(item => item.price_diff > 0).length;
    
    return {
      totalItems,
      //totalDiff,
      //averageDiffPercent,
      higherPrices,
      lowerPrices
    };
  };
  
  const stats = getUpdateStatistics();
  
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
      
      {/* Статистика обновления */}
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
      
      {/* Stepper */}
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
                  
                  {errorOccurred && (
                    <Alert severity="error" sx={{ mb: 2 }}>
                      <Typography variant="body1" fontWeight="bold">
                        Произошла ошибка при обновлении цен
                      </Typography>
                      <Typography variant="body2">
                        Пожалуйста, попробуйте еще раз или обратитесь в службу поддержки.
                      </Typography>
                    </Alert>
                  )}
                  
                  {updateCompleted && updatedFile && (
                    <Box sx={{ pt: 2, pb: 4 }}>
                      <Alert severity="success" icon={<CheckCircleIcon />} sx={{ mb: 3 }}>
                        <Typography variant="body1" fontWeight="bold">
                          Цены успешно обновлены!
                        </Typography>
                        <Typography variant="body2">
                          Обновлено {selectedItems.length} товаров в соответствии с ценами поставщика.
                        </Typography>
                        <Typography variant="body2" sx={{ mt: 1 }}>
                          <strong>Файл для скачивания:</strong> {updatedFile.filename}
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
      
      {/* Диалог подтверждения */}
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