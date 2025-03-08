import React, { useState, useEffect, useRef } from 'react';
import { 
  Typography, 
  Box, 
  Paper, 
  Container, 
  Tabs, 
  Tab, 
  Alert,
  Button,
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
import { comparisonService } from '../services/api';
import InfoIcon from '@mui/icons-material/Info';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import useLogger from '../hooks/useLogger';
import LogButton from '../components/ui/LogButton';

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
    
    // Цены выше в магазине
    const higherPrices = comparisonResult.matches.filter(item => item.price_diff < 0);
    // Цены ниже в магазине
    const lowerPrices = comparisonResult.matches.filter(item => item.price_diff > 0);
    // Одинаковые цены
    const samePrices = comparisonResult.matches.filter(item => item.price_diff === 0);
    
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
  
  // Загрузка результатов сравнения при монтировании
  useEffect(() => {
    const compareFiles = async () => {
      if (!state?.supplierFile || !state?.storeFile) {
        setError('Не найдены файлы для сравнения. Пожалуйста, вернитесь на страницу загрузки файлов.');
        logger.logUserAction('error', 'comparison', { error: 'missing_files' });
        return;
      }
      
      try {
        setLoading(true);
        setError(null);
        
        logger.logUserAction('comparison_start', 'comparison', {
          supplier_file: state.supplierFile.original_filename,
          store_file: state.storeFile.original_filename
        });
        
        console.log('Отправляемые данные:', {
          supplier_file: state.supplierFile,
          store_file: state.storeFile,
        });

        // Определяем, работаем ли мы на Vercel
        const isVercelEnv = window.location.hostname.includes('vercel.app') || 
                          window.location.hostname.includes('now.sh');

        // Для Vercel настраиваем запрос с таймаутом
        if (isVercelEnv) {
          console.log('Vercel среда: настраиваем запрос с коротким таймаутом');
          
          // Используем увеличенный таймаут для Vercel
          const controller = new AbortController();
          const timeoutId = setTimeout(() => controller.abort(), 8000);
          
          try {
            const response = await fetch(`${window.location.origin}/api/v1/comparison/compare`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({
                supplier_file: state.supplierFile,
                store_file: state.storeFile
              }),
              signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            if (!response.ok) {
              throw new Error(`Ошибка API: ${response.status} ${response.statusText}`);
            }
            
            const result = await response.json();
            console.log('Результат сравнения:', result);
            
            if (result && result.matches && result.matches.length > 0) {
              setComparisonResult(result);
              setSelectedItems(result.matches);
              
              // Логируем успешное сравнение
              logger.logUserAction('comparison_success', 'comparison', {
                matches_count: result.matches.length,
                missing_in_store_count: result.missing_in_store.length,
                missing_in_supplier_count: result.missing_in_supplier.length
              });
            } else {
              console.warn('Нет совпадений для отображения!');
              setError('Нет данных для сравнения');
              
              // Логируем отсутствие результатов
              logger.logUserAction('comparison_no_results', 'comparison', {});
            }
          } catch (fetchError: any) {
            console.error('Ошибка при сравнении файлов (Vercel):', fetchError);
            if (fetchError.name === 'AbortError') {
              setError('Превышено время ожидания ответа от сервера. Пожалуйста, попробуйте еще раз с файлами меньшего размера.');
            } else {
              setError('Ошибка при сравнении файлов: ' + (fetchError.message || 'Неизвестная ошибка'));
            }
            
            // Логируем ошибку
            logger.logUserAction('comparison_error', 'comparison', {
              error_message: fetchError.message || 'Неизвестная ошибка',
              error_type: fetchError.name
            });
          }
        } else {
          // Для не-Vercel используем обычный API
          const result = await comparisonService.compareFiles(state.supplierFile, state.storeFile);
          console.log('Результат сравнения:', result);

          if (result && result.matches && result.matches.length > 0) {
            setComparisonResult(result);
            setSelectedItems(result.matches);
            
            // Логируем успешное сравнение
            logger.logUserAction('comparison_success', 'comparison', {
              matches_count: result.matches.length,
              missing_in_store_count: result.missing_in_store.length,
              missing_in_supplier_count: result.missing_in_supplier.length
            });
          } else {
            console.warn('Нет совпадений для отображения!');
            setError('Нет данных для сравнения');
            
            // Логируем отсутствие результатов
            logger.logUserAction('comparison_no_results', 'comparison', {});
          }
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
    if (gridApiRef.current) {
      const selectedRows = gridApiRef.current.api.getSelectedRows();
      setSelectedItems(selectedRows);
      
      // Логируем выбор строк
      logger.logUserAction('rows_selected', 'data_grid', { 
        count: selectedRows.length 
      });
    }
  };
  
  // Обработчик клика по строке
  const onRowClicked = (event: any) => {
    // Логируем клик по строке
    logger.logUserAction('row_click', 'data_grid', { 
      article: event.data.article
    });
  };
  
  // Обработчик инициализации таблицы
  const onGridReady = (params: any) => {
    gridApiRef.current = params.api;
    console.log('Таблица AG Grid инициализирована:', params.api);
    
    // Принудительно обновляем размеры таблицы
    setTimeout(() => {
      if (gridApiRef.current) {
        gridApiRef.current.sizeColumnsToFit();
        gridApiRef.current.resetRowHeights();
        
        // Выбираем все строки по умолчанию
        gridApiRef.current.selectAll();
      }
    }, 100);
    
    // Явно устанавливаем данные в таблицу
    if (comparisonResult && comparisonResult.matches && comparisonResult.matches.length > 0) {
      console.log('Устанавливаем данные в таблицу:', comparisonResult.matches);
      params.api.setRowData(comparisonResult.matches);
    } else {
      console.warn('Нет данных для отображения в таблице!');
    }
  };
  
  // Переход на страницу обновления цен
  const handleGoToUpdate = () => {
    if (selectedItems.length === 0) {
      alert('Пожалуйста, выберите товары для обновления цен');
      return;
    }
    
    navigate('/update', {
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
        {!loading && !comparisonResult && (
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
  
  return (
    <Container maxWidth="lg">
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Результаты сравнения
        </Typography>
        <Typography variant="subtitle1" color="text.secondary">
          Сравнение цен поставщика и магазина для {comparisonResult.matches.length} товаров
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
                <Typography variant="h5">{comparisonResult.matches.length}</Typography>
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
                <Typography variant="h5">{comparisonResult.missing_in_store.length}</Typography>
              </Box>
              <Box sx={{ minWidth: 200, flex: 1 }}>
                <Typography variant="body2" color="text.secondary">Отсутствуют у поставщика</Typography>
                <Typography variant="h5">{comparisonResult.missing_in_supplier.length}</Typography>
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
              icon={<Chip label={comparisonResult.matches.length} size="small" color="primary" />} 
              iconPosition="end"
            />
            <Tab 
              label="Отсутствуют в магазине" 
              icon={<Chip label={comparisonResult.missing_in_store.length} size="small" color="warning" />} 
              iconPosition="end"
            />
            <Tab 
              label="Отсутствуют у поставщика" 
              icon={<Chip label={comparisonResult.missing_in_supplier.length} size="small" color="error" />} 
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
              onClick={() => {
                navigate('/update-prices', {
                  state: {
                    selectedItems,
                    storeFile: state.storeFile
                  }
                });
              }}
            >
              Обновить цены выбранных товаров ({selectedItems.length})
            </LogButton>
          </Box>
          
          {/* Отображаем таблицу только если есть данные */}
          {comparisonResult && comparisonResult.matches && comparisonResult.matches.length > 0 ? (
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
                  rowData={comparisonResult.matches}
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
                  rowData={comparisonResult.missing_in_store}
                  columnDefs={missingInStoreColumns}
                  defaultColDef={{
                    resizable: true,
                    sortable: true,
                    filter: true
                  }}
                  pagination={true}
                  paginationPageSize={10}
                  rowHeight={48}
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
                  rowData={comparisonResult.missing_in_supplier}
                  columnDefs={missingInSupplierColumns}
                  defaultColDef={{
                    resizable: true,
                    sortable: true,
                    filter: true
                  }}
                  pagination={true}
                  paginationPageSize={10}
                  rowHeight={48}
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
            onClick={() => {
              navigate('/update-prices', {
                state: {
                  selectedItems,
                  storeFile: state.storeFile
                }
              });
            }}
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