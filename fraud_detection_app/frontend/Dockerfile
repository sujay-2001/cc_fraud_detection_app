# -------- deps ----------
FROM node:20 AS deps
WORKDIR /app
COPY package.json ./
RUN npm install                 

# -------- builder ---------
FROM node:20 AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build               

# -------- runtime ---------
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
