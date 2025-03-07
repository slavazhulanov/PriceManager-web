import React from 'react';
import { 
  Typography, 
  Box, 
  Container, 
  Button, 
  Grid, 
  Card, 
  CardContent, 
  CardActions,
  Divider
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import CompareArrowsIcon from '@mui/icons-material/CompareArrows';
import UpdateIcon from '@mui/icons-material/Update';

const HomePage: React.FC = () => {
  const navigate = useNavigate();
  
  return (
    <Container maxWidth="lg">
      <Box sx={{ my: 4, textAlign: 'center' }}>
        <Typography variant="h3" component="h1" gutterBottom>
          PriceManager
        </Typography>
        <Typography variant="h5" color="text.secondary" paragraph>
          Система управления ценами для вашего бизнеса
        </Typography>
        <Typography variant="body1" paragraph sx={{ maxWidth: 700, mx: 'auto', mb: 4 }}>
          PriceManager помогает сравнивать цены поставщиков с ценами в вашем магазине,
          выявлять расхождения и автоматизировать обновление цен.
        </Typography>
        
        <Divider sx={{ my: 4 }} />
        
        <Typography variant="h5" gutterBottom sx={{ mt: 6, mb: 3 }}>
          Основные возможности
        </Typography>
        
        <Grid container spacing={4} justifyContent="center">
          <Grid item xs={12} sm={6} md={4}>
            <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
              <CardContent sx={{ flexGrow: 1 }}>
                <Box sx={{ display: 'flex', justifyContent: 'center', mb: 2 }}>
                  <CloudUploadIcon color="primary" sx={{ fontSize: 60 }} />
                </Box>
                <Typography variant="h5" component="h2" gutterBottom>
                  Загрузка файлов
                </Typography>
                <Typography>
                  Загружайте прайс-листы поставщиков и данные из вашего магазина в различных форматах.
                  Система автоматически определит структуру данных.
                </Typography>
              </CardContent>
              <CardActions>
                <Button 
                  size="large" 
                  fullWidth 
                  variant="contained" 
                  onClick={() => navigate('/upload')}
                >
                  Загрузить файлы
                </Button>
              </CardActions>
            </Card>
          </Grid>
          
          <Grid item xs={12} sm={6} md={4}>
            <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
              <CardContent sx={{ flexGrow: 1 }}>
                <Box sx={{ display: 'flex', justifyContent: 'center', mb: 2 }}>
                  <CompareArrowsIcon color="primary" sx={{ fontSize: 60 }} />
                </Box>
                <Typography variant="h5" component="h2" gutterBottom>
                  Сравнение цен
                </Typography>
                <Typography>
                  Сравнивайте цены поставщиков с ценами в вашем магазине.
                  Выявляйте товары с наибольшей разницей в цене и принимайте решения на основе данных.
                </Typography>
              </CardContent>
              <CardActions>
                <Button 
                  size="large" 
                  fullWidth 
                  variant="contained" 
                  onClick={() => navigate('/comparison')}
                  color="primary"
                >
                  Сравнить цены
                </Button>
              </CardActions>
            </Card>
          </Grid>
          
          <Grid item xs={12} sm={6} md={4}>
            <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
              <CardContent sx={{ flexGrow: 1 }}>
                <Box sx={{ display: 'flex', justifyContent: 'center', mb: 2 }}>
                  <UpdateIcon color="primary" sx={{ fontSize: 60 }} />
                </Box>
                <Typography variant="h5" component="h2" gutterBottom>
                  Обновление цен
                </Typography>
                <Typography>
                  Автоматически обновляйте цены в вашем магазине на основе данных поставщиков.
                  Выбирайте товары для обновления и контролируйте процесс.
                </Typography>
              </CardContent>
              <CardActions>
                <Button 
                  size="large" 
                  fullWidth 
                  variant="contained" 
                  onClick={() => navigate('/upload')}
                  color="primary"
                >
                  Начать работу
                </Button>
              </CardActions>
            </Card>
          </Grid>
        </Grid>
      </Box>
    </Container>
  );
};

export default HomePage; 