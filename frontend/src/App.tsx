import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { Container } from '@mui/material';

// Компоненты
import Header from './components/layout/Header';
import HomePage from './pages/HomePage';
import FileUploadPage from './pages/FileUploadPage';
import ComparisonPage from './pages/ComparisonPage';
import UpdatePricePage from './pages/UpdatePricePage';
import UserActionLogger from './components/UserActionLogger';

// Создаем тему для Material UI
const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
    background: {
      default: '#f5f5f5',
    },
  },
  typography: {
    fontFamily: [
      'Roboto',
      '"Helvetica Neue"',
      'Arial',
      'sans-serif',
    ].join(','),
  },
});

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <UserActionLogger />
        <Header />
        <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/upload" element={<FileUploadPage />} />
            <Route path="/comparison" element={<ComparisonPage />} />
            <Route path="/update-prices" element={<UpdatePricePage />} />
          </Routes>
        </Container>
      </Router>
    </ThemeProvider>
  );
}

export default App;
