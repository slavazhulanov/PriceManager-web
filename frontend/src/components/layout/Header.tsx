import React from 'react';
import { 
  AppBar, 
  Toolbar, 
  Typography, 
  Button, 
  Box, 
  Container,
  useTheme
} from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';
import CompareArrowsIcon from '@mui/icons-material/CompareArrows';

const Header: React.FC = () => {
  return (
    <AppBar position="static">
      <Container maxWidth="lg">
        <Toolbar>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <CompareArrowsIcon sx={{ mr: 1 }} />
            <Typography
              variant="h6"
              component={RouterLink}
              to="/"
              sx={{
                textDecoration: 'none',
                color: 'white',
                fontWeight: 'bold',
                flexGrow: 1,
                display: { xs: 'none', sm: 'block' }
              }}
            >
              PriceManager
            </Typography>
          </Box>
          
          <Box sx={{ flexGrow: 1 }} />
          
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button 
              color="inherit" 
              component={RouterLink} 
              to="/"
            >
              Главная
            </Button>
            <Button 
              color="inherit" 
              component={RouterLink} 
              to="/upload"
            >
              Загрузка файлов
            </Button>
            <Button 
              color="inherit" 
              component={RouterLink} 
              to="/comparison"
            >
              Сравнение цен
            </Button>
          </Box>
        </Toolbar>
      </Container>
    </AppBar>
  );
};

export default Header; 