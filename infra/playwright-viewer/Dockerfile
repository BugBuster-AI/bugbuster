FROM node:22-slim

WORKDIR /app

ARG PORT=4172
ENV PORT=${PORT}

RUN npm init -y && \
    npm install --no-optional \
      playwright-core@1.59.0-alpha-1771104257000 \
      serve

EXPOSE ${PORT}

CMD ["sh", "-c", "npx serve -s node_modules/playwright-core/lib/vite/traceViewer -l tcp://0.0.0.0:$PORT --no-clipboard"]
