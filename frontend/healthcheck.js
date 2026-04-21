const http = require('http');

const port = parseInt(process.env.PORT || '3000', 10);
const req = http.get({ host: '127.0.0.1', port, path: '/health', timeout: 2000 }, (res) => {
  process.exit(res.statusCode === 200 ? 0 : 1);
});
req.on('error', () => process.exit(1));
req.on('timeout', () => { req.destroy(); process.exit(1); });
