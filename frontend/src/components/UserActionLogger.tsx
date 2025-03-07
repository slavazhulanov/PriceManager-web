import React, { useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import logger from '../services/logger';

/**
 * Компонент для глобального отслеживания действий пользователя
 * Его нужно добавить в корневой компонент приложения
 */
export const UserActionLogger: React.FC = () => {
  const location = useLocation();
  
  // Отслеживаем изменение URL
  useEffect(() => {
    // Не логируем первоначальный URL при загрузке приложения
    if (location.key !== 'default') {
      const pageName = location.pathname.replace(/^\//, '') || 'home';
      
      logger.logUserAction('page_navigation', 'router', pageName, {
        from: document.referrer,
        to: location.pathname,
        search: location.search,
        hash: location.hash
      });
    }
  }, [location]);
  
  // Отслеживаем клики по всем элементам
  useEffect(() => {
    const handleGlobalClick = (e: MouseEvent) => {
      // Находим ближайший элемент с data-log-name (если есть)
      const target = e.target as HTMLElement;
      let currentNode: HTMLElement | null = target;
      
      while (currentNode && !currentNode.dataset.logName) {
        currentNode = currentNode.parentElement;
      }
      
      // Если нашли элемент с data-log-name, логируем действие
      if (currentNode && currentNode.dataset.logName) {
        const componentName = currentNode.dataset.logName;
        const pageName = currentNode.dataset.logPage || location.pathname.replace(/^\//, '') || 'unknown';
        const componentType = currentNode.dataset.logType || 'element';
        
        // Собираем дополнительные данные из data-log-* атрибутов
        const details: Record<string, any> = {};
        Object.entries(currentNode.dataset).forEach(([key, value]) => {
          if (key.startsWith('logData') && key !== 'logData') {
            const propName = key.replace('logData', '').toLowerCase();
            details[propName] = value;
          }
        });
        
        logger.logUserAction(`${componentType}_click`, componentName, pageName, details);
      }
    };
    
    // Добавляем глобальный обработчик кликов
    document.addEventListener('click', handleGlobalClick);
    
    return () => {
      document.removeEventListener('click', handleGlobalClick);
    };
  }, [location]);
  
  // Отслеживаем отправки форм
  useEffect(() => {
    const handleFormSubmit = (e: Event) => {
      const form = e.target as HTMLFormElement;
      if (form.dataset.logName) {
        const formName = form.dataset.logName;
        const pageName = form.dataset.logPage || location.pathname.replace(/^\//, '') || 'unknown';
        
        logger.logUserAction('form_submit', formName, pageName);
      }
    };
    
    // Добавляем глобальный обработчик отправки форм
    document.addEventListener('submit', handleFormSubmit);
    
    return () => {
      document.removeEventListener('submit', handleFormSubmit);
    };
  }, [location]);
  
  return null; // Это невидимый компонент
};

export default UserActionLogger; 