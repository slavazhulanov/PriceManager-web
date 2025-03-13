// Удаляем неиспользуемый импорт
// import { format } from 'date-fns';

interface LogEntry {
    timestamp: string;
    level: string;
    message: string;
    data?: any;
    trace_id?: string;
    user_id?: string;
}

interface UserAction {
    action_type: string;
    component: string;
    page: string;
    details?: Record<string, any>;
    timestamp: string;
}

interface ILogger {
    debug(message: string, data?: any): void;
    info(message: string, data?: any): void;
    warn(message: string, data?: any): void;
    error(message: string, data?: any): void;
    track(event: string, properties?: any): void;
    logUserAction(actionType: string, component: string, page: string, details?: Record<string, any>): void;
    setUserId(userId: string): void;
    setTraceId(traceId: string): void;
    forceFlush(): Promise<void>;
}

class Logger implements ILogger {
    private static instance: Logger;
    private buffer: (LogEntry | UserAction)[] = [];
    private isTransmitting = false;
    private flushInterval: number = 5000; // 5 секунд
    private maxBufferSize: number = 100;
    private intervalId?: NodeJS.Timeout;

    private constructor() {
        this.setupErrorHandling();
        this.startFlushInterval();
    }

    public static getInstance(): Logger {
        if (!Logger.instance) {
            Logger.instance = new Logger();
        }
        return Logger.instance;
    }

    private setupErrorHandling() {
        if (typeof window !== 'undefined') {
            // Перехватываем консольные логи
            const originalConsoleLog = console.log;
            const originalConsoleError = console.error;
            const originalConsoleWarn = console.warn;

            console.log = (...args) => {
                this.debug('Console log', { args });
                originalConsoleLog.apply(console, args);
            };

            console.error = (...args) => {
                this.error('Console error', { args });
                originalConsoleError.apply(console, args);
            };

            console.warn = (...args) => {
                this.warn('Console warning', { args });
                originalConsoleWarn.apply(console, args);
            };

            // Перехватываем необработанные ошибки
            window.onerror = (message, source, lineno, colno, error) => {
                this.error('Unhandled error', {
                    message,
                    source,
                    lineno,
                    colno,
                    stack: error?.stack
                });
                return false;
            };

            // Перехватываем ошибки в промисах
            window.onunhandledrejection = (event) => {
                this.error('Unhandled promise rejection', {
                    reason: event.reason
                });
            };

            // Перехватываем ошибки в React
            const originalError = console.error;
            console.error = (...args) => {
                if (args[0]?.includes?.('React error')) {
                    this.error('React error', { args });
                }
                originalError.apply(console, args);
            };
        }
    }

    private startFlushInterval() {
        if (typeof window !== 'undefined') {
            this.intervalId = setInterval(() => this.flush(), this.flushInterval);
            // Очищаем интервал при закрытии страницы
            window.addEventListener('beforeunload', () => {
                if (this.intervalId) {
                    clearInterval(this.intervalId);
                }
                this.flush();
            });
        }
    }

    private async flush(): Promise<void> {
        if (this.buffer.length === 0) return;

        try {
            // Разделяем логи и действия пользователя
            const logs = this.buffer.filter(entry => 'level' in entry) as LogEntry[];
            const userActions = this.buffer.filter(entry => 'action_type' in entry) as UserAction[];

            // Отправляем логи
            if (logs.length > 0) {
                const response = await fetch('/api/v1/logs/frontend/batch', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(logs),
                });

                if (!response.ok) {
                    throw new Error(`Failed to send logs: ${response.statusText}`);
                }
            }

            // Отправляем действия пользователя
            if (userActions.length > 0) {
                const response = await fetch('/api/v1/logs/user-actions/batch', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(userActions),
                });

                if (!response.ok) {
                    throw new Error(`Failed to send user actions: ${response.statusText}`);
                }
            }

            // Очищаем буфер только если все отправки прошли успешно
            this.buffer = [];
        } catch (error) {
            console.warn('Сервер логирования недоступен, логи будут сохранены только локально:', error);
            // Не очищаем буфер в случае ошибки, чтобы попробовать отправить позже
        }
    }

    private createLogEntry(level: string, message: string, data?: any): LogEntry {
        return {
            timestamp: new Date().toISOString(),
            level,
            message,
            data,
            trace_id: this.getTraceId() || "",
            user_id: this.getUserId() || ""
        };
    }

    private getTraceId(): string | undefined {
        return localStorage.getItem('trace_id') || undefined;
    }

    private getUserId(): string | undefined {
        return localStorage.getItem('user_id') || undefined;
    }

    private addToBuffer(entry: LogEntry | UserAction) {
        this.buffer.push(entry);
        if (this.buffer.length >= this.maxBufferSize) {
            this.flush();
        }
    }

    public debug(message: string, data?: any) {
        this.addToBuffer(this.createLogEntry('DEBUG', message, data));
    }

    public info(message: string, data?: any) {
        this.addToBuffer(this.createLogEntry('INFO', message, data));
    }

    public warn(message: string, data?: any) {
        this.addToBuffer(this.createLogEntry('WARN', message, data));
    }

    public error(message: string, data?: any) {
        this.addToBuffer(this.createLogEntry('ERROR', message, data));
    }

    public track(event: string, properties?: any) {
        this.addToBuffer(this.createLogEntry('TRACK', event, properties));
    }

    public logUserAction(actionType: string, component: string, page: string, details?: Record<string, any>) {
        const action: UserAction = {
            action_type: actionType,
            component,
            page,
            details,
            timestamp: new Date().toISOString()
        };
        this.addToBuffer(action);
    }

    public setUserId(userId: string) {
        localStorage.setItem('user_id', userId);
    }

    public setTraceId(traceId: string) {
        localStorage.setItem('trace_id', traceId);
    }

    public async forceFlush() {
        await this.flush();
    }

    public logButtonClick(buttonName: string, pageName: string, details?: Record<string, any>) {
        this.logUserAction('button_click', buttonName, pageName, details);
    }
}

export const logger = Logger.getInstance(); 