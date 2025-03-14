import React, { useState, useEffect, useCallback } from 'react';
import { 
  Typography, 
  Box, 
  Paper, 
  Stepper, 
  Step, 
  StepLabel, 
  Button, 
  Container, 
  Grid, 
  Divider,
  Alert,
  Card,
  CardContent,
  CircularProgress
} from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import SettingsIcon from '@mui/icons-material/Settings';
import CompareArrowsIcon from '@mui/icons-material/CompareArrows';
import BuildIcon from '@mui/icons-material/Build';
import { useNavigate } from 'react-router-dom';
import FileDropzone from '../components/file/FileDropzone';
import ColumnSelector from '../components/file/ColumnSelector';
import { 
  FileInfo, 
  FileTypes,
  ColumnMapping 
} from '../types';
import { fileService } from '../services/api';
import axios from 'axios';

// Шаги загрузки файлов
const steps = [
  {
    label: 'Загрузка файлов',
    description: 'Загрузите файлы прайс-листов для сравнения',
    icon: <CloudUploadIcon />
  },
  {
    label: 'Настройка колонок',
    description: 'Укажите, какие колонки содержат артикулы и цены',
    icon: <SettingsIcon />
  },
  {
    label: 'Готово к сравнению',
    description: 'Перейдите к сравнению цен',
    icon: <CompareArrowsIcon />
  },
];

const FileUploadPage: React.FC = () => {
  const navigate = useNavigate();
  const [activeStep, setActiveStep] = useState(0);
  const [supplierFile, setSupplierFile] = useState<FileInfo | null>(null);
  const [storeFile, setStoreFile] = useState<FileInfo | null>(null);
  const [supplierColumns, setSupplierColumns] = useState<string[]>([]);
  const [storeColumns, setStoreColumns] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [columnsLoading, setColumnsLoading] = useState(false);
  
  // Загрузка колонок для файлов
  const loadColumns = useCallback(async () => {
    console.log('Начало загрузки колонок', {
      supplierFile,
      storeFile,
      supplierColumns,
      storeColumns,
      columnsLoading
    });
    
    if (columnsLoading) {
      console.log('Загрузка колонок уже выполняется');
      return;
    }
    
    // Проверяем, нужно ли вообще загружать колонки
    const needSupplierColumns = supplierFile && !supplierColumns.length;
    const needStoreColumns = storeFile && !storeColumns.length;
    
    if (!needSupplierColumns && !needStoreColumns) {
      console.log('Нет необходимости загружать колонки, все уже загружено');
      return;
    }
    
    setColumnsLoading(true);
    setError(null);
    
    try {
      // Загрузка колонок для файла поставщика
      if (needSupplierColumns) {
        try {
          if (!supplierFile.stored_filename) {
            console.error('Отсутствует stored_filename для файла поставщика', supplierFile);
            setError('Ошибка загрузки колонок: отсутствует имя файла');
            setColumnsLoading(false);
            return;
          }
          
          console.log('Запрос колонок для файла поставщика:', {
            stored_filename: supplierFile.stored_filename,
            encoding: supplierFile.encoding,
            separator: supplierFile.separator
          });
          
          const columns = await fileService.getColumns(
            supplierFile.stored_filename,
            supplierFile.encoding,
            supplierFile.separator
          );
          
          console.log('Получены колонки для файла поставщика:', columns);
          if (columns && columns.length > 0) {
            setSupplierColumns(columns);
          } else {
            console.error('Получен пустой список колонок для файла поставщика');
            setError('Не удалось получить колонки для файла поставщика');
          }
        } catch (err: any) {
          console.error('Ошибка загрузки колонок для файла поставщика:', {
            error: err,
            supplierFile
          });
          setError(`Ошибка загрузки колонок для файла поставщика: ${err.message || err}`);
        }
      } else {
        console.log('Пропуск загрузки колонок для файла поставщика:', {
          hasFile: !!supplierFile,
          hasColumns: supplierColumns.length > 0
        });
      }
      
      // Загрузка колонок для файла магазина
      if (needStoreColumns) {
        try {
          if (!storeFile.stored_filename) {
            console.error('Отсутствует stored_filename для файла магазина', storeFile);
            setError('Ошибка загрузки колонок: отсутствует имя файла');
            setColumnsLoading(false);
            return;
          }
          
          console.log('Запрос колонок для файла магазина:', {
            stored_filename: storeFile.stored_filename,
            encoding: storeFile.encoding,
            separator: storeFile.separator
          });
          
          const columns = await fileService.getColumns(
            storeFile.stored_filename,
            storeFile.encoding,
            storeFile.separator
          );
          
          console.log('Получены колонки для файла магазина:', columns);
          if (columns && columns.length > 0) {
            setStoreColumns(columns);
          } else {
            console.error('Получен пустой список колонок для файла магазина');
            setError('Не удалось получить колонки для файла магазина');
          }
        } catch (err: any) {
          console.error('Ошибка загрузки колонок для файла магазина:', {
            error: err,
            storeFile
          });
          setError(`Ошибка загрузки колонок для файла магазина: ${err.message || err}`);
        }
      } else {
        console.log('Пропуск загрузки колонок для файла магазина:', {
          hasFile: !!storeFile,
          hasColumns: storeColumns.length > 0
        });
      }
    } catch (err: any) {
      console.error('Общая ошибка при загрузке колонок:', err);
      setError(`Ошибка при загрузке колонок: ${err.message || err}`);
    } finally {
      console.log('Завершение загрузки колонок', {
        supplierColumns,
        storeColumns
      });
      setColumnsLoading(false);
    }
  }, [supplierFile, storeFile, supplierColumns, storeColumns, columnsLoading]);
  
  // При изменении файлов загружаем их колонки
  useEffect(() => {
    // Защита от множественных запросов
    let isActive = true;
    
    // Проверяем, нужно ли загружать колонки
    const needSupplierColumns = supplierFile && !supplierColumns.length;
    const needStoreColumns = storeFile && !storeColumns.length;
    
    if (needSupplierColumns || needStoreColumns) {
      console.log('Запуск загрузки колонок из useEffect', {
        supplierFile: !!supplierFile,
        storeFile: !!storeFile,
        supplierColumns: supplierColumns.length,
        storeColumns: storeColumns.length
      });
      
      // Используем setTimeout для предотвращения слишком частых запросов
      const timeoutId = setTimeout(() => {
        if (isActive) {
          loadColumns();
        }
      }, 100);
      
      return () => {
        isActive = false;
        clearTimeout(timeoutId);
      };
    }
    
    return () => {
      isActive = false;
    };
  }, [supplierFile, storeFile, loadColumns, supplierColumns.length, storeColumns.length]);
  
  // Обработчик загрузки файла поставщика
  const handleSupplierFileUpload = useCallback((fileInfo: FileInfo) => {
    console.log('Загружен файл поставщика:', {
      fileInfo,
      currentSupplierFile: supplierFile,
      currentSupplierColumns: supplierColumns
    });
    
    // Сбрасываем колонки только если загружен новый файл
    if (!supplierFile || supplierFile.id !== fileInfo.id) {
      setSupplierColumns([]);
    }
    
    setSupplierFile(fileInfo);
    setSuccess('Файл поставщика успешно загружен');
    setError(null);
  }, [supplierFile, supplierColumns]);
  
  // Обработчик загрузки файла магазина
  const handleStoreFileUpload = useCallback((fileInfo: FileInfo) => {
    console.log('Загружен файл магазина:', {
      fileInfo,
      currentStoreFile: storeFile,
      currentStoreColumns: storeColumns
    });
    
    // Сбрасываем колонки только если загружен новый файл
    if (!storeFile || storeFile.id !== fileInfo.id) {
      setStoreColumns([]);
    }
    
    setStoreFile(fileInfo);
    setSuccess('Файл магазина успешно загружен');
    setError(null);
  }, [storeFile, storeColumns]);
  
  // Обработчик сохранения маппинга колонок для файла поставщика
  const handleSupplierColumnMapping = (mapping: ColumnMapping) => {
    if (supplierFile) {
      const updatedFile = { ...supplierFile, column_mapping: mapping };
      
      // Обновляем состояние интерфейса
      setSupplierFile(updatedFile);
      setSuccess('Колонки для файла поставщика настроены');
      
      // Выводим отладочную информацию
      console.log('Сохраняем маппинг колонок для поставщика:', updatedFile);
      
      fileService.saveColumnMapping(updatedFile)
        .then(response => {
          console.log('Маппинг колонок для поставщика успешно сохранен на сервере:', response);
          // Обновляем состояние с данными с сервера
          setSupplierFile(response);
        })
        .catch(err => {
          console.error('Ошибка при сохранении маппинга колонок поставщика:', err);
          // Не показываем пользователю ошибку, так как поля уже сохранены в интерфейсе
        });
    }
  };
  
  // Обработчик сохранения маппинга колонок для файла магазина
  const handleStoreColumnMapping = (mapping: ColumnMapping) => {
    if (storeFile) {
      const updatedFile = { ...storeFile, column_mapping: mapping };
      
      // Обновляем состояние интерфейса
      setStoreFile(updatedFile);
      setSuccess('Колонки для файла магазина настроены');
      
      // Выводим отладочную информацию
      console.log('Сохраняем маппинг колонок для магазина:', updatedFile);
      
      fileService.saveColumnMapping(updatedFile)
        .then(response => {
          console.log('Маппинг колонок для магазина успешно сохранен на сервере:', response);
          // Обновляем состояние с данными с сервера
          setStoreFile(response);
        })
        .catch(err => {
          console.error('Ошибка при сохранении маппинга колонок магазина:', err);
          // Не показываем пользователю ошибку, так как поля уже сохранены в интерфейсе
        });
    }
  };
  
  // Следующий шаг
  const handleNext = () => {
    let canContinue = true;
    
    // Проверки для перехода на следующий шаг
    if (activeStep === 0) {
      if (!supplierFile || !storeFile) {
        setError('Пожалуйста, загрузите оба файла прежде чем продолжить');
        canContinue = false;
      }
    } else if (activeStep === 1) {
      if (!supplierFile?.column_mapping || !storeFile?.column_mapping) {
        setError('Пожалуйста, настройте колонки для обоих файлов');
        canContinue = false;
      }
    }
    
    if (canContinue) {
      setError(null);
      setActiveStep((prevActiveStep) => prevActiveStep + 1);
      setSuccess(`Шаг ${activeStep + 1} выполнен успешно`);
    }
  };
  
  // Предыдущий шаг
  const handleBack = () => {
    setActiveStep((prevActiveStep) => prevActiveStep - 1);
  };
  
  // Переход к сравнению
  const handleGoToComparison = () => {
    navigate('/comparison', { 
      state: { 
        supplierFile,
        storeFile
      } 
    });
  };
  
  // Добавляем функцию для диагностики проблемы
  const runDiagnostic = async () => {
    console.log('Запуск диагностического теста получения колонок');
    
    try {
      // Тестируем получение колонок для тестового файла
      console.log('Запрос колонок для файла:', {
        filename: 'diagnostic-test.csv',
        encoding: undefined,
        separator: undefined,
        url: 'files/columns/diagnostic-test.csv'
      });
      
      const response = await fileService.getColumns('diagnostic-test.csv');
      console.log('Результат диагностического теста:', response);
      
      // Если колонки получены успешно, добавляем их к поставщику
      if (response && response.length > 0) {
        setSupplierColumns(response);
      }
    } catch (err) {
      console.error('Ошибка диагностического теста:', err);
    }
  };
  
  // Добавляем функцию для тестирования общего API
  const testGeneralApi = async () => {
    console.log('Запуск теста общего API');
    
    try {
      console.log('Выполнение тестового запроса к API');
      const response = await axios.get('/api/v1/test');
      
      console.log('Получен ответ от тестового API:', response.data);
      console.log('Статус ответа:', response.status);
      console.log('Заголовки ответа:', response.headers);
      console.log('Ответ теста API:', response.data);
    } catch (err) {
      console.error('Ошибка теста общего API:', err);
    }
  };
  
  // Рендеринг контента в зависимости от активного шага
  const getStepContent = (step: number) => {
    switch (step) {
      case 0:
        return (
          <Grid container spacing={4}>
            <Grid item xs={12} md={6}>
              <FileDropzone 
                fileType={FileTypes.SUPPLIER}
                title="Загрузите файл с ОПТОВЫМИ ценами"
                description="Файл прайс-листа от вашего поставщика"
                onFileUploaded={handleSupplierFileUpload}
                isUploaded={!!supplierFile}
              />
            </Grid>
            
            <Grid item xs={12} md={6}>
              <FileDropzone 
                fileType={FileTypes.STORE}
                title="Загрузите файл с ТЕКУЩИМИ ценами магазина"
                description="Ваш текущий прайс-лист, цены в котором нужно обновить"
                onFileUploaded={handleStoreFileUpload}
                isUploaded={!!storeFile}
              />
            </Grid>
          </Grid>
        );
      case 1:
        return (
          <Grid container spacing={4}>
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom color="primary">
                    Настройка колонок файла поставщика
                  </Typography>
                  <Typography variant="body2" color="text.secondary" paragraph>
                    Для корректного сравнения цен нужно указать, какие колонки в файле содержат артикулы, цены и наименования товаров.
                    Мы попытались определить их автоматически, но вы можете изменить выбор, если он неверен.
                  </Typography>
                  {supplierFile && supplierColumns.length > 0 ? (
                    <ColumnSelector 
                      columns={supplierColumns}
                      onSave={handleSupplierColumnMapping}
                      initialMapping={supplierFile.column_mapping}
                    />
                  ) : (
                    <Paper sx={{ p: 3 }}>
                      <Typography color="text.secondary">
                        Загрузите файл поставщика и дождитесь загрузки колонок...
                      </Typography>
                      {supplierFile && (
                        <Button 
                          variant="outlined" 
                          color="warning" 
                          startIcon={<BuildIcon />}
                          onClick={runDiagnostic}
                          sx={{ mt: 2 }}
                        >
                          Диагностика (получить тестовые колонки)
                        </Button>
                      )}
                    </Paper>
                  )}
                </CardContent>
              </Card>
            </Grid>
            
            <Grid item xs={12} sx={{ mt: 3 }}>
              <Divider />
            </Grid>
            
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom color="primary">
                    Настройка колонок файла магазина
                  </Typography>
                  <Typography variant="body2" color="text.secondary" paragraph>
                    Для корректного сравнения цен нужно указать, какие колонки в файле содержат артикулы, цены и наименования товаров.
                    Мы попытались определить их автоматически, но вы можете изменить выбор, если он неверен.
                  </Typography>
                  {storeFile && storeColumns.length > 0 ? (
                    <ColumnSelector 
                      columns={storeColumns}
                      onSave={handleStoreColumnMapping}
                      initialMapping={storeFile.column_mapping}
                    />
                  ) : (
                    <Paper sx={{ p: 3 }}>
                      <Typography color="text.secondary">
                        Загрузите файл магазина и дождитесь загрузки колонок...
                      </Typography>
                    </Paper>
                  )}
                </CardContent>
              </Card>
            </Grid>
            
            <Grid item xs={12} sx={{ mt: 2 }}>
              <Button
                variant="outlined"
                color="info"
                onClick={testGeneralApi}
              >
                Проверить API
              </Button>
            </Grid>
          </Grid>
        );
      case 2:
        return (
          <Box textAlign="center" p={3}>
            <Paper sx={{ p: 4, maxWidth: 600, mx: 'auto' }}>
              <Typography variant="h5" gutterBottom color="primary">
                Все готово для сравнения цен!
              </Typography>
              
              <Typography paragraph sx={{ mb: 4 }}>
                Нажмите на кнопку ниже, чтобы перейти к сравнению цен между файлами
                поставщика и магазина. Вы сможете увидеть разницу в ценах и обновить
                свои цены.
              </Typography>
              
              <Button 
                variant="contained" 
                color="primary" 
                size="large"
                onClick={handleGoToComparison}
              >
                Перейти к сравнению цен
              </Button>
            </Paper>
          </Box>
        );
      default:
        return 'Неизвестный шаг';
    }
  };
  
  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 8 }}>
      <Typography variant="h4" gutterBottom align="center" sx={{ mb: 4 }}>
        Загрузка и подготовка прайс-листов
      </Typography>
      
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}
      
      {success && (
        <Alert severity="success" sx={{ mb: 3 }}>
          {success}
        </Alert>
      )}
      
      <Stepper activeStep={activeStep} alternativeLabel sx={{ mb: 5 }}>
        {steps.map((step, index) => (
          <Step key={step.label}>
            <StepLabel 
              StepIconProps={{
                icon: step.icon
              }}
            >
              {step.label}
            </StepLabel>
          </Step>
        ))}
      </Stepper>
      
      <Box sx={{ mb: 5 }}>
        <Typography variant="subtitle1" align="center" color="text.secondary" gutterBottom>
          {steps[activeStep]?.description}
        </Typography>
      </Box>
      
      {columnsLoading && activeStep === 1 && (
        <Box sx={{ display: 'flex', justifyContent: 'center', mb: 3 }}>
          <CircularProgress />
        </Box>
      )}
      
      {getStepContent(activeStep)}
      
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 4 }}>
        <Button
          variant="outlined"
          onClick={handleBack}
          disabled={activeStep === 0}
        >
          Назад
        </Button>
        
        {activeStep === steps.length - 1 ? (
          <Button
            variant="contained"
            color="primary"
            onClick={handleGoToComparison}
          >
            Перейти к сравнению
          </Button>
        ) : (
          <Button
            variant="contained"
            color="primary"
            onClick={handleNext}
          >
            Далее
          </Button>
        )}
      </Box>
    </Container>
  );
};

export default FileUploadPage; 