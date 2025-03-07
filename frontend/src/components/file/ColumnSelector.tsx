import React, { useState, useEffect } from 'react';
import { 
  FormControl, 
  InputLabel, 
  Select, 
  MenuItem, 
  SelectChangeEvent, 
  Typography, 
  Box, 
  Paper, 
  Button,
  Grid,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Alert,
  Tooltip,
  IconButton
} from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import InfoIcon from '@mui/icons-material/Info';
import { ColumnMapping } from '../../types';

interface ColumnSelectorProps {
  columns: string[];
  onSave: (mapping: ColumnMapping) => void;
  initialMapping?: ColumnMapping;
}

const ColumnSelector: React.FC<ColumnSelectorProps> = ({
  columns,
  onSave,
  initialMapping
}) => {
  const [articleColumn, setArticleColumn] = useState<string>(initialMapping?.article_column || '');
  const [priceColumn, setPriceColumn] = useState<string>(initialMapping?.price_column || '');
  const [nameColumn, setNameColumn] = useState<string>(initialMapping?.name_column || '');
  const [saved, setSaved] = useState<boolean>(!!initialMapping);
  const [autoDetected, setAutoDetected] = useState<boolean>(false);
  
  useEffect(() => {
    // При изменении списка колонок, если есть начальные значения, устанавливаем их
    if (initialMapping) {
      setArticleColumn(initialMapping.article_column);
      setPriceColumn(initialMapping.price_column);
      if (initialMapping.name_column) {
        setNameColumn(initialMapping.name_column);
      }
      setSaved(true);
    }
    // Если колонок мало, можно попробовать автоматически определить нужные
    else if (columns.length > 0) {
      // Автоматический выбор колонки для артикула
      const possibleArticleColumns = columns.filter(col => 
        col.toLowerCase().includes('артикул') || 
        col.toLowerCase().includes('article') || 
        col.toLowerCase().includes('код') || 
        col.toLowerCase().includes('code')
      );
      if (possibleArticleColumns.length > 0) {
        setArticleColumn(possibleArticleColumns[0]);
        setAutoDetected(true);
      }
      
      // Автоматический выбор колонки для цены
      const possiblePriceColumns = columns.filter(col => 
        col.toLowerCase().includes('цена') || 
        col.toLowerCase().includes('price') || 
        col.toLowerCase().includes('стоимость') || 
        col.toLowerCase().includes('cost')
      );
      if (possiblePriceColumns.length > 0) {
        setPriceColumn(possiblePriceColumns[0]);
        setAutoDetected(true);
      }
      
      // Автоматический выбор колонки для наименования
      const possibleNameColumns = columns.filter(col => 
        col.toLowerCase().includes('наименование') || 
        col.toLowerCase().includes('название') || 
        col.toLowerCase().includes('name') || 
        col.toLowerCase().includes('товар') || 
        col.toLowerCase().includes('product')
      );
      if (possibleNameColumns.length > 0) {
        setNameColumn(possibleNameColumns[0]);
        setAutoDetected(true);
      }
    }
  }, [columns, initialMapping]);
  
  const handleArticleChange = (event: SelectChangeEvent<string>) => {
    setArticleColumn(event.target.value);
    setSaved(false);
  };
  
  const handlePriceChange = (event: SelectChangeEvent<string>) => {
    setPriceColumn(event.target.value);
    setSaved(false);
  };
  
  const handleNameChange = (event: SelectChangeEvent<string>) => {
    setNameColumn(event.target.value);
    setSaved(false);
  };
  
  const handleSave = () => {
    // Проверяем, что выбраны обязательные колонки
    if (!articleColumn || !priceColumn) {
      alert('Пожалуйста, выберите колонки для артикула и цены');
      return;
    }
    
    // Создаем объект маппинга
    const mapping: ColumnMapping = {
      article_column: articleColumn,
      price_column: priceColumn
    };
    
    // Добавляем необязательную колонку имени, если она выбрана
    if (nameColumn) {
      mapping.name_column = nameColumn;
    }
    
    // Вызываем callback
    onSave(mapping);
    setSaved(true);
  };
  
  // Примерные данные для предпросмотра
  const previewData = [
    {
      article: articleColumn ? 'A12345' : '',
      name: nameColumn ? 'Смартфон Samsung Galaxy' : '',
      price: priceColumn ? '29 990 ₽' : ''
    },
    {
      article: articleColumn ? 'B67890' : '',
      name: nameColumn ? 'Ноутбук ASUS VivoBook' : '',
      price: priceColumn ? '49 990 ₽' : ''
    }
  ];
  
  return (
    <Paper sx={{ p: 3 }}>
      {autoDetected && !saved && (
        <Alert severity="info" sx={{ mb: 3 }}>
          Мы автоматически определили колонки на основе их названий. Пожалуйста, проверьте правильность выбора.
        </Alert>
      )}
      
      {saved && (
        <Alert severity="success" sx={{ mb: 3 }} icon={<CheckCircleIcon />}>
          Настройки колонок сохранены успешно!
        </Alert>
      )}
      
      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <FormControl fullWidth margin="normal">
            <InputLabel id="article-column-label" required>
              Колонка с артикулом
              <Tooltip title="Выберите колонку, содержащую артикулы или коды товаров">
                <IconButton size="small" sx={{ ml: 1 }}>
                  <HelpOutlineIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            </InputLabel>
            <Select
              labelId="article-column-label"
              value={articleColumn}
              onChange={handleArticleChange}
              label="Колонка с артикулом *"
              required
            >
              {columns.map((column) => (
                <MenuItem key={column} value={column}>
                  {column}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Grid>
        
        <Grid item xs={12} md={4}>
          <FormControl fullWidth margin="normal">
            <InputLabel id="price-column-label" required>
              Колонка с ценой
              <Tooltip title="Выберите колонку, содержащую цены товаров">
                <IconButton size="small" sx={{ ml: 1 }}>
                  <HelpOutlineIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            </InputLabel>
            <Select
              labelId="price-column-label"
              value={priceColumn}
              onChange={handlePriceChange}
              label="Колонка с ценой *"
              required
            >
              {columns.map((column) => (
                <MenuItem key={column} value={column}>
                  {column}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Grid>
        
        <Grid item xs={12} md={4}>
          <FormControl fullWidth margin="normal">
            <InputLabel id="name-column-label">
              Колонка с названием
              <Tooltip title="Выберите колонку, содержащую наименования товаров (необязательно)">
                <IconButton size="small" sx={{ ml: 1 }}>
                  <HelpOutlineIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            </InputLabel>
            <Select
              labelId="name-column-label"
              value={nameColumn}
              onChange={handleNameChange}
              label="Колонка с названием"
            >
              <MenuItem value="">
                <em>Не выбрано</em>
              </MenuItem>
              {columns.map((column) => (
                <MenuItem key={column} value={column}>
                  {column}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Grid>
      </Grid>
      
      {/* Предпросмотр сопоставления */}
      {(articleColumn || priceColumn || nameColumn) && (
        <Box sx={{ mt: 4, mb: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <InfoIcon color="primary" sx={{ mr: 1 }} />
            <Typography variant="h6" gutterBottom>
              Предпросмотр сопоставления
            </Typography>
          </Box>
          
          <TableContainer component={Paper} variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow>
                  {articleColumn && <TableCell sx={{ fontWeight: 'bold' }}>Артикул ({articleColumn})</TableCell>}
                  {nameColumn && <TableCell sx={{ fontWeight: 'bold' }}>Название ({nameColumn})</TableCell>}
                  {priceColumn && <TableCell sx={{ fontWeight: 'bold' }}>Цена ({priceColumn})</TableCell>}
                </TableRow>
              </TableHead>
              <TableBody>
                {previewData.map((row, index) => (
                  <TableRow key={index}>
                    {articleColumn && <TableCell>{row.article}</TableCell>}
                    {nameColumn && <TableCell>{row.name}</TableCell>}
                    {priceColumn && <TableCell>{row.price}</TableCell>}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
            * Это примерные данные для предпросмотра. Реальные данные будут использованы при сравнении.
          </Typography>
        </Box>
      )}
      
      <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end' }}>
        <Button 
          variant="contained" 
          color="primary" 
          onClick={handleSave}
          disabled={!articleColumn || !priceColumn || saved}
          sx={{ minWidth: 150 }}
        >
          {saved ? "Сохранено" : "Сохранить"}
        </Button>
      </Box>
    </Paper>
  );
};

export default ColumnSelector; 