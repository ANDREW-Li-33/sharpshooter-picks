FROM node:16 AS build

WORKDIR /app

# copy package.json and package-lock.json to install dependencies
COPY package*.json ./

# install required dependicies
RUN npm install 

# copy the rest of the application code into the container
COPY . .

RUN npm run build

# use a lightweight nginx image to serve the app in production
FROM nginx:alpine

# copy the built app (created by "npm run build") to the Nginx HTML folder
# from=build because we named this stage in the first line
COPY --from=build /app/out /usr/share/nginx/html

# expose the port that Nginx uses
EXPOSE 3000

# run Nginx in the foreground to serve the app
CMD ["nginx", "-g", "daemon off;"]
