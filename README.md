**Commands to build and run docker image and containers:**

- docker build -t simple-server .
- docker-compose up -d
- docker run -d --name server-app -p 127.0.0.1:3000:3030 simple-server:latest
