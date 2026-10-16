"""
gen_vapid_keys.py — одноразовая генерация пары VAPID-ключей для Web Push.

Зачем:
    Push-службы (Apple, Google) принимают уведомления только от сервера,
    который может доказать, что он тот, для кого пользователь оформил
    подписку. Это доказательство строится на паре ключей:
      - публичный ключ отдаётся браузеру (атрибут data-vapid-key на кнопке);
      - приватный ключ остаётся на сервере и подписывает каждую отправку.

Как запускать (один раз, из терминала):
    pip install py-vapid        # входит в pywebpush, отдельно нужен только если его нет
    python gen_vapid_keys.py

Что выведет:
    VAPID_PUBLIC_KEY  = <строка>
    VAPID_PRIVATE_KEY = <строка>
    Обе строки — в формате base64url (буквы, цифры, '-' и '_', без '=').

Что делать с результатом:
    Вставить значения в settings.py (или в переменные окружения):
        VAPID_PUBLIC_KEY  = "<публичный>"
        VAPID_PRIVATE_KEY = "<приватный>"

Важно:
    - Запускайте один раз. Каждый запуск создаёт НОВУЮ пару, и ключи нельзя
      менять после того, как пользователи подписались: старые подписки
      перестанут работать, и все должны будут подписаться заново.
    - Приватный ключ никому не показывайте и не коммитьте в git.
    - Сам скрипт ничего не сохраняет в файлы, только печатает на экран.
"""

import base64

from cryptography.hazmat.primitives import serialization
from py_vapid import Vapid


def b64url(data: bytes) -> str:
    """Переводит байты в base64url без знаков '=' в конце — формат, который
    ждут и браузер (publicKey), и pywebpush (private key)."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


# 1. Создаём новую пару ключей (эллиптическая кривая P-256, как требует стандарт).
v = Vapid()
v.generate_keys()

# 2. Публичный ключ: «несжатая точка» кривой, 65 байт — именно в таком виде
#    его принимает браузер в pushManager.subscribe(applicationServerKey).
public = v.public_key.public_bytes(
    serialization.Encoding.X962,
    serialization.PublicFormat.UncompressedPoint,
)

# 3. Приватный ключ: «сырое» число длиной 32 байта.
private = v.private_key.private_numbers().private_value.to_bytes(32, "big")

# 4. Печатаем в виде, готовом для вставки в settings.py.
print("VAPID_PUBLIC_KEY  =", b64url(public))
print("VAPID_PRIVATE_KEY =", b64url(private))
