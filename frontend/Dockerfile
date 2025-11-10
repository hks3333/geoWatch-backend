# frontend/Dockerfile

# 1. Build Stage
FROM node:18-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./

RUN npm install
COPY . .

# This ARG is set by Cloud Run during the build
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

# 2. Serve Stage
FROM nginx:1.25-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
ENV PORT=8080
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]