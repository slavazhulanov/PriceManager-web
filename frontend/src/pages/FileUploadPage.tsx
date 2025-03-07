import React, { useState, useEffect } from 'react';
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
import { useNavigate } from 'react-router-dom';
import FileDropzone from '../components/file/FileDropzone';
import ColumnSelector from '../components/file/ColumnSelector';
import { FileInfo, FileType, ColumnMapping } from '../types';
import { fileService } from '../services/api';

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
  const loadColumns = async () => {
    setColumnsLoading(true);
    setError(null);
    
    try {
      // Загрузка колонок для файла поставщика
      if (supplierFile && !supplierColumns.length) {
        try {
          // В реальном приложении или если включен флаг использования реального API
          if (process.env.NODE_ENV === 'production' || process.env.REACT_APP_USE_REAL_API === 'true') {
            const columns = await fileService.getColumns(
              supplierFile.stored_filename,
              supplierFile.encoding,
              supplierFile.separator
            );
            setSupplierColumns(columns);
          } else {
            // Для демонстрации используем моковые данные
            // Если файл содержит 'mock' в имени, используем предопределенные колонки
            const mockColumns = ['Артикул', 'Цена поставщика', 'Наименование товара', 'Категория', 'Бренд'];
            setSupplierColumns(mockColumns);
          }
        } catch (err: any) {
          console.error('Ошибка загрузки колонок для файла поставщика:', err);
          setError(`Ошибка загрузки колонок для файла поставщика: ${err.message || err}`);
        }
      }
      
      // Загрузка колонок для файла магазина
      if (storeFile && !storeColumns.length) {
        try {
          // В реальном приложении или если включен флаг использования реального API
          if (process.env.NODE_ENV === 'production' || process.env.REACT_APP_USE_REAL_API === 'true') {
            const columns = await fileService.getColumns(
              storeFile.stored_filename,
              storeFile.encoding,
              storeFile.separator
            );
            setStoreColumns(columns);
          } else {
            // Для демонстрации используем моковые данные
            const mockColumns = ['Артикул', 'Цена магазина', 'Наименование товара', 'Остаток', 'Категория'];
            setStoreColumns(mockColumns);
          }
        } catch (err: any) {
          console.error('Ошибка загрузки колонок для файла магазина:', err);
          setError(`Ошибка загрузки колонок для файла магазина: ${err.message || err}`);
        }
      }
    } finally {
      setColumnsLoading(false);
    }
  };
  
  // При изменении файлов загружаем их колонки
  useEffect(() => {
    loadColumns();
  }, [supplierFile, storeFile, supplierColumns.length, storeColumns.length]);
  
  // Обработчик загрузки файла поставщика
  const handleSupplierFileUpload = (fileInfo: FileInfo) => {
    setSupplierFile(fileInfo);
  };
  
  // Обработчик загрузки файла магазина
  const handleStoreFileUpload = (fileInfo: FileInfo) => {
    setStoreFile(fileInfo);
  };
  
  // Обработчик сохранения маппинга колонок для файла поставщика
  const handleSupplierColumnMapping = (mapping: ColumnMapping) => {
    if (supplierFile) {
      const updatedFile = { ...supplierFile, column_mapping: mapping };
      
      // Обновляем состояние интерфейса
      setSupplierFile(updatedFile);
      setSuccess('Колонки для файла поставщика настроены');
      
      // В реальном приложении сохраняем маппинг на сервере
      if (process.env.NODE_ENV === 'production' || process.env.REACT_APP_USE_REAL_API === 'true') {
        fileService.saveColumnMapping(updatedFile)
          .then(() => {
            console.log('Маппинг колонок для поставщика успешно сохранен на сервере');
          })
          .catch(err => {
            console.error('Ошибка при сохранении маппинга колонок поставщика:', err);
            // Не показываем пользователю ошибку, так как поля уже сохранены в интерфейсе
          });
      }
    }
  };
  
  // Обработчик сохранения маппинга колонок для файла магазина
  const handleStoreColumnMapping = (mapping: ColumnMapping) => {
    if (storeFile) {
      const updatedFile = { ...storeFile, column_mapping: mapping };
      
      // Обновляем состояние интерфейса
      setStoreFile(updatedFile);
      setSuccess('Колонки для файла магазина настроены');
      
      // В реальном приложении сохраняем маппинг на сервере
      if (process.env.NODE_ENV === 'production' || process.env.REACT_APP_USE_REAL_API === 'true') {
        fileService.saveColumnMapping(updatedFile)
          .then(() => {
            console.log('Маппинг колонок для магазина успешно сохранен на сервере');
          })
          .catch(err => {
            console.error('Ошибка при сохранении маппинга колонок магазина:', err);
            // Не показываем пользователю ошибку, так как поля уже сохранены в интерфейсе
          });
      }
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
    // В реальном приложении мы бы здесь сохраняли данные в localStorage или Redux
    // и переходили на страницу сравнения
    navigate('/comparison', { 
      state: { 
        supplierFile,
        storeFile
      } 
    });
  };
  
  // Рендеринг контента в зависимости от активного шага
  const getStepContent = (step: number) => {
    switch (step) {
      case 0:
        return (
          <Grid container spacing={4}>
            <Grid item xs={12} md={6}>
              <FileDropzone 
                fileType={FileType.SUPPLIER}
                title="Загрузите файл с ОПТОВЫМИ ценами"
                description="Файл прайс-листа от вашего поставщика"
                onFileUploaded={handleSupplierFileUpload}
                isUploaded={!!supplierFile}
              />
            </Grid>
            
            <Grid item xs={12} md={6}>
              <FileDropzone 
                fileType={FileType.STORE}
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
                    Укажите, какие колонки в вашем файле магазина содержат артикулы, цены и наименования товаров.
                    Эта информация нужна для правильного обновления цен.
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
          </Grid>
        );
      case 2:
        return (
          <Card sx={{ p: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom color="primary">
                Готово к сравнению
              </Typography>
              
              <Typography variant="body1" paragraph>
                Поздравляем! Все необходимые данные загружены и настроены. Теперь вы можете перейти к сравнению цен.
              </Typography>
              
              <Typography variant="body2" paragraph color="text.secondary">
                На следующем экране вы увидите:
                <ul>
                  <li>Товары с разницей в ценах между поставщиком и магазином</li>
                  <li>Товары, которые есть у поставщика, но отсутствуют в вашем магазине</li>
                  <li>Товары, которые есть в магазине, но отсутствуют у поставщика</li>
                </ul>
              </Typography>
              
              <Box sx={{ mt: 3 }}>
                <Button 
                  variant="contained" 
                  color="primary" 
                  size="large"
                  onClick={handleGoToComparison}
                >
                  Перейти к сравнению цен
                </Button>
              </Box>
            </CardContent>
          </Card>
        );
      default:
        return 'Неизвестный шаг';
    }
  };
  
  return (
    <Container maxWidth="lg">
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Загрузка и настройка файлов
        </Typography>
        <Typography variant="subtitle1" color="text.secondary">
          Загрузите файлы прайс-листов поставщика и магазина для сравнения и обновления цен
        </Typography>
      </Box>
      
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}
      
      {success && (
        <Alert severity="success" sx={{ mb: 3 }} onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      )}
      
      <Stepper activeStep={activeStep} alternativeLabel sx={{ mb: 4 }}>
        {steps.map((step, index) => (
          <Step key={step.label}>
            <StepLabel 
              StepIconProps={{ 
                icon: step.icon 
              }}
            >
              <Typography variant="subtitle2">{step.label}</Typography>
              <Typography variant="caption" color="text.secondary">{step.description}</Typography>
            </StepLabel>
          </Step>
        ))}
      </Stepper>
      
      <Box sx={{ mb: 4 }}>
        {getStepContent(activeStep)}
      </Box>
      
      <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
        <Button
          variant="outlined"
          onClick={handleBack}
          disabled={activeStep === 0}
          sx={{ mr: 1 }}
        >
          Назад
        </Button>
        
        {activeStep < steps.length - 1 && (
          <Button
            variant="contained"
            onClick={handleNext}
          >
            {activeStep === 0 ? 'Далее: Настройка колонок' : 'Далее: Проверка данных'}
          </Button>
        )}
      </Box>
    </Container>
  );
};

export default FileUploadPage; 