# frontend/Dockerfile
FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

# Expose Vite's default development port
EXPOSE 5173

# Crucial: --host ensures Vite is accessible outside the container
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]