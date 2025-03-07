import React, { useState } from 'react';
import { 
  Typography, 
  Box, 
  Paper, 
  Container, 
  Button, 
  Alert, 
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Checkbox,
  Link
} from '@mui/material';
import { useLocation, useNavigate } from 'react-router-dom';
import { MatchedItem, FileInfo, PriceUpdate } from '../types';
import { priceService } from '../services/api';

interface LocationState {
  selectedItems: MatchedItem[];
  storeFile: FileInfo;
}

const PriceUpdatePage: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const state = location.state as LocationState;
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<boolean>(false);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [selectedItems, setSelectedItems] = useState<MatchedItem[]>(
    state?.selectedItems || []
  );
  
  // Обработчик выбора/отмены выбора всех элементов
  const handleSelectAll = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.checked) {
      setSelectedItems(state?.selectedItems || []);
    } else {
      setSelectedItems([]);
    }
  };
  
  // Обработчик выбора/отмены выбора отдельного элемента
  const handleSelectItem = (item: MatchedItem) => {
    const isSelected = selectedItems.some(
      (selectedItem) => selectedItem.article === item.article
    );
    
    if (isSelected) {
      setSelectedItems(
        selectedItems.filter((selectedItem) => selectedItem.article !== item.article)
      );
    } else {
      setSelectedItems([...selectedItems, item]);
    }
  };
  
  // Проверка, выбран ли элемент
  const isSelected = (article: string) => {
    return selectedItems.some((item) => item.article === article);
  };
  
  // Обработчик обновления цен
  const handleUpdatePrices = async () => {
    if (!state?.storeFile) {
      setError('Не найден файл магазина. Пожалуйста, вернитесь на страницу сравнения.');
      return;
    }
    
    if (selectedItems.length === 0) {
      setError('Пожалуйста, выберите товары для обновления цен');
      return;
    }
    
    try {
      setLoading(true);
      setError(null);
      
      // Подготовка данных для обновления
      const updates: PriceUpdate[] = selectedItems.map((item) => ({
        article: item.article,
        old_price: item.store_price,
        new_price: item.supplier_price,
        supplier_name: item.supplier_name,
        store_name: item.store_name
      }));
      
      // В реальном приложении мы бы вызывали API
      // const updatedPrices = await priceService.updatePrices(updates, state.storeFile);
      // const result = await priceService.saveUpdatedFile(state.storeFile, updatedPrices);
      
      // Для примера используем моки
      setTimeout(() => {
        setSuccess(true);
        setDownloadUrl('/uploads/mock-updated-file.xlsx');
        setLoading(false);
      }, 1500);
      
    } catch (err: any) {
      setError('Ошибка при обновлении цен: ' + (err.message || 'Неизвестная ошибка'));
      setLoading(false);
    }
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
            onClick={() => navigate('/comparison')}
          >
            Вернуться к сравнению
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
            Обновляем цены...
          </Typography>
        </Box>
      </Container>
    );
  }
  
  if (success) {
    return (
      <Container maxWidth="lg">
        <Box sx={{ mt: 3 }}>
          <Alert severity="success" sx={{ mb: 3 }}>
            Цены успешно обновлены! Обновлено товаров: {selectedItems.length}
          </Alert>
          
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Скачать обновленный прайс-лист
            </Typography>
            
            <Typography paragraph>
              Вы можете скачать обновленный прайс-лист магазина с новыми ценами.
            </Typography>
            
            <Box sx={{ mt: 3 }}>
              <Button 
                variant="contained" 
                color="primary" 
                component={Link}
                href={downloadUrl || '#'}
                download
                disabled={!downloadUrl}
              >
                Скачать прайс-лист
              </Button>
            </Box>
          </Paper>
          
          <Box sx={{ mt: 3, display: 'flex', gap: 2 }}>
            <Button 
              variant="outlined" 
              onClick={() => navigate('/comparison')}
            >
              Вернуться к сравнению
            </Button>
            
            <Button 
              variant="outlined" 
              onClick={() => navigate('/')}
            >
              На главную
            </Button>
          </Box>
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
          Выберите товары, цены которых нужно обновить
        </Typography>
      </Box>
      
      <Paper sx={{ p: 3, mb: 4 }}>
        <Typography variant="body1" paragraph>
          Выбрано товаров для обновления: <strong>{selectedItems.length}</strong>
        </Typography>
        
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell padding="checkbox">
                  <Checkbox
                    indeterminate={
                      selectedItems.length > 0 && 
                      selectedItems.length < (state?.selectedItems?.length || 0)
                    }
                    checked={
                      (state?.selectedItems?.length || 0) > 0 && 
                      selectedItems.length === (state?.selectedItems?.length || 0)
                    }
                    onChange={handleSelectAll}
                  />
                </TableCell>
                <TableCell>Артикул</TableCell>
                <TableCell>Название товара</TableCell>
                <TableCell>Текущая цена</TableCell>
                <TableCell>Новая цена</TableCell>
                <TableCell>Разница</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {state?.selectedItems?.map((item) => {
                const isItemSelected = isSelected(item.article);
                
                return (
                  <TableRow
                    key={item.article}
                    hover
                    onClick={() => handleSelectItem(item)}
                    role="checkbox"
                    aria-checked={isItemSelected}
                    selected={isItemSelected}
                  >
                    <TableCell padding="checkbox">
                      <Checkbox checked={isItemSelected} />
                    </TableCell>
                    <TableCell>{item.article}</TableCell>
                    <TableCell>{item.store_name || item.supplier_name}</TableCell>
                    <TableCell>{item.store_price.toFixed(2)} ₽</TableCell>
                    <TableCell>{item.supplier_price.toFixed(2)} ₽</TableCell>
                    <TableCell
                      sx={{
                        color: item.price_diff < 0 ? 'red' : 'green'
                      }}
                    >
                      {item.price_diff.toFixed(2)} ₽ ({item.price_diff_percent.toFixed(2)}%)
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>
      
      <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
        <Button
          variant="outlined"
          onClick={() => navigate('/comparison')}
        >
          Назад к сравнению
        </Button>
        
        <Button
          variant="contained"
          color="primary"
          onClick={handleUpdatePrices}
          disabled={selectedItems.length === 0}
        >
          Обновить цены ({selectedItems.length})
        </Button>
      </Box>
    </Container>
  );
};

export default PriceUpdatePage; 