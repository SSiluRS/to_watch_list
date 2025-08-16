# build
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json .
RUN npm ci
ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
COPY . .
RUN echo "VITE_API_BASE_URL=${VITE_API_BASE_URL}" > .env.production  # Создаём .env.production
RUN npm run build

# serve
FROM nginx:1.27-alpine
COPY --from=build /app/dist/ /usr/share/nginx/html/
EXPOSE 80
