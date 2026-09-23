# syntax=docker/dockerfile:1

# ---- Build stage ----
# node:22-alpine: current Node.js LTS, small Alpine-based image — used only to
# run `npm ci` + `vite build`; it is not shipped in the final image.
FROM node:22-alpine AS build
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# ---- Runtime stage ----
# nginx:alpine: lightweight, standard static-file server for a Vite SPA build
# output; no Node.js runtime is needed to serve prebuilt static assets.
FROM nginx:alpine AS runtime

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
