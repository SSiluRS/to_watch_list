# ToWatchList

Сервис для ведения личных и общих списков фильмов и сериалов с интеграцией поиска по Kinopoisk.  
Проект включает **frontend** на Vue 3 + Vite и **backend** на FastAPI + MariaDB, с авторизацией через JWT и безопасным хранением паролей.

---

## 📦 Стек технологий

- **Backend**: Python 3.11, FastAPI, uvicorn, httpx, mysql-connector-python, passlib[bcrypt], python-jose
- **Database**: MariaDB
- **Frontend**: Vue 3, Vite, axios
- **Auth**: JWT (HS256), пароли — werkzeug (scrypt) + миграция на bcrypt
- **CI/CD & Deploy**: Docker, docker-compose

---

## 🏗 Архитектура

- **DEV**:
  - Frontend (Vite) и Backend (uvicorn) запускаются отдельно
  - API-запросы идут на адрес из `.env.development` (без dev-proxy, но можно настроить)
- **PROD**:
  - Frontend собирается в `dist/` и раздаётся через FastAPI (StaticFiles)
  - Все запросы идут на один origin, CORS не нужен

---

## 📂 Структура репозиториев

### Backend ([to_watch_list](https://github.com/SSiluRS/to_watch_list))
```
app/
  main.py          # FastAPI-приложение, регистрация роутеров, CORS, StaticFiles
  db.py            # Подключение к MariaDB
  auth.py          # JWT, verify/hash пароля
  auth_reset.py    # Reset-токены (sha256(token+pepper))
  kinopoisk.py     # Прокси к Kinopoisk API через httpx
  schemas.py       # Pydantic-модели
frontend/          # Собранный фронт для prod
Dockerfile
docker-compose.yml
requirements.txt
```

### Frontend ([to_watch_list_front](https://github.com/SSiluRS/to_watch_list_front))
```
src/
  main.js          # createApp, глобальные стили
  api.js           # axios с baseURL из VITE_API_BASE_URL
  App.vue
  components/      # AuthForm, ListsView, ItemsView, KinopoiskSearch, ForgotPassword, ResetPassword
vite.config.mjs
package.json
```

---

## ⚙ Переменные окружения

### Backend (.env)
| Переменная             | Описание                              |
|------------------------|---------------------------------------|
| MYSQL_HOST             | Адрес MariaDB                         |
| MYSQL_PORT             | Порт MariaDB                          |
| MYSQL_USER / MYSQL_PASSWORD  | Данные подключения к БД               |
| MYSQL_DATABASE         | Имя базы                              |
| JWT_SECRET / JWT_ALG   | Секрет и алгоритм для JWT              |
| JWT_EXPIRE_DAYS        | Срок действия JWT                     |
| KINOPOISK_API_KEY      | API-ключ api.poiskkino.dev             |
| RESET_TOKEN_SECRET     | Pepper для reset-токенов               |
| RESET_TOKEN_TTL_MIN    | TTL токена сброса пароля (мин)         |
| DEBUG_BEHAVIOR         | В DEV возвращает `dev_token` в API     |

### Frontend (.env.*)
| Файл             | Переменная            | Пример                      |
|------------------|-----------------------|------------------------------|
| .env.development | VITE_API_BASE_URL     | http://192.168.1.9:8000      |
| .env.production  | VITE_API_BASE_URL     | *(пусто)*                    |

---

## 🚀 Запуск проекта

### Dev (раздельно)
```bash
# Backend
cd back
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend
cd front
npm ci
npm run dev
```
Открыть: `http://<front-ip>:<front-port>`

## 🌐 Публичные эндпоинты API

| Метод | Путь                         | Описание                               |
|-------|------------------------------|----------------------------------------|
| POST  | /register                    | Регистрация                            |
| POST  | /login                       | Логин + миграция пароля в bcrypt       |
| GET   | /user?username=...           | Получение пользователя                 |
| GET   | /kinopoisk/search?query=...  | Поиск через Kinopoisk                   |
| POST  | /password/forgot             | Запрос на сброс пароля                  |
| POST  | /password/reset              | Сброс пароля по токену                  |
| POST  | /password/change             | Смена пароля (требует JWT)              |

---

## 🔒 Механизмы безопасности
- **JWT** с exp и HS256
- **Пароли**: поддержка старых werkzeug-хэшей, пересчёт в bcrypt при логине
- **Kinopoisk-прокси**: ключ хранится на сервере, не передаётся на фронт
- **Reset-токены**: хэширование с pepper, TTL


## 📄 Лицензия
MIT License

---
