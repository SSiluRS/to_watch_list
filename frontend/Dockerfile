# build
FROM node:20-alpine AS build
WORKDIR /app
COPY frontend/package*.json .
RUN npm ci
ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
COPY . .
RUN npm run build

# serve
FROM nginx:1.27-alpine
COPY --from=build /app/dist/ /usr/share/nginx/html/
EXPOSE 80
