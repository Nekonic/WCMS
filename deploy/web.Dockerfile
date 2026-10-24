FROM node:22.23.4-alpine AS build
RUN npm install -g pnpm@12.15.0
WORKDIR /app/frontend
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

FROM nginx:1.28.3-alpine
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
COPY deploy/snippets/ /etc/nginx/snippets/
COPY --from=build /app/frontend/build /usr/share/nginx/html
