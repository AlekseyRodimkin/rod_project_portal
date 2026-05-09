# docker compose down && docker-compose up -d --build
# docker compose up -d && docker-compose logs -f
# sudo scp -i ~/Desktop/vdsina_ssh_key_2 -P 43564 /Users/alex/Desktop/PycharmProjects/rod_project_portal/rod_project_portal/db/db.sqlite3 alex@144.124.229.249:~/projects/rod_project_portal/db
# scp -i ~/Desktop/vdsina_ssh_key_2 -P 43564 ~/Desktop/public-key.gpg  alex@144.124.229.249:~/projects/rod_project_portal/rp_portal_backup

# docker compose down
# docker compose up --build -d

# Перезапуск контейнера nginx
# docker restart remnawave-nginx

# sudo vim /opt/remnawave/nginx.conf
# /opt/remnawave/docker-compose.yml

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
sudo vim /opt/remnawave/nginx.conf
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
