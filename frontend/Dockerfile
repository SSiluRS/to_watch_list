# build
FROM node:20-alpine AS build
WORKDIR /app

ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

COPY frontend/package*.json ./
RUN npm ci
COPY . .

# Записываем файл .env.production (или .env) чтобы Vite подхватил значение
RUN echo "VITE_API_BASE_URL=$VITE_API_BASE_URL" > .env.production
RUN npm run build

FROM nginx:1.27-alpine AS release
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
