const { createProxyMiddleware } = require('http-proxy-middleware');

/**
 * Настройка прокси-сервера для перенаправления запросов с фронтенда на бэкенд
 * @param {Object} app - Express-приложение
 */
module.exports = function(app) {
  // Настройка прокси для API
  app.use(
    '/api',
    createProxyMiddleware({
      target: 'http://localhost:8000',
      changeOrigin: true,
      secure: false,
      headers: {
        'Connection': 'keep-alive'
      },
      // Включаем поддержку WebSockets
      ws: true,
      // Необходимые заголовки для CORS
      onProxyRes: function(proxyRes, req, res) {
        proxyRes.headers['Access-Control-Allow-Origin'] = '*';
        proxyRes.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS';
        proxyRes.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization';
      },
      // Обработка ошибок
      onError: function(err, req, res) {
        console.error('Proxy Error:', err);
        res.writeHead(500, {
          'Content-Type': 'application/json',
        });
        res.end(JSON.stringify({ error: 'Proxy Error', details: err.message }));
      }
    })
  );
}; 