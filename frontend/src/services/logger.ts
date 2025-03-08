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
  }
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
  if (actionBuffer.length === 0 || isTransmitting) return;
  
  // Предотвращаем параллельные отправки
  isTransmitting = true;
  
  try {
    // Копируем буфер и очищаем оригинал
    const actionsToSend = [...actionBuffer];
    actionBuffer = [];
    
    // Отправляем данные на сервер
    try {
      const endpoint = actionsToSend.length === 1 ? 'logs/user-action' : 'logs/user-actions/batch';
      const payload = actionsToSend.length === 1 ? actionsToSend[0] : actionsToSend;
      
      await loggerApi.post(endpoint, payload);
      
      if (isDev) {
        console.log(`[UserAction] Отправлено ${actionsToSend.length} действий на сервер`);
      }
    } catch (error) {
      // В продакшене просто логируем ошибку в консоль, без повторной отправки
      console.warn('Ошибка отправки логов на сервер:', error);
      
      // В режиме разработки выводим детали ошибки
      if (process.env.NODE_ENV === 'development') {
        console.error('Детальная информация об ошибке логирования:', error);
      }
      
      // Не возвращаем действия обратно в буфер, чтобы избежать зацикливания при постоянных ошибках
      if (process.env.NODE_ENV !== 'production') {
        console.warn('Данные логирования не будут отправлены на сервер. Это не влияет на основную функциональность приложения.');
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