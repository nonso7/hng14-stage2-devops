const express = require('express');
const axios = require('axios');
const path = require('path');

const API_URL = process.env.API_URL || 'http://api:8000';
const PORT = parseInt(process.env.PORT || '3000', 10);

const app = express();
app.use(express.json());
app.use(express.static(path.join(__dirname, 'views')));

app.get('/health', async (_req, res) => {
  try {
    const r = await axios.get(`${API_URL}/health`, { timeout: 2000 });
    if (r.status === 200) {
      return res.json({ status: 'ok' });
    }
    return res.status(503).json({ status: 'degraded' });
  } catch (err) {
    return res.status(503).json({ status: 'degraded', error: err.message });
  }
});

app.post('/submit', async (_req, res) => {
  try {
    const r = await axios.post(`${API_URL}/jobs`);
    res.json(r.data);
  } catch (err) {
    console.error('submit failed:', err.message);
    res.status(502).json({ error: 'api unavailable' });
  }
});

app.get('/status/:id', async (req, res) => {
  try {
    const r = await axios.get(`${API_URL}/jobs/${req.params.id}`);
    res.json(r.data);
  } catch (err) {
    if (err.response && err.response.status === 404) {
      return res.status(404).json({ error: 'not found' });
    }
    console.error('status failed:', err.message);
    res.status(502).json({ error: 'api unavailable' });
  }
});

app.listen(PORT, () => {
  console.log(`Frontend running on port ${PORT}`);
});
