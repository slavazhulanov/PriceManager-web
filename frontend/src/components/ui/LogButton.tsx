import React from 'react';
import { Button, ButtonProps } from '@mui/material';
import logger from '../../services/logger';

interface LogButtonProps extends ButtonProps {
  /**
   * Имя кнопки для логирования
   */
  logName: string;
  
  /**
   * Название страницы, на которой расположена кнопка
   */
  pageName: string;
  
  /**
   * Дополнительные данные для логирования
   */
  logDetails?: Record<string, any>;
}

/**
 * Кнопка, которая автоматически логирует клики
 */
const LogButton: React.FC<LogButtonProps> = ({
  logName,
  pageName,
  logDetails = {},
  onClick,
  children,
  ...props
}) => {
  
  const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
    // Логируем клик
    logger.logButtonClick(logName, pageName, logDetails);
    
    // Вызываем оригинальный обработчик, если он есть
    onClick?.(e);
  };
  
  return (
    <Button
      {...props}
      onClick={handleClick}
    >
      {children}
    </Button>
  );
};

export default LogButton; 