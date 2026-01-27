FROM nginx:alpine

COPY docker/nginx.conf /etc/nginx/nginx.conf
COPY frontend/ /usr/share/nginx/html/

EXPOSE 80 443