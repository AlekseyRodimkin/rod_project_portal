#!/bin/bash
set -euo pipefail

set -a
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/.env"
set +a

BACKUP_SCRIPTS_DIR="$PROJECT_DIR/rp_portal_backup"
echo 'Создание папки /rp_portal_backup'
mkdir -p "$BACKUP_SCRIPTS_DIR"

BACKUP_DIR="$BACKUP_SCRIPTS_DIR/backups"
echo 'Создание папки /rp_portal_backup/backups'
mkdir -p "$BACKUP_DIR"

echo 'Создание файла backup.sh'
cat > "$BACKUP_SCRIPTS_DIR/backup.sh" <<'EOS'
#!/bin/bash
set -euo pipefail

set -a
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../" && pwd)/.env"
set +a

DATE=$(date +%Y-%m-%d)
SQL_FILE="$PROJECT_DIR/rp_portal_backup/backups/backup-$DATE.sqlite3"
CRYPTED_FILE="$PROJECT_DIR/rp_portal_backup/backups/backup-$DATE.gpg"

echo 'Копия файла базы данных'
cp "$PROJECT_DIR/db/db.sqlite3" "$SQLITE_BACKUP"

echo 'Шифрование'
# gpg --encrypt --recipient "$PUB_KEY_ID" -o "$CRYPTED_FILE" "db.sqlite3_copy"
gpg --batch --yes --trust-model always --encrypt --recipient "$PUB_KEY_ID" -o "$CRYPTED_FILE" "$SQLITE_BACKUP"

echo 'Удаляем исходный нешифрованный файл'
rm -f "$SQLITE_BACKUP"

echo 'Отправка файла'

FILE_PATH="$CRYPTED_FILE"
FILE_NAME=$(basename "$FILE_PATH")
DIR_PATH=$(dirname "$FILE_PATH")
TOKEN="${YANDEX_TOKEN:?YANDEX_TOKEN не задан}"
YANDEX_FOLDER="Приложения/$YANDEX_APP_NAME"
KEEP=${KEEP_BACKUPS:-5}

send_bot_notif() {
    if [[ -z "${BOT_TOKEN:-}" || -z "${CHAT_ID:-}" ]]; then
        return 1
    fi

    local url="https://api.telegram.org/bot${BOT_TOKEN}/sendMessage"
    local text="rod-project.24-7.ro/portal: Резервная копия '$CRYPTED_FILE' загружена в Яндекс Диск"

    curl -s -X POST "$url" \
         -d "chat_id=${CHAT_ID}" \
         -d "text=${text}" > /dev/null
}
echo 'Создаем папку приложения на Диске'
first_req_url="https://cloud-api.yandex.net/v1/disk/resources?path=$YANDEX_FOLDER"
RESPONSE=$(curl -s -w "%{http_code}" -H "Authorization: OAuth $TOKEN" "$first_req_url")
STATUS_CODE=${RESPONSE: -3}
BODY=${RESPONSE%???}

if [ "$STATUS_CODE" -eq 200 ]; then
    echo "Папка приложения создана"
else
    echo "Ошибка API Yandex Disk: Статус $STATUS_CODE"
    if command -v jq >/dev/null 2>&1 && [ -n "$BODY" ]; then
        ERROR_MESSAGE=$(echo "$BODY" | jq -r '.message // .description // .error // "Неизвестная ошибка"')
        echo "Описание: $ERROR_MESSAGE"
    else
        if [ -n "$BODY" ]; then
            echo "Тело ответа:"
            echo "$BODY"
        else
            echo "Тело ответа пустое."
        fi
    fi
    exit
fi

echo 'Запрос ссылки по url: https://cloud-api.yandex.net/v1/disk/resources/upload?path=/$YANDEX_FOLDER/$FILE_NAME&overwrite=true'
UPLOAD_URL=$(curl -s -H "Authorization: OAuth $TOKEN" \
  "https://cloud-api.yandex.net/v1/disk/resources/upload?path=/$YANDEX_FOLDER/$FILE_NAME&overwrite=true" | \
  jq -r '.href')

if [[ -z "$UPLOAD_URL" || "$UPLOAD_URL" == "null" ]]; then
  echo "Ошибка получения URL для загрузки"
  exit 1
fi

echo "Загружаем $FILE_NAME на Яндекс.Диск..."
curl -s --progress-bar -T "$FILE_PATH" "$UPLOAD_URL" | cat

if [[ ${PIPESTATUS[0]} -eq 0 ]]; then
  send_bot_notif
  echo "Файл успешно загружен"
else
  echo "Ошибка загрузки"
  exit 1
fi

echo "Очистка старых бэкапов (оставляем $KEEP последних)..."
mapfile -t FILES < <(ls -1t "$DIR_PATH"/backup-*.gpg 2>/dev/null || true)

if [[ ${#FILES[@]} -le $KEEP ]]; then
  echo "Нечего удалять"
else
  for ((i=$KEEP; i<${#FILES[@]}; i++)); do
    echo "Удаляем ${FILES[$i]}
    rm -f "$DIR_PATH/${FILES[$i]}"
  done
fi
EOS

chmod +x "$BACKUP_SCRIPTS_DIR/backup.sh"
echo 'Файл backup.sh теперь исполняемый'

echo 'Производится настройку cron для ежедневного запуска генерации бэкапа, шифрования и отправки на Yandex Disk'
CRON_CMD="0 0 * * * /usr/bin/bash $BACKUP_SCRIPTS_DIR/backup.sh >> "$BACKUP_SCRIPTS_DIR/backup.log" 2>&1"
(crontab -l 2>/dev/null | grep -F -q "$BACKUP_SCRIPTS_DIR/backup.sh") || (crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -
