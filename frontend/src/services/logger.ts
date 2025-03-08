import axios from 'axios';

// Определение базового URL API в зависимости от окружения
const getApiUrl = () => {
  // В продакшн на Vercel мы используем API с префиксом /api
  if (process.env.NODE_ENV === 'production') {
    return '/api/v1';
  }
  // В локальной разработке используем полный URL
  return 'http://localhost:8000/api/v1';
};

const API_URL = getApiUrl();

// Создаем экземпляр axios для логирования
const loggerApi = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  // Добавляем таймаут и отключаем повторные попытки
  timeout: 3000
});

/**
 * Типы действий пользователя
 */
export enum UserActionType {
  BUTTON_CLICK = 'button_click',
  LINK_CLICK = 'link_click',
  FORM_SUBMIT = 'form_submit',
  FILE_UPLOAD = 'file_upload',
  DROPDOWN_SELECT = 'dropdown_select',
  PAGE_VIEW = 'page_view',
  TAB_SWITCH = 'tab_switch',
  MODAL_OPEN = 'modal_open',
  MODAL_CLOSE = 'modal_close',
  ITEM_SELECT = 'item_select',
  ROW_EXPAND = 'row_expand',
  CHECKBOX_TOGGLE = 'checkbox_toggle',
  RADIO_SELECT = 'radio_select',
}

/**
 * Интерфейс действия пользователя
 */
export interface UserAction {
  action_type: UserActionType | string;
  component: string;
  page: string;
  details?: Record<string, any>;
  timestamp?: string;
}

// Буфер для накопления действий перед отправкой
let actionBuffer: UserAction[] = [];
let isTransmitting = false;
let sendInterval: NodeJS.Timeout | null = null;

// Режим разработки или продакшн
const isDev = process.env.NODE_ENV === 'development';

// Флаг, показывающий, что логирование недоступно
let loggingUnavailable = false;
// Счетчик неудачных попыток
let failedAttempts = 0;

// Определяем, работаем ли мы на Vercel
const isVercel = () => {
  return window.location.hostname.includes('vercel.app') || 
         window.location.hostname.includes('now.sh');
};

// Флаг, показывающий что мы находимся в Vercel и логирование отключено
const isVercelEnv = isVercel();

/**
 * Логирование действия пользователя
 */
export const logUserAction = (
  actionType: UserActionType | string,
  component: string,
  page: string,
  details: Record<string, any> = {}
) => {
  // Создаем объект действия
  const action: UserAction = {
    action_type: actionType,
    component,
    page,
    details,
    timestamp: new Date().toISOString(),
  };
  
  // Выводим в консоль в режиме разработки
  if (isDev) {
    console.log(`[UserAction] ${action.action_type} | ${action.component} | ${action.page}`, details);
  }
  
  // Добавляем в буфер
  actionBuffer.push(action);
  
  // Планируем отправку буфера
  scheduleBufferSend();
};

/**
 * Логирование клика на кнопку
 */
export const logButtonClick = (buttonName: string, page: string, details: Record<string, any> = {}) => {
  logUserAction(UserActionType.BUTTON_CLICK, buttonName, page, details);
};

/**
 * Логирование перехода по ссылке
 */
export const logLinkClick = (linkName: string, page: string, destination: string) => {
  logUserAction(UserActionType.LINK_CLICK, linkName, page, { destination });
};

/**
 * Логирование отправки формы
 */
export const logFormSubmit = (formName: string, page: string, formData: Record<string, any> = {}) => {
  // Убираем чувствительные данные
  const safeFormData = { ...formData };
  
  // Удаляем пароли и другие чувствительные поля
  ['password', 'token', 'secret', 'key'].forEach(key => {
    if (key in safeFormData) {
      safeFormData[key] = '[REDACTED]';
    }
  });
  
  logUserAction(UserActionType.FORM_SUBMIT, formName, page, safeFormData);
};

/**
 * Логирование переключения вкладок
 */
export const logTabSwitch = (tabName: string, page: string) => {
  logUserAction(UserActionType.TAB_SWITCH, tabName, page);
};

/**
 * Логирование выбора из выпадающего списка
 */
export const logDropdownSelect = (dropdownName: string, page: string, selectedValue: string) => {
  logUserAction(UserActionType.DROPDOWN_SELECT, dropdownName, page, { selected_value: selectedValue });
};

/**
 * Логирование загрузки файла
 */
export const logFileUpload = (inputName: string, page: string, fileName: string, fileSize: number, fileType: string) => {
  logUserAction(UserActionType.FILE_UPLOAD, inputName, page, { 
    file_name: fileName, 
    file_size: fileSize, 
    file_type: fileType 
  });
};

/**
 * Логирование просмотра страницы
 */
export const logPageView = (page: string, referrer: string = '') => {
  logUserAction(UserActionType.PAGE_VIEW, 'page', page, { referrer });
};

// Отправка буфера действий на сервер
const sendBuffer = async () => {
  // Если буфер пуст или уже идет отправка, ничего не делаем
  if (actionBuffer.length === 0 || isTransmitting) {
    return;
  }
  
  // Если мы на Vercel, просто очищаем буфер и не отправляем логи
  if (isVercelEnv) {
    if (process.env.NODE_ENV === 'development') {
      console.log(`[Logger] Vercel среда: ${actionBuffer.length} действий НЕ отправлены на сервер`);
    }
    actionBuffer = [];
    return;
  }
  
  // Если логирование отключено после множества ошибок, просто очищаем буфер
  if (loggingUnavailable) {
    if (process.env.NODE_ENV === 'development') {
      console.warn('Логирование отключено из-за предыдущих ошибок. Действия не будут отправлены на сервер.');
    }
    actionBuffer = [];
    return;
  }
  
  isTransmitting = true;
  const actionsToSend = [...actionBuffer];
  actionBuffer = [];
  
  try {
    // Попытка отправки логов
    if (actionsToSend.length === 1) {
      await loggerApi.post('/logs/user-action', actionsToSend[0]);
    } else {
      await loggerApi.post('/logs/user-actions/batch', actionsToSend);
    }
    
    // Успешная отправка - сбрасываем счетчик неудачных попыток
    failedAttempts = 0;
    
    if (process.env.NODE_ENV === 'development') {
      console.debug(`Отправлено ${actionsToSend.length} лог-событий`);
    }
  } catch (error) {
    failedAttempts++;
    
    // Если много ошибок подряд, отключаем логирование
    if (failedAttempts > 3) {
      loggingUnavailable = true;
      if (process.env.NODE_ENV === 'development') {
        console.error('Слишком много ошибок при отправке логов. Логирование отключено.');
      }
    } else {
      if (process.env.NODE_ENV === 'development') {
        console.warn(`Ошибка при отправке логов (попытка ${failedAttempts}/3):`, error);
      }
    }
  } finally {
    isTransmitting = false;
  }
};

/**
 * Планирование отправки буфера
 */
const scheduleBufferSend = () => {
  // Если уже есть запланированная отправка - не планируем новую
  if (sendInterval) return;
  
  // Планируем отправку через 2 секунды бездействия
  sendInterval = setTimeout(() => {
    sendInterval = null;
    sendBuffer();
  }, 2000);
  
  // Если буфер слишком большой - отправляем сразу
  if (actionBuffer.length >= 10) {
    if (sendInterval) {
      clearTimeout(sendInterval);
      sendInterval = null;
    }
    sendBuffer();
  }
};

/**
 * Отправка всех накопленных логов перед выходом со страницы
 */
export const flushLogs = () => {
  if (sendInterval) {
    clearTimeout(sendInterval);
    sendInterval = null;
  }
  
  sendBuffer();
};

// Отправляем логи перед выходом со страницы
if (typeof window !== 'undefined') {
  window.addEventListener('beforeunload', flushLogs);
}

export default {
  logUserAction,
  logButtonClick,
  logLinkClick,
  logFormSubmit,
  logTabSwitch,
  logDropdownSelect,
  logFileUpload,
  logPageView,
  flushLogs,
}; 