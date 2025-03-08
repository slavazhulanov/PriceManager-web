import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { 
  Box, 
  Typography, 
  Paper, 
  CircularProgress, 
  Alert,
  Button,
  Chip,
  Stack,
  LinearProgress
} from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import { FileType } from '../../types';
import { fileService } from '../../services/api';

interface FileDropzoneProps {
  fileType: FileType;
  onFileUploaded: (fileInfo: any) => void;
  title: string;
  description?: string;
  accepts?: string[];
  maxSize?: number;
  isUploaded?: boolean;
}

const FileDropzone: React.FC<FileDropzoneProps> = ({
  fileType,
  onFileUploaded,
  title,
  description,
  accepts = ['.xlsx', '.xls', '.csv'],
  maxSize = 10 * 1024 * 1024, // 10MB по умолчанию
  isUploaded = false
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fileUploaded, setFileUploaded] = useState(isUploaded);
  const [fileName, setFileName] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  
  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    // Проверяем, что был загружен только один файл
    if (acceptedFiles.length !== 1) {
      setError('Пожалуйста, загрузите только один файл.');
      return;
    }
    
    const file = acceptedFiles[0];
    setFileName(file.name);
    
    // Проверяем размер файла
    if (file.size > maxSize) {
      setError(`Размер файла превышает максимально допустимый (${maxSize / 1024 / 1024} МБ).`);
      return;
    }
    
    try {
      setLoading(true);
      setError(null);
      setUploadProgress(0);
      
      // Проверяем, используем ли реальный API или моки
      const useRealApi = process.env.NODE_ENV === 'production' || process.env.REACT_APP_USE_REAL_API === 'true';
      console.log(`Режим API: ${useRealApi ? 'Реальный API' : 'Mock API'}, file: ${file.name}`);
      
      if (useRealApi) {
        // Используем прямую загрузку в Supabase для производительности
        try {
          // Шаг 1: Получаем URL для загрузки
          console.log('Запрос URL для прямой загрузки в Supabase');
          const { uploadUrl, fileInfo } = await fileService.getUploadUrl(file.name, fileType);
          
          // Шаг 2: Загружаем файл напрямую в Supabase
          console.log('Начало прямой загрузки в Supabase', uploadUrl);
          setUploadProgress(10);
          
          // Имитируем прогресс загрузки
          const progressInterval = setInterval(() => {
            setUploadProgress(prev => {
              if (prev >= 90) {
                clearInterval(progressInterval);
                return 90;
              }
              return prev + 10;
            });
          }, 300);
          
          const uploadSuccess = await fileService.uploadToSupabase(file, uploadUrl);
          clearInterval(progressInterval);
          
          if (!uploadSuccess) {
            throw new Error('Не удалось загрузить файл в Supabase');
          }
          
          setUploadProgress(95);
          console.log('Файл успешно загружен в Supabase');
          
          // Шаг 3: Регистрируем файл в нашем API
          console.log('Регистрация файла в системе');
          const registeredFileInfo = await fileService.registerUploadedFile(fileInfo);
          
          setUploadProgress(100);
          console.log('Файл успешно зарегистрирован:', registeredFileInfo);
          
          onFileUploaded(registeredFileInfo);
          setFileUploaded(true);
        } catch (supabaseError: any) {
          console.error('Ошибка при прямой загрузке в Supabase:', supabaseError);
          
          // Если прямая загрузка не удалась, используем резервный метод
          console.log('Использование резервного метода загрузки');
          const fileInfo = await fileService.uploadFile(file, fileType);
          onFileUploaded(fileInfo);
          setFileUploaded(true);
        }
      } else {
        // Для демонстрации просто имитируем загрузку
        console.log('Загрузка файла через Mock API');
        
        // Имитируем прогресс загрузки
        const progressInterval = setInterval(() => {
          setUploadProgress(prev => {
            if (prev >= 90) {
              clearInterval(progressInterval);
              return 90;
            }
            return prev + 10;
          });
        }, 200);
        
        setTimeout(() => {
          clearInterval(progressInterval);
          setUploadProgress(100);
          
          // Для файлов с mock_ в имени не добавляем префикс, иначе добавляем
          const mockFilename = file.name.toLowerCase().includes('mock_') 
            ? file.name 
            : 'mock_' + file.name;
            
          const fileInfo = {
            id: 'mock-id-' + Date.now(),
            original_filename: file.name,
            stored_filename: mockFilename,
            file_type: fileType,
            encoding: 'utf-8',
            separator: ','
          };
          
          console.log('Создан фейковый объект FileInfo:', fileInfo);
          onFileUploaded(fileInfo);
          setFileUploaded(true);
        }, 1000);
      }
    } catch (err: any) {
      setError(err.message || 'Произошла ошибка при загрузке файла.');
      console.error('Ошибка при загрузке файла:', err);
      setUploadProgress(0);
    } finally {
      setLoading(false);
    }
  }, [fileType, maxSize, onFileUploaded]);
  
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': accepts.includes('.xlsx') ? ['.xlsx'] : [],
      'application/vnd.ms-excel': accepts.includes('.xls') ? ['.xls'] : [],
      'text/csv': accepts.includes('.csv') ? ['.csv'] : []
    },
    maxSize,
    multiple: false,
  });

  // Пример структуры файла в зависимости от типа
  const getFileExample = () => {
    if (fileType === FileType.SUPPLIER) {
      return (
        <Box sx={{ mt: 2, p: 1, bgcolor: 'rgba(0, 0, 0, 0.04)', borderRadius: 1, fontSize: '0.75rem' }}>
          <Typography variant="caption" sx={{ fontWeight: 'bold' }}>Пример структуры файла:</Typography>
          <pre style={{ margin: '5px 0', overflow: 'auto' }}>
            Артикул;Наименование;Цена;Остаток{'\n'}
            10001;Смартфон Samsung;29990;10{'\n'}
            10002;Ноутбук ASUS;49990;5
          </pre>
        </Box>
      );
    } else {
      return (
        <Box sx={{ mt: 2, p: 1, bgcolor: 'rgba(0, 0, 0, 0.04)', borderRadius: 1, fontSize: '0.75rem' }}>
          <Typography variant="caption" sx={{ fontWeight: 'bold' }}>Пример структуры файла:</Typography>
          <pre style={{ margin: '5px 0', overflow: 'auto' }}>
            Код;Товар;Стоимость;Количество{'\n'}
            10001;Samsung Galaxy;31990;8{'\n'}
            10002;ASUS VivoBook;54990;3
          </pre>
        </Box>
      );
    }
  };
  
  return (
    <Paper
      sx={{
        p: 3,
        border: '2px dashed',
        borderColor: fileUploaded ? 'success.main' : isDragActive ? 'primary.main' : 'divider',
        backgroundColor: fileUploaded 
          ? 'rgba(76, 175, 80, 0.04)' 
          : isDragActive 
            ? 'rgba(25, 118, 210, 0.04)' 
            : 'background.paper',
        transition: 'all 0.3s ease',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      {error && (
        <Alert severity="error" sx={{ mb: 2, width: '100%' }}>
          {error}
        </Alert>
      )}
      
      {uploadProgress > 0 && uploadProgress < 100 && (
        <Box sx={{ width: '100%', mb: 2 }}>
          <LinearProgress variant="determinate" value={uploadProgress} />
          <Typography variant="caption" align="center" display="block" sx={{ mt: 1 }}>
            Загрузка файла: {uploadProgress}%
          </Typography>
        </Box>
      )}
      
      {fileUploaded ? (
        <Box sx={{ 
            display: 'flex', 
            flexDirection: 'column', 
            alignItems: 'center', 
            width: '100%',
            py: 2 
          }}>
          <CheckCircleIcon color="success" sx={{ fontSize: 48, mb: 2 }} />
          <Typography variant="h6" gutterBottom align="center" color="success.main">
            Файл успешно загружен
          </Typography>
          {fileName && (
            <Chip 
              label={fileName} 
              color="success" 
              variant="outlined" 
              sx={{ mt: 1 }} 
            />
          )}
          <Button 
            variant="outlined" 
            color="primary" 
            sx={{ mt: 2 }}
            {...getRootProps()}
          >
            <input {...getInputProps()} />
            Загрузить другой файл
          </Button>
        </Box>
      ) : (
        <Box
          {...getRootProps()}
          sx={{
            p: 3,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            cursor: 'pointer',
            width: '100%',
            height: '100%',
            justifyContent: 'center',
          }}
        >
          <input {...getInputProps()} />
          
          {loading ? (
            <CircularProgress />
          ) : (
            <>
              <CloudUploadIcon color="primary" sx={{ fontSize: 48, mb: 2 }} />
              <Typography variant="h6" gutterBottom align="center">
                {title}
              </Typography>
              {description && (
                <Typography variant="body2" color="text.secondary" align="center" sx={{ mb: 1 }}>
                  {description}
                </Typography>
              )}
              <Typography variant="body2" color="text.secondary" align="center">
                Перетащите файл сюда или нажмите для выбора
              </Typography>
              <Stack direction="row" spacing={1} sx={{ mt: 1, mb: 2, flexWrap: 'wrap', justifyContent: 'center' }}>
                {accepts.map(format => (
                  <Chip key={format} label={format} size="small" variant="outlined" sx={{ m: 0.5 }} />
                ))}
              </Stack>
              <Button variant="contained" color="primary">
                Выбрать файл
              </Button>
              {getFileExample()}
            </>
          )}
        </Box>
      )}
    </Paper>
  );
};

export default FileDropzone; 