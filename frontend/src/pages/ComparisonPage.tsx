import React, { useState, useEffect, useRef } from 'react';
import { 
  Typography, 
  Box, 
  Paper, 
  Container, 
  Tabs, 
  Tab, 
  Alert,
  CircularProgress,
  Chip,
  Card,
  CardContent,
  Tooltip,
  Divider,
  IconButton,
} from '@mui/material';
import { useLocation, useNavigate } from 'react-router-dom';
import { AgGridReact } from 'ag-grid-react';
import { ColDef } from 'ag-grid-community';
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-material.css';
import { 
  FileInfo, 
  ComparisonResult, 
  MatchedItem, 
  MissingInStoreItem, 
  MissingInSupplierItem 
} from '../types';
import InfoIcon from '@mui/icons-material/Info';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import useLogger from '../hooks/useLogger';
import LogButton from '../components/ui/LogButton';
import axios from 'axios';

interface LocationState {
  supplierFile: FileInfo;
  storeFile: FileInfo;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

// Компонент для вкладок
const TabPanel: React.FC<TabPanelProps> = (props) => {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`tabpanel-${index}`}
      aria-labelledby={`tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box sx={{ pt: 3 }}>
          {children}
        </Box>
      )}
    </div>
  );
};

const ComparisonPage: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const state = location.state as LocationState;
  
  const [tabValue, setTabValue] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [comparisonResult, setComparisonResult] = useState<ComparisonResult | null>(null);
  const [selectedItems, setSelectedItems] = useState<MatchedItem[]>([]);
  const gridApiRef = useRef<any>(null);
  
  // Инициализация логгера для страницы
  const logger = useLogger('ComparisonPage');
  
  // Статистика
  const getStatistics = () => {
    if (!comparisonResult) return null;
    
    // Проверяем наличие данных
    if (!comparisonResult.matches_data || comparisonResult.matches_data.length === 0) {
      return {
        higherPrices: [],
        lowerPrices: [],
        samePrices: []
      };
    }
    
    // Цены выше в магазине
    const higherPrices = comparisonResult.matches_data.filter(item => item.price_diff < 0);
    // Цены ниже в магазине
    const lowerPrices = comparisonResult.matches_data.filter(item => item.price_diff > 0);
    // Одинаковые цены
    const samePrices = comparisonResult.matches_data.filter(item => item.price_diff === 0);
    
    return {
      higherPrices,
      lowerPrices,
      samePrices
    };
  };
  
  const stats = getStatistics();
  
  // Колонки для таблицы совпадающих товаров
  const matchesColumns: ColDef<MatchedItem>[] = [
    { 
      headerName: 'Артикул', 
      field: 'article', 
      sortable: true, 
      filter: true,
      checkboxSelection: true,
      headerCheckboxSelection: true,
      width: 120
    },
    { 
      headerName: 'Название товара', 
      field: 'supplier_name', 
      sortable: true, 
      filter: true,
      width: 300,
      tooltipField: 'supplier_name'
    },
    { 
      headerName: 'Цена поставщика', 
      field: 'supplier_price', 
      sortable: true, 
      filter: true,
      width: 150,
      valueFormatter: (params) => `${params.value.toFixed(2)} ₽`
    },
    { 
      headerName: 'Цена магазина', 
      field: 'store_price', 
      sortable: true, 
      filter: true,
      width: 150,
      valueFormatter: (params) => `${params.value.toFixed(2)} ₽`
    },
    { 
      headerName: 'Разница', 
      field: 'price_diff', 
      sortable: true, 
      filter: true,
      width: 150,
      valueFormatter: (params) => `${params.value.toFixed(2)} ₽`,
      cellStyle: (params) => {
        if (params.value < 0) {
          return { color: 'red', fontWeight: 'bold' };
        } else if (params.value > 0) {
          return { color: 'green', fontWeight: 'bold' };
        }
        return null;
      }
    },
    { 
      headerName: 'Разница, %', 
      field: 'price_diff_percent', 
      sortable: true, 
      filter: true,
      width: 120,
      valueFormatter: (params) => `${params.value.toFixed(2)}%`,
      cellStyle: (params) => {
        if (params.value < 0) {
          return { color: 'red', fontWeight: 'bold' };
        } else if (params.value > 0) {
          return { color: 'green', fontWeight: 'bold' };
        }
        return null;
      }
    }
  ];
  
  // Колонки для таблицы отсутствующих в магазине товаров
  const missingInStoreColumns: ColDef<MissingInStoreItem>[] = [
    { 
      headerName: 'Артикул', 
      field: 'article', 
      sortable: true, 
      filter: true,
      width: 150
    },
    { 
      headerName: 'Название товара', 
      field: 'supplier_name', 
      sortable: true, 
      filter: true,
      width: 300,
      tooltipField: 'supplier_name'
    },
    { 
      headerName: 'Цена поставщика', 
      field: 'supplier_price', 
      sortable: true, 
      filter: true,
      width: 150,
      valueFormatter: (params) => `${params.value.toFixed(2)} ₽`
    }
  ];
  
  // Колонки для таблицы отсутствующих у поставщика товаров
  const missingInSupplierColumns: ColDef<MissingInSupplierItem>[] = [
    { 
      headerName: 'Артикул', 
      field: 'article', 
      sortable: true, 
      filter: true,
      width: 150
    },
    { 
      headerName: 'Название товара', 
      field: 'store_name', 
      sortable: true, 
      filter: true,
      width: 300,
      tooltipField: 'store_name'
    },
    { 
      headerName: 'Цена магазина', 
      field: 'store_price', 
      sortable: true, 
      filter: true,
      width: 150,
      valueFormatter: (params) => `${params.value.toFixed(2)} ₽`
    }
  ];
  
  // Проверка доступности бэкенда
  const checkBackendAvailability = async () => {
    const endpoints = ['/api/v1/health', '/docs', '/api/v1'];
    let backendAvailable = false;
    
    // Пробуем подключиться к разным эндпоинтам бэкенда
    for (const endpoint of endpoints) {
      try {
        console.log(`Пробуем подключиться к ${endpoint}...`);
        await axios.get(`${endpoint}`, { timeout: 1500 });
        console.log(`Успешное подключение к ${endpoint}`);
        backendAvailable = true;
        break;
      } catch (e) {
        console.log(`Не удалось подключиться к ${endpoint}:`, e);
      }
    }
    
    if (!backendAvailable) {
      throw new Error('Не удалось подключиться к серверу. Проверьте, запущен ли бэкенд на порту 8000.');
    }
  };

  // Функция сравнения файлов
  const compareFiles = async () => {
    setLoading(true);
    setError('');
    setComparisonResult(null);

    try {
      // Проверяем доступность бэкенда
      await checkBackendAvailability();
      
      if (!state?.supplierFile || !state?.storeFile) {
        throw new Error('Не найдены файлы для сравнения. Пожалуйста, вернитесь на страницу загрузки файлов.');
      }
      
      // Отправка запроса на сервер с данными из location state
      const apiUrl = `/api/v1/comparison/compare`;
      console.log('Отправка запроса на:', apiUrl);
      console.log('С данными:', {
        supplier_file: state.supplierFile,
        store_file: state.storeFile
      });
      
      const response = await axios.post(apiUrl, {
        supplier_file: state.supplierFile,
        store_file: state.storeFile
      });
      
      console.log('Полный ответ сервера:', response);
      console.log('Результат сравнения (детально):', {
        matches_data: response.data.matches_data?.length || 0,
        missing_in_store: response.data.missing_in_store?.length || 0,
        missing_in_supplier: response.data.missing_in_supplier?.length || 0,
        raw_response: response.data
      });

      // Проверяем наличие данных в ответе
      if (response.data) {
        setComparisonResult(response.data);
        
        // Если есть совпадающие товары, выбираем их все
        if (response.data.matches_data && response.data.matches_data.length > 0) {
          setSelectedItems(response.data.matches_data);
          
          // Логируем успешное сравнение
          logger.logUserAction('comparison_success', 'comparison', {
            matches_count: response.data.matches_data.length,
            missing_in_store_count: response.data.missing_in_store?.length || 0,
            missing_in_supplier_count: response.data.missing_in_supplier?.length || 0
          });
        } else {
          console.warn('Нет совпадений для отображения, но есть другие результаты');
          // Не устанавливаем ошибку, если есть другие данные для отображения
          if (!response.data.missing_in_store?.length && !response.data.missing_in_supplier?.length) {
            setError('Нет данных для сравнения. Проверьте маппинг колонок и данные в файлах.');
          }
          
          // Логируем отсутствие результатов
          logger.logUserAction('comparison_no_results', 'comparison', {
            has_missing_in_store: response.data.missing_in_store?.length > 0,
            has_missing_in_supplier: response.data.missing_in_supplier?.length > 0
          });
        }
      } else {
        console.warn('Пустой ответ от сервера!');
        setError('Сервер вернул пустой ответ. Пожалуйста, попробуйте еще раз.');
        
        // Логируем ошибку
        logger.logUserAction('comparison_error', 'comparison', {
          error_message: 'Пустой ответ от сервера'
        });
      }
    } catch (err: any) {
      console.error('Ошибка при сравнении файлов:', err);
      if (err.response) {
        console.error('Ответ от сервера:', err.response.data);
      }
      setError('Ошибка при сравнении файлов: ' + (err.message || 'Неизвестная ошибка'));
      
      // Логируем ошибку
      logger.logUserAction('comparison_error', 'comparison', {
        error_message: err.message || 'Неизвестная ошибка',
        status: err.response?.status
      });
    } finally {
      setLoading(false);
      window.scrollTo(0, 0);
    }
  };
  
  // Загрузка результатов сравнения при монтировании
  useEffect(() => {
    compareFiles();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  
  // Обработчик изменения вкладки
  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
    
    // Логируем переключение вкладки
    const tabNames = ['matches', 'missing_in_store', 'missing_in_supplier'];
    logger.logTabSwitch(tabNames[newValue]);
  };
  
  // Обработчик выбора строк
  const onSelectionChanged = () => {
    if (gridApiRef.current && gridApiRef.current.api) {
      const selectedRows = gridApiRef.current.api.getSelectedRows();
      setSelectedItems(selectedRows);
      
      // Логируем выбор строк
      logger.logUserAction('rows_selected', 'data_grid', { 
        count: selectedRows.length 
      });
    } else {
      console.warn('Ошибка получения выбранных строк: gridApiRef.current или gridApiRef.current.api не определен');
    }
  };
  
  // Обработчик клика по строке
  const onRowClicked = (event: any) => {
    if (!event || !event.data) {
      console.warn('Ошибка в onRowClicked: event или event.data не определен', event);
      return;
    }
    
    // Логируем клик по строке
    logger.logUserAction('row_click', 'data_grid', { 
      article: event.data.article || 'неизвестный артикул'
    });
  };
  
  // Обработчик инициализации таблицы
  const onGridReady = (params: any) => {
    console.log('Таблица AG Grid инициализирована. Параметры:', params);
    
    if (!params || !params.api) {
      console.error('Ошибка инициализации AG Grid: params или params.api не определены', params);
      return;
    }
    
    gridApiRef.current = params;
    console.log('gridApiRef.current установлен:', gridApiRef.current);
    
    // Принудительно обновляем размеры таблицы
    setTimeout(() => {
      if (gridApiRef.current && gridApiRef.current.api) {
        console.log('Вызов методов AG Grid для обновления размеров');
        gridApiRef.current.api.sizeColumnsToFit();
        gridApiRef.current.api.resetRowHeights();
        
        // Выбираем все строки по умолчанию
        gridApiRef.current.api.selectAll();
      } else {
        console.error('Невозможно обновить размеры таблицы: gridApiRef.current или gridApiRef.current.api не определен');
      }
    }, 300); // Увеличим таймаут для надежности
    
    // Явно устанавливаем данные в таблицу
    if (comparisonResult && comparisonResult.matches_data && comparisonResult.matches_data.length > 0) {
      console.log('Устанавливаем данные в таблицу:', comparisonResult.matches_data);
      params.api.setRowData(comparisonResult.matches_data);
    } else {
      console.warn('Нет данных для отображения в таблице!');
    }
  };
  
  const handleGoToUpdate = () => {
    if (selectedItems.length === 0) {
      alert('Пожалуйста, выберите товары для обновления цен');
      return;
    }
    
    navigate('/update-prices', {
      state: {
        selectedItems,
        storeFile: state.storeFile
      }
    });
  };
  
  if (error) {
    return (
      <Container maxWidth="lg">
        <Alert severity="error" sx={{ mt: 3 }}>
          {error}
        </Alert>
        
        {error.includes('подключиться к серверу') && (
          <Box sx={{ mt: 2, p: 2, bgcolor: '#f5f5f5', borderRadius: 1 }}>
            <Typography variant="subtitle1" fontWeight="bold">Проблема с подключением к бэкенду:</Typography>
            <Typography variant="body2">
              Для работы приложения необходимо запустить бэкенд-сервер. Выполните следующие шаги:
            </Typography>
            <Box component="ol" sx={{ pl: 4, mt: 1 }}>
              <li>
                <Typography variant="body2">
                  Откройте новый терминал
                </Typography>
              </li>
              <li>
                <Typography variant="body2">
                  Перейдите в корневую директорию проекта
                </Typography>
              </li>
              <li>
                <Typography variant="body2">
                  Выполните команду: <code>./start_backend.sh</code>
                </Typography>
              </li>
              <li>
                <Typography variant="body2">
                  Дождитесь запуска сервера (в терминале должно появиться сообщение "Uvicorn running on http://0.0.0.0:8000")
                </Typography>
              </li>
              <li>
                <Typography variant="body2">
                  Нажмите на кнопку "Повторить сравнение" ниже
                </Typography>
              </li>
            </Box>
          </Box>
        )}
        
        {!loading && !comparisonResult && (
          <Box sx={{ mt: 3, display: 'flex', justifyContent: 'center', gap: 2 }}>
            <LogButton 
              logName="retry_comparison"
              pageName="ComparisonPage"
              variant="contained" 
              color="primary"
              onClick={() => window.location.reload()}
            >
              Повторить сравнение
            </LogButton>
            
            <LogButton 
              logName="return_to_upload"
              pageName="ComparisonPage"
              variant="outlined" 
              onClick={() => navigate('/upload')}
            >
              Вернуться к загрузке файлов
            </LogButton>
          </Box>
        )}
      </Container>
    );
  }
  
  if (loading) {
    return (
      <Container maxWidth="lg">
        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', mt: 5 }}>
          <CircularProgress size={60} />
          <Typography variant="h6" sx={{ mt: 3 }}>
            Сравниваем прайс-листы...
          </Typography>
          <Typography variant="body1" sx={{ mt: 2 }}>
            Это может занять некоторое время в зависимости от размера файлов
          </Typography>
        </Box>
      </Container>
    );
  }
  
  if (!comparisonResult) {
    return (
      <Container maxWidth="lg">
        <Alert severity="warning" sx={{ mt: 3 }}>
          Нет данных для сравнения
        </Alert>
        <Box sx={{ mt: 2, p: 2, bgcolor: '#f5f5f5', borderRadius: 1 }}>
          <Typography variant="subtitle1" fontWeight="bold">Диагностическая информация:</Typography>
          <Typography variant="body2">
            1. Проверьте, запущен ли бэкенд-сервер на порту 8000. Выполните команду <code>./start_backend.sh</code> в корне проекта.
          </Typography>
          <Typography variant="body2">
            2. Убедитесь, что маппинг колонок настроен правильно для обоих файлов.
          </Typography>
          <Typography variant="body2">
            3. Проверьте, что файлы содержат данные с одинаковыми артикулами (используйте одинаковый формат артикула).
          </Typography>
          <Typography variant="body2" sx={{ mt: 1 }}>
            Файл поставщика: {state?.supplierFile ? state.supplierFile.original_filename : 'не выбран'}
          </Typography>
          <Typography variant="body2">
            Файл магазина: {state?.storeFile ? state.storeFile.original_filename : 'не выбран'}
          </Typography>
        </Box>
        {!loading && (
          <Box sx={{ mt: 3, display: 'flex', justifyContent: 'center' }}>
            <LogButton 
              logName="return_to_upload"
              pageName="ComparisonPage"
              variant="contained" 
              onClick={() => navigate('/upload')}
            >
              Вернуться к загрузке файлов
            </LogButton>
          </Box>
        )}
      </Container>
    );
  }

  // Проверяем, есть ли хоть какие-то данные для отображения
  const hasAnyData = (
    (comparisonResult.matches_data && comparisonResult.matches_data.length > 0) ||
    (comparisonResult.missing_in_store && comparisonResult.missing_in_store.length > 0) ||
    (comparisonResult.missing_in_supplier && comparisonResult.missing_in_supplier.length > 0)
  );

  if (!hasAnyData) {
    return (
      <Container maxWidth="lg">
        <Alert severity="warning" sx={{ mt: 3 }}>
          Не найдено совпадений или отличий между файлами. Проверьте, что файлы содержат данные с одинаковыми артикулами и корректно настроен маппинг колонок.
        </Alert>
        
        <Box sx={{ mt: 2, p: 2, bgcolor: '#f5f5f5', borderRadius: 1 }}>
          <Typography variant="subtitle1" fontWeight="bold">Возможные причины отсутствия данных:</Typography>
          
          <Typography variant="body2" sx={{mt: 1}}>
            <strong>1. Разные форматы артикулов в файлах</strong> - артикулы должны точно совпадать, включая:
          </Typography>
          <Box component="ul" sx={{ pl: 4, mt: 0.5 }}>
            <li>
              <Typography variant="body2">
                Регистр букв (например, "ABC123" и "abc123" считаются разными)
              </Typography>
            </li>
            <li>
              <Typography variant="body2">
                Пробелы и дефисы (например, "123-456" и "123456" считаются разными)
              </Typography>
            </li>
            <li>
              <Typography variant="body2">
                Ведущие нули (например, "00123" и "123" считаются разными)
              </Typography>
            </li>
          </Box>
          
          <Typography variant="body2" sx={{mt: 1}}>
            <strong>2. Неправильный маппинг колонок</strong> - убедитесь, что правильно указали, какие колонки содержат:
          </Typography>
          <Box component="ul" sx={{ pl: 4, mt: 0.5 }}>
            <li>
              <Typography variant="body2">
                Артикул (article)
              </Typography>
            </li>
            <li>
              <Typography variant="body2">
                Название товара (name)
              </Typography>
            </li>
            <li>
              <Typography variant="body2">
                Цену (price)
              </Typography>
            </li>
          </Box>
          
          <Typography variant="body2" sx={{mt: 1}}>
            <strong>3. Бэкенд-сервер не запущен</strong> - запустите сервер с помощью команды <code>./start_backend.sh</code>
          </Typography>
        </Box>
        
        <Box sx={{ mt: 3, display: 'flex', justifyContent: 'center' }}>
          <LogButton 
            logName="return_to_upload"
            pageName="ComparisonPage"
            variant="contained" 
            onClick={() => navigate('/upload')}
          >
            Вернуться к загрузке файлов
          </LogButton>
        </Box>
      </Container>
    );
  }
  
  return (
    <Container maxWidth="lg">
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Результаты сравнения
        </Typography>
        <Typography variant="subtitle1" color="text.secondary">
          Сравнение цен поставщика и магазина для {comparisonResult.matches_data?.length || 0} товаров
        </Typography>
      </Box>
      
      {/* Статистика обновления */}
      {stats && (
        <Card sx={{ mb: 4 }}>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <InfoIcon color="primary" sx={{ mr: 1 }} />
              <Typography variant="h6">Общая статистика</Typography>
              <Tooltip title="Здесь представлена статистика сравнения цен по всем найденным товарам">
                <IconButton size="small" sx={{ ml: 1 }}>
                  <HelpOutlineIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            </Box>
            
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
              <Box sx={{ minWidth: 200, flex: 1 }}>
                <Typography variant="body2" color="text.secondary">Совпадающие товары</Typography>
                <Typography variant="h5">{comparisonResult.matches_data?.length || 0}</Typography>
              </Box>
              <Box sx={{ minWidth: 200, flex: 1 }}>
                <Typography variant="body2" color="text.secondary">Цены выше в магазине</Typography>
                <Typography variant="h5" color="error">{stats.higherPrices.length}</Typography>
              </Box>
              <Box sx={{ minWidth: 200, flex: 1 }}>
                <Typography variant="body2" color="text.secondary">Цены ниже в магазине</Typography>
                <Typography variant="h5" color="success">{stats.lowerPrices.length}</Typography>
              </Box>
              <Box sx={{ minWidth: 200, flex: 1 }}>
                <Typography variant="body2" color="text.secondary">Одинаковые цены</Typography>
                <Typography variant="h5">{stats.samePrices.length}</Typography>
              </Box>
            </Box>
            
            <Divider sx={{ my: 2 }} />
            
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
              <Box sx={{ minWidth: 200, flex: 1 }}>
                <Typography variant="body2" color="text.secondary">Отсутствуют в магазине</Typography>
                <Typography variant="h5">{comparisonResult.missing_in_store?.length || 0}</Typography>
              </Box>
              <Box sx={{ minWidth: 200, flex: 1 }}>
                <Typography variant="body2" color="text.secondary">Отсутствуют у поставщика</Typography>
                <Typography variant="h5">{comparisonResult.missing_in_supplier?.length || 0}</Typography>
              </Box>
            </Box>
          </CardContent>
        </Card>
      )}
      
      <Box sx={{ width: '100%' }}>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={tabValue} onChange={handleTabChange} aria-label="comparison tabs">
            <Tab 
              label="Совпадающие товары" 
              icon={<Chip label={comparisonResult.matches_data?.length || 0} size="small" color="primary" />} 
              iconPosition="end"
            />
            <Tab 
              label="Отсутствуют в магазине" 
              icon={<Chip label={comparisonResult.missing_in_store?.length || 0} size="small" color="warning" />} 
              iconPosition="end"
            />
            <Tab 
              label="Отсутствуют у поставщика" 
              icon={<Chip label={comparisonResult.missing_in_supplier?.length || 0} size="small" color="error" />} 
              iconPosition="end"
            />
          </Tabs>
        </Box>
        
        <TabPanel value={tabValue} index={0}>
          <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 2 }}>
            <LogButton
              logName="go_to_updates"
              pageName="ComparisonPage"
              logDetails={{ selected_items_count: selectedItems.length }}
              variant="contained"
              color="primary"
              disabled={selectedItems.length === 0}
              onClick={handleGoToUpdate}
            >
              Обновить цены выбранных товаров ({selectedItems.length})
            </LogButton>
          </Box>
          
          {/* Отображаем таблицу только если есть данные */}
          {comparisonResult && comparisonResult.matches_data && comparisonResult.matches_data.length > 0 ? (
            <Paper 
              elevation={1} 
              sx={{ 
                p: 1, 
                mb: 2,
                border: '1px solid #ddd'
              }}
            >
              <div 
                className="ag-theme-material" 
                style={{ 
                  height: '500px', 
                  width: '100%'
                }}
              >
                <AgGridReact
                  rowData={comparisonResult?.matches_data || []}
                  columnDefs={matchesColumns}
                  defaultColDef={{
                    resizable: true,
                    sortable: true,
                    filter: true
                  }}
                  pagination={true}
                  paginationPageSize={10}
                  rowSelection="multiple"
                  onSelectionChanged={onSelectionChanged}
                  onGridReady={onGridReady}
                  onRowClicked={onRowClicked}
                  rowHeight={48}
                  enableCellTextSelection={true}
                />
              </div>
            </Paper>
          ) : (
            <Alert severity="info" sx={{ mt: 2 }}>
              {loading ? "Загрузка данных..." : "Нет совпадающих товаров для отображения"}
            </Alert>
          )}
        </TabPanel>
        
        <TabPanel value={tabValue} index={1}>
          <Alert severity="info" sx={{ mb: 3 }}>
            Эти товары есть у поставщика, но отсутствуют в вашем магазине. Возможно, вы захотите добавить их в свой ассортимент.
          </Alert>
          
          {comparisonResult && comparisonResult.missing_in_store && comparisonResult.missing_in_store.length > 0 ? (
            <Paper 
              elevation={1} 
              sx={{ 
                p: 1, 
                mb: 2,
                border: '1px solid #ddd'
              }}
            >
              <div 
                className="ag-theme-material" 
                style={{ 
                  height: '400px', 
                  width: '100%'
                }}
              >
                <AgGridReact
                  rowData={comparisonResult?.missing_in_store || []}
                  columnDefs={missingInStoreColumns}
                  defaultColDef={{
                    resizable: true,
                    sortable: true,
                    filter: true
                  }}
                  pagination={true}
                  paginationPageSize={10}
                  rowHeight={48}
                  onRowClicked={onRowClicked}
                  enableCellTextSelection={true}
                />
              </div>
            </Paper>
          ) : (
            <Alert severity="info">
              {loading ? "Загрузка данных..." : "Нет товаров, отсутствующих в магазине"}
            </Alert>
          )}
        </TabPanel>
        
        <TabPanel value={tabValue} index={2}>
          <Alert severity="warning" sx={{ mb: 3 }}>
            Эти товары есть в вашем магазине, но отсутствуют у поставщика. Возможно, они сняты с производства или заменены новыми моделями.
          </Alert>
          
          {comparisonResult && comparisonResult.missing_in_supplier && comparisonResult.missing_in_supplier.length > 0 ? (
            <Paper 
              elevation={1} 
              sx={{ 
                p: 1, 
                mb: 2,
                border: '1px solid #ddd'
              }}
            >
              <div 
                className="ag-theme-material" 
                style={{ 
                  height: '400px', 
                  width: '100%'
                }}
              >
                <AgGridReact
                  rowData={comparisonResult?.missing_in_supplier || []}
                  columnDefs={missingInSupplierColumns}
                  defaultColDef={{
                    resizable: true,
                    sortable: true,
                    filter: true
                  }}
                  pagination={true}
                  paginationPageSize={10}
                  rowHeight={48}
                  onRowClicked={onRowClicked}
                  enableCellTextSelection={true}
                />
              </div>
            </Paper>
          ) : (
            <Alert severity="info">
              {loading ? "Загрузка данных..." : "Нет товаров, отсутствующих у поставщика"}
            </Alert>
          )}
        </TabPanel>
      </Box>
      
      {/* Кнопки навигации внизу страницы */}
      {comparisonResult && (
        <Box sx={{ mt: 3, display: 'flex', justifyContent: 'space-between' }}>
          <LogButton
            logName="go_to_updates"
            pageName="ComparisonPage"
            logDetails={{ selected_items_count: selectedItems.length }}
            variant="contained"
            color="primary"
            disabled={selectedItems.length === 0}
            onClick={handleGoToUpdate}
          >
            Обновить цены выбранных товаров ({selectedItems.length})
          </LogButton>
          
          <LogButton
            logName="return_to_upload"
            pageName="ComparisonPage"
            variant="outlined"
            onClick={() => navigate('/upload')}
          >
            Загрузить другие файлы
          </LogButton>
        </Box>
      )}
    </Container>
  );
};

export default ComparisonPage; 