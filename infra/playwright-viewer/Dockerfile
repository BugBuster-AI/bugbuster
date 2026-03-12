FROM node:22.5.1

WORKDIR /app

ARG LANGUAGE
ARG PORT=4172

ENV PORT=${PORT}
ENV VITE_LANGUAGE=${LANGUAGE}

COPY package.json package-lock.json ./
COPY packages/ ./packages/

RUN npm i --legacy-peer-deps

COPY . .

RUN npm run build

EXPOSE ${PORT}

CMD ["sh", "-c", "npm run trace-viewer -- --host 0.0.0.0 --port $PORT"]
