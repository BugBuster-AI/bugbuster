# Этап 1: Сборка приложения
FROM node:22.5.1 AS builder

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем аргументы для сборки (используются на этапе build)
ARG BACKEND_URL=/api/
ARG LANGUAGE=en
ARG VERSION=ru

ENV VITE_BACKEND_URL=${BACKEND_URL}
ENV VITE_LANGUAGE=${LANGUAGE}
ENV VITE_APP_VERSION=${VERSION}

# Копируем package.json и package-lock.json
COPY package.json package-lock.json ./

# Устанавливаем зависимости
RUN npm i --legacy-peer-deps

# Копируем остальные файлы проекта
COPY . .

# Собираем проект
RUN npm run build

# Этап 2: Production образ с nginx (для коробочного решения)
FROM nginx:alpine

WORKDIR /app

# Устанавливаем gettext для envsubst
RUN apk add --no-cache gettext

# Копируем собранные статические файлы из builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Конфиг nginx и общий прокси-сниппет
COPY nginx.conf /etc/nginx/templates/default.conf.template
COPY api-proxy.conf /app/api-proxy.conf

RUN printf '#!/bin/sh\n\
# Устанавливаем PORT по умолчанию, если не передан\n\
export PORT=${PORT:-3000}\n\
\n\
# Генерируем nginx.conf из шаблона\n\
envsubst "\$PORT" < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf\n\
\n\
# Запускаем nginx\n\
exec nginx -g "daemon off;"\n' > /docker-entrypoint.sh && chmod +x /docker-entrypoint.sh

# Указываем порт (документационный, реальный порт задаётся через переменную окружения)
EXPOSE 3000

# Запускаем entrypoint скрипт
CMD ["/bin/sh", "/docker-entrypoint.sh"]
