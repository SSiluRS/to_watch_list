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

api.interceptors.response.use(
  response => response,
  error => {
    if (error.response && error.response.status === 401) {
      // Токен истек или невалиден
      localStorage.clear();
      window.location.reload(); // Перезагрузка сбросит состояние Vue и покажет AuthForm
    }
    return Promise.reject(error);
  }
);

export function getItems(params = {}) {
  // поддерживаем sort_by, order, list_id, limit, offset
  console.log(params)
  return api.get("/items", { params });
}
