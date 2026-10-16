"""Статика располагается по пути. Нужно прокинуть volume туда из контейнера приложений"""
# /var/www/html/<domain>/static

"""
Сертификаты генерируются командой
Перед генерацией возможно нужно будет остановить контейнеры занимающие 80 порт
"""
# certbot certonly --standalone -d <domain>

"""Сертификаты генерируются по пути"""
# /etc/letsencrypt/live/<domain>/fullchain.pem
# /etc/letsencrypt/live/<domain>/privkey.pem

"""Удаление сертификатов"""
# sudo  certbot certificates
# sudo certbot delete --cert-name <domain>

"""После генерации нужно прокинуть volume на каждый сертификат внутрь docker-compose.yml"""
# /opt/remnawave - папка remnawave
# /opt/remnawave/docker-compose.yml
# - /etc/letsencrypt/live/<DOMAIN>/fullchain.pem:/etc/nginx/ssl/<DOMAIN>/fullchain.pem:ro
# - /etc/letsencrypt/live/<DOMAIN>/privkey.pem:/etc/nginx/ssl/<DOMAIN>/privkey.pem:ro

"""Переразвертывание compose remnawave"""
# docker compose -f /opt/remnawave/docker-compose.yml down
# docker compose -f /opt/remnawave/docker-compose.yml up -d


"""
HTTPS - вставка в конфигурацию nginx для rod-project.24-7.ro
sudo vim .../nginx.conf
"""

# server {
#     server_name rod-project.24-7.ro;
#     listen unix:/dev/shm/nginx.sock ssl proxy_protocol;
#     http2 on;
#     ssl_certificate "/etc/nginx/ssl/rod-project.24-7.ro/fullchain.pem";
#     ssl_certificate_key "/etc/nginx/ssl/rod-project.24-7.ro/privkey.pem";
#     ssl_trusted_certificate "/etc/nginx/ssl/rod-project.24-7.ro/fullchain.pem";
#     location /static/ {
#         alias /var/www/html/rod_project_portal/static/;
#     }
#
#     location / {
#         proxy_pass http://127.0.0.1:8000;
#         proxy_set_header Host $host;
#         proxy_set_header X-Real-IP $proxy_protocol_addr;
#         proxy_set_header X-Forwarded-For $proxy_protocol_addr;
#         proxy_set_header X-Forwarded-Proto $scheme;
#     }
# }

"""Потом перезапустить nginx"""
# docker compose restart remnawave-nginx
# или
# docker restart remnawave-nginx
