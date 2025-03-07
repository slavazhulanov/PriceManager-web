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
        return;
      }
      
      try {
        setLoading(true);
        setError(null);
        
        // В реальном приложении вызываем API
        if (process.env.NODE_ENV === 'production' || process.env.REACT_APP_USE_REAL_API === 'true') {
          try {
            const result = await comparisonService.compareFiles(state.supplierFile, state.storeFile);
            console.log('Данные для сравнения успешно загружены:', result);
            setComparisonResult(result);
            
            // Выбираем все товары по умолчанию
            if (result && result.matches) {
              setSelectedItems(result.matches);
            }
          } catch (apiError: any) {
            console.error('Ошибка API при сравнении файлов:', apiError);
            setError(`Ошибка при сравнении файлов: ${apiError}`);
          }
        } else {
          // Для демонстрации используем моковые данные
          const mockResult: ComparisonResult = {
            matches: [
              { 
                article: '10001', 
                supplier_name: 'Смартфон Samsung Galaxy A54', 
                store_name: 'Samsung Galaxy A54 128GB', 
                supplier_price: 27990, 
                store_price: 29990, 
                price_diff: -2000, 
                price_diff_percent: -6.67
              },
              { 
                article: '10002', 
                supplier_name: 'Ноутбук ASUS VivoBook 15', 
                store_name: 'ASUS VivoBook 15 K513', 
                supplier_price: 45990, 
                store_price: 48990, 
                price_diff: -3000, 
                price_diff_percent: -6.12
              },
              { 
                article: '10003', 
                supplier_name: 'Наушники Sony WH-1000XM5', 
                store_name: 'Sony WH-1000XM5 Black', 
                supplier_price: 32490, 
                store_price: 34990, 
                price_diff: -2500, 
                price_diff_percent: -7.14
              },
              { 
                article: '10005', 
                supplier_name: 'Телевизор LG OLED C3', 
                store_name: 'LG OLED C3 55" 4K', 
                supplier_price: 119900, 
                store_price: 115990, 
                price_diff: 3910, 
                price_diff_percent: 3.37
              },
              { 
                article: '10007', 
                supplier_name: 'Видеокарта NVIDIA GeForce RTX 4070', 
                store_name: 'NVIDIA GeForce RTX 4070 Founders Edition', 
                supplier_price: 78990, 
                store_price: 82990, 
                price_diff: -4000, 
                price_diff_percent: -4.82
              },
              { 
                article: '10008', 
                supplier_name: 'Монитор Samsung Odyssey G5', 
                store_name: 'Samsung Odyssey G5 27"', 
                supplier_price: 29990, 
                store_price: 32990, 
                price_diff: -3000, 
                price_diff_percent: -9.09
              },
              { 
                article: '10009', 
                supplier_name: 'Умные часы Apple Watch Series 8', 
                store_name: 'Apple Watch Series 8 GPS 41mm', 
                supplier_price: 36990, 
                store_price: 38990, 
                price_diff: -2000, 
                price_diff_percent: -5.13
              },
              { 
                article: '10012', 
                supplier_name: 'Робот-пылесос Xiaomi Robot Vacuum', 
                store_name: 'Xiaomi Robot Vacuum S10', 
                supplier_price: 22990, 
                store_price: 24990, 
                price_diff: -2000, 
                price_diff_percent: -8.00
              }
            ],
            missing_in_store: [
              { article: '10004', supplier_name: 'Планшет Apple iPad Air', supplier_price: 58990 },
              { article: '10006', supplier_name: 'Игровая приставка Sony PlayStation 5', supplier_price: 49990 },
              { article: '10010', supplier_name: 'Холодильник Bosch Serie 4', supplier_price: 75990 },
              { article: '10011', supplier_name: 'Фотоаппарат Canon EOS R6', supplier_price: 199990 },
              { article: '10013', supplier_name: 'Клавиатура Logitech G Pro', supplier_price: 12990 },
              { article: '10014', supplier_name: 'Принтер HP LaserJet', supplier_price: 18990 },
              { article: '10015', supplier_name: 'Усилитель звука Denon PMA-600NE', supplier_price: 42990 }
            ],
            missing_in_supplier: [
              { article: '10016', store_name: 'Sony PlayStation DualSense', store_price: 7990 },
              { article: '10017', store_name: 'Яндекс Станция Лайт', store_price: 5990 },
              { article: '10018', store_name: 'Apple AirPods Pro 2', store_price: 22990 },
              { article: '10019', store_name: 'Samsung Galaxy S23 Ultra', store_price: 99990 },
              { article: '10020', store_name: 'Logitech MX Master 3S', store_price: 8990 }
            ]
          };
          
          console.log('Данные для сравнения готовы (моки):', mockResult);
          setComparisonResult(mockResult);
          
          // Выбираем все товары по умолчанию для обновления цен
          setSelectedItems(mockResult.matches);
        }
        
        setLoading(false);
        
        // Убедимся, что сверху страницы
        window.scrollTo(0, 0);
        
      } catch (err: any) {
        console.error('Общая ошибка при сравнении файлов:', err);
        setError('Ошибка при сравнении файлов: ' + (err.message || 'Неизвестная ошибка'));
        setLoading(false);
      }
    };
    
    compareFiles();
  }, [state]);
  
  // Обработчик изменения вкладки
  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };
  
  // Обработчик выбора строк в таблице совпадений
  const onSelectionChanged = (event: any) => {
    const selectedRows = event.api.getSelectedRows();
    setSelectedItems(selectedRows);
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
        <Box sx={{ mt: 3 }}>
          <Button 
            variant="contained" 
            onClick={() => navigate('/upload')}
          >
            Вернуться к загрузке файлов
          </Button>
        </Box>
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
        <Box sx={{ mt: 3 }}>
          <Button 
            variant="contained" 
            onClick={() => navigate('/upload')}
          >
            Загрузить файлы
          </Button>
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
            <Button 
              variant="contained" 
              color="primary" 
              onClick={handleGoToUpdate}
              disabled={selectedItems.length === 0}
            >
              Обновить цены всех товаров ({comparisonResult?.matches.length || 0})
            </Button>
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
          
          <Box sx={{ mt: 2, display: 'flex', justifyContent: 'flex-end' }}>
            <Button 
              variant="contained" 
              color="primary" 
              onClick={handleGoToUpdate}
              disabled={selectedItems.length === 0}
            >
              Обновить цены всех товаров ({comparisonResult?.matches.length || 0})
            </Button>
          </Box>
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
    </Container>
  );
};

export default ComparisonPage; 