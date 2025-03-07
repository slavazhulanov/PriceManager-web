import React, { ComponentType, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import logger from '../../services/logger';

export interface WithLoggingProps {
  /**
   * Название компонента для логов
   */
  componentName?: string;
  
  /**
   * Дополнительные данные для логирования
   */
  logData?: Record<string, any>;
}

/**
 * HOC для логирования жизненного цикла компонента
 * @param Component Компонент для оборачивания
 * @param pageName Название страницы
 * @returns Компонент с логированием
 */
export const withLogging = <P extends object>(
  Component: ComponentType<P>,
  pageName: string
) => {
  const WithLoggingComponent: React.FC<P & WithLoggingProps> = (props) => {
    const { componentName = Component.displayName || Component.name || 'UnknownComponent', logData = {}, ...componentProps } = props;
    const location = useLocation();
    
    // Логирование монтирования компонента
    useEffect(() => {
      logger.logUserAction('component_mount', componentName, pageName, {
        pathname: location.pathname,
        ...logData
      });
      
      // Логирование размонтирования компонента
      return () => {
        logger.logUserAction('component_unmount', componentName, pageName, {
          pathname: location.pathname,
          ...logData
        });
      };
    }, []);
    
    return <Component {...(componentProps as P)} />;
  };
  
  // Устанавливаем отображаемое имя для компонента
  WithLoggingComponent.displayName = `withLogging(${Component.displayName || Component.name || 'Component'})`;
  
  return WithLoggingComponent;
};

export default withLogging; 