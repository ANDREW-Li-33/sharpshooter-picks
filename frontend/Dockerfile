# Use Node.js as our base image
FROM node:18-alpine

# Set working directory in the container
WORKDIR /app

# Copy package files first (this helps with caching)
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of the application
COPY . .

# Expose the port Next.js runs on
EXPOSE 3000

# Start the development server
CMD ["npm", "run", "dev"]