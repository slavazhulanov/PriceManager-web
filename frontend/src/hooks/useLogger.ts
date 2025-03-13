import { useEffect, useCallback, useMemo } from 'react';
import { useLocation } from 'react-router-dom';
import { logger } from '../utils/logger';

export interface LoggerContextData {
    componentName?: string;
    userId?: string;
    additionalData?: Record<string, any>;
}

/**
 * Хук для логирования действий пользователя в React-компонентах
 */
export const useLogger = (context?: LoggerContextData | string) => {
    const location = useLocation();
    
    // Преобразуем строковый контекст в LoggerContextData и оборачиваем в useMemo
    const contextData = useMemo(() => {
        return typeof context === 'string' 
            ? { componentName: context } 
            : context || {};
    }, [context]);

    useEffect(() => {
        // Логируем переход на новую страницу
        if (location.key !== 'default') {
            logger.track('page_view', {
                path: location.pathname,
                search: location.search,
                hash: location.hash,
                ...contextData?.additionalData
            });
        }
    }, [location, contextData?.additionalData]);

    const logEvent = useCallback((
        eventName: string,
        eventData?: Record<string, any>
    ) => {
        logger.track(eventName, {
            component: contextData?.componentName,
            path: location.pathname,
            userId: contextData?.userId,
            ...contextData?.additionalData,
            ...eventData
        });
    }, [location.pathname, contextData]);

    const logError = useCallback((
        error: Error | string,
        errorContext?: Record<string, any>
    ) => {
        const errorMessage = error instanceof Error ? error.message : error;
        const errorStack = error instanceof Error ? error.stack : undefined;

        logger.error(errorMessage, {
            component: contextData?.componentName,
            path: location.pathname,
            userId: contextData?.userId,
            stack: errorStack,
            ...contextData?.additionalData,
            ...errorContext
        });
    }, [location.pathname, contextData]);

    const logInfo = useCallback((
        message: string,
        data?: Record<string, any>
    ) => {
        logger.info(message, {
            component: contextData?.componentName,
            path: location.pathname,
            userId: contextData?.userId,
            ...contextData?.additionalData,
            ...data
        });
    }, [location.pathname, contextData]);

    const logWarning = useCallback((
        message: string,
        data?: Record<string, any>
    ) => {
        logger.warn(message, {
            component: contextData?.componentName,
            path: location.pathname,
            userId: contextData?.userId,
            ...contextData?.additionalData,
            ...data
        });
    }, [location.pathname, contextData]);

    const logDebug = useCallback((
        message: string,
        data?: Record<string, any>
    ) => {
        logger.debug(message, {
            component: contextData?.componentName,
            path: location.pathname,
            userId: contextData?.userId,
            ...contextData?.additionalData,
            ...data
        });
    }, [location.pathname, contextData]);

    // Специальные логгеры для UI событий
    const logClick = useCallback((
        elementName: string,
        data?: Record<string, any>
    ) => {
        logEvent('click', {
            element: elementName,
            ...data
        });
    }, [logEvent]);

    const logFormSubmit = useCallback((
        formName: string,
        data?: Record<string, any>
    ) => {
        logEvent('form_submit', {
            form: formName,
            ...data
        });
    }, [logEvent]);

    const logInputChange = useCallback((
        inputName: string,
        data?: Record<string, any>
    ) => {
        logEvent('input_change', {
            input: inputName,
            ...data
        });
    }, [logEvent]);

    // Добавляем функцию logUserAction для совместимости
    const logUserAction = useCallback((
        actionType: string,
        component: string,
        details?: Record<string, any>
    ) => {
        logger.logUserAction(
            actionType,
            component || contextData?.componentName || 'unknown',
            location.pathname,
            details
        );
    }, [location.pathname, contextData?.componentName]);

    // Добавляем функцию logTabSwitch для совместимости
    const logTabSwitch = useCallback((
        tabName: string
    ) => {
        logUserAction('tab_switch', 'tabs', { tab: tabName });
    }, [logUserAction]);

    return {
        logEvent,
        logError,
        logInfo,
        logWarning,
        logDebug,
        logClick,
        logFormSubmit,
        logInputChange,
        // Добавляем новые функции в возвращаемый объект
        logUserAction,
        logTabSwitch
    };
};

export default useLogger; 