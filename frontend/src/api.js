// src/api.js
import axios from 'axios';

// фронт не знает хост бэка — используем относительный путь
const api = axios.create({ baseURL: "/api" });
export default api;

api.interceptors.request.use(config => {
  const token = localStorage.getItem('token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export function getItems(params = {}) {
  // поддерживаем sort_by, order, list_id, limit, offset
  console.log(params)
  return api.get("/items", { params });
}
