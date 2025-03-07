import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import logger, { UserActionType } from '../services/logger';

/**
 * Хук для логирования действий пользователя в React-компонентах
 */
export const useLogger = (page: string) => {
  const location = useLocation();
  
  // Логирование просмотра страницы при монтировании компонента
  useEffect(() => {
    // Определяем предыдущую страницу из истории
    const referrer = document.referrer || 'direct';
    
    // Логируем просмотр страницы
    logger.logPageView(page, referrer);
    
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page]);
  
  // Логирование изменения URL
  useEffect(() => {
    // Логируем изменение URL, но только если это не начальная загрузка
    if (location.key !== 'default') {
      logger.logUserAction('url_change', 'router', page, {
        pathname: location.pathname,
        search: location.search,
        hash: location.hash,
      });
    }
    
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.pathname, location.search, location.hash]);
  
  return {
    /**
     * Логирование клика на кнопку
     */
    logButtonClick: (buttonName: string, details = {}) => {
      logger.logButtonClick(buttonName, page, details);
    },
    
    /**
     * Логирование перехода по ссылке
     */
    logLinkClick: (linkName: string, destination: string) => {
      logger.logLinkClick(linkName, page, destination);
    },
    
    /**
     * Логирование отправки формы
     */
    logFormSubmit: (formName: string, formData = {}) => {
      logger.logFormSubmit(formName, page, formData);
    },
    
    /**
     * Логирование выбора вкладки
     */
    logTabSwitch: (tabName: string) => {
      logger.logTabSwitch(tabName, page);
    },
    
    /**
     * Логирование выбора из выпадающего списка
     */
    logDropdownSelect: (dropdownName: string, selectedValue: string) => {
      logger.logDropdownSelect(dropdownName, page, selectedValue);
    },
    
    /**
     * Логирование загрузки файла
     */
    logFileUpload: (inputName: string, fileName: string, fileSize: number, fileType: string) => {
      logger.logFileUpload(inputName, page, fileName, fileSize, fileType);
    },
    
    /**
     * Логирование действия пользователя (общий метод)
     */
    logUserAction: (actionType: UserActionType | string, component: string, details = {}) => {
      logger.logUserAction(actionType, component, page, details);
    },
  };
};

export default useLogger; 