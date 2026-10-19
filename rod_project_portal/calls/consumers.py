# Серверная часть видеозвонка: сигнальный WebSocket-сервер (Django Channels)
# Сам видеопоток через сервер не идёт — он передаётся напрямую между
# браузерами по WebRTC

# Сервер:
#   1) распределяет участников по комнатам (максимум 2 человека в комнате)
#   2) сообщает о входе/выходе собеседника
#   3) пересылает служебные сообщения (offer, answer, ice) от одного
#      участника другому.

# JS → Python	join	«Хочу в комнату X»
# JS → Python	signal	«Перешли это собеседнику»
# Python → JS	waiting	«Ты первый, жди»
# Python → JS	peer-joined	«К тебе зашёл второй»
# Python → JS	signal	«Вот сообщение от собеседника»
# Python → JS	peer-left	«Собеседник ушёл»
# Python → JS	full	«Комната занята»

import json
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.urls import reverse
from django.conf import settings
from pywebpush import webpush, WebPushException

# Хранилище комнат в памяти процесса:
#   { "имя_комнаты": {channel_name_1, channel_name_2} }
# channel_name — уникальный идентификатор соединения в Channels

ROOMS = {}


def user_group(user_id):
    return f"user_{user_id}"


# Располагать функцию до CallConsumer !!!
@database_sync_to_async
def send_push(user_id, payload):
    """
    Отправляет Web Push-уведомление на все устройства пользователя
    Аргументы:
        user_id (int): id пользователя-получателя.
        payload (dict): содержимое уведомления, уходит в sw.js как JSON
            title (str): заголовок («Входящий звонок»)
            body  (str): текст (имя звонящего)
            tag   (str): идентификатор; уведомление с тем же tag заменяет старое
            url   (str): куда перейти по нажатию (страница звонка)

    Как работает:
        - берёт все подписки пользователя из PushSubscription (по одной на устройство)
        - отправляет каждой через pywebpush с подписью VAPID-ключом
        - ttl=30: если телефон недоступен 30 секунд, уведомление отбрасывается
          (устаревший звонок не нужен)
        - Urgency=high: просит доставить немедленно

    Ошибки:
        - подписка устарела (404/410: приложение удалено или разрешение отозвано)
        - удаляется из базы
        - остальные ошибки отдельной подписки не мешают отправке на другие.

    Возвращает: None. Функция синхронная (сетевой запрос), поэтому обёрнута в
    database_sync_to_async и безопасно вызывается из async-кода consumer через await
    """
    from calls.models import PushSubscription
    for sub in PushSubscription.objects.filter(user_id=user_id):
        try:
            r = webpush(
                subscription_info={"endpoint": sub.endpoint,
                                   "keys": {"p256dh": sub.p256dh, "auth": sub.auth}},
                data=json.dumps(payload),
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": settings.VAPID_SUBJECT},
                ttl=30,
                headers={"Urgency": "high"},
            )
            print("push sent:", sub.endpoint[:50], r.status_code)
        except WebPushException as e:
            print("push error:", repr(e))
            if e.response is not None and e.response.status_code in (404, 410):
                sub.delete()
        except Exception as e:
            print("push error:", repr(e))


@database_sync_to_async
def get_other_participant(room_name, user):
    """
    Ищет запись модели Friendship по названию комнаты (room_name) со статусом подтвержденной дружбы (ACCEPTED)
    Сравнивает ID текущего пользователя с участниками связи (from_user и to_user)
    Возвращает противоположного участника (собеседника), либо None, если связь не найдена или пользователь не является участником этой комнаты
    """
    from calls.models import Friendship

    link = (
        Friendship.objects.select_related("from_user", "to_user")
        .filter(room_name=room_name, status=Friendship.Status.ACCEPTED)
        .first()
    )
    if not link:
        return None
    if link.from_user_id == user.id:
        return link.to_user
    if link.to_user_id == user.id:
        return link.from_user
    return None  # пользователь не участник этой комнаты


class CallConsumer(AsyncWebsocketConsumer):
    # Клиент открыл WebSocket-соединение
    async def connect(self):
        self.room_name = (
            None  # Пока клиент не прислал "join", он ни в какой комнате не состоит
        )
        # Принимаем соединение
        self.callee_id = (
            None  # Кому мы звонили (id), чтобы отменить его окно, если бросим трубку
        )
        await self.accept()

    # Соединение закрыто (клиент ушёл, закрыл вкладку, пропала сеть)
    async def disconnect(self, close_code):
        if (
                self.room_name and self.room_name in ROOMS
        ):  # Действуем, только если клиент успел войти в существующую комнату
            ROOMS[self.room_name].discard(
                self.channel_name
            )  # Убираем этого участника из комнаты (discard не падает, если его там уже нет).

            for channel_name in ROOMS[
                self.room_name
            ]:  # Сообщаем оставшемуся участнику, что собеседник вышел
                await self.channel_layer.send(
                    channel_name,
                    {
                        "type": "room_message",  # "type" здесь — имя метода-обработчика: Channels
                        "content": {
                            "type": "peer-left"
                        },  # Что именно в итоге уйдёт клиенту по WebSocket
                    },
                )

            # Если комната опустела, а мы кому-то звонили — собеседник,
            # возможно, ещё видит окно входящего звонка. Просим закрыть его
            # В сообщении есть room: окно закроется, только если это тот же вызов
            if not ROOMS[self.room_name] and self.callee_id:
                await self.channel_layer.group_send(
                    user_group(self.callee_id),
                    {
                        "type": "notify",
                        "content": {"type": "call-cancelled", "room": self.room_name},
                    },
                )

            # Если комната опустела — удаляем её, чтобы не копить мусор
            if not ROOMS[self.room_name]:
                del ROOMS[self.room_name]

    # Пришло сообщение от клиента
    async def receive(self, text_data):
        # Ожидаем JSON, при невалидных данных молча игнорируем сообщение
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        # Тип сообщения: "join" (войти в комнату) или "signal" (служебные данные)
        msg_type = data.get("type")

        # Вход в комнату
        # Принимаем "join" только один раз: если комната уже выбрана, игнорируем
        if msg_type == "join" and not self.room_name:
            room = data.get("room")
            if not room:  # Без имени комнаты входить некуда
                return

            self.room_name = room
            peers = ROOMS.setdefault(
                self.room_name, set()
            )  # Берём набор участников комнаты, если комнаты нет - создаём пустую

            if len(peers) >= 2:  # В комнате уже двое — это соединение лишнее
                await self.send(
                    text_data=json.dumps({"type": "full"})
                )  # Говорим клиенту, что комната занята
                # Сбрасываем комнату, чтобы при отключении этот клиент
                # не повлиял на чужую комнату (не отправил "peer-left")
                self.room_name = None
                return

            # Уведомляем уже находящегося в комнате участника о новом госте
            # Именно получив "peer-joined", он создаёт offer и начинает звонок
            for channel_name in peers:
                await self.channel_layer.send(
                    channel_name,
                    {"type": "room_message", "content": {"type": "peer-joined"}},
                )

            peers.add(
                self.channel_name
            )  # Добавляем себя в комнату (после рассылки, чтобы не уведомлять себя)

            # Если мы первые — сообщаем клиенту, что нужно ждать собеседника
            if len(peers) == 1:
                await self.send(text_data=json.dumps({"type": "waiting"}))

                user = self.scope.get("user")
                if user and user.is_authenticated:
                    try:
                        callee = await get_other_participant(self.room_name, user)
                        if callee:
                            self.callee_id = callee.id
                            audio = bool(data.get("audio"))
                            call_url = reverse(
                                "calls:call_room", kwargs={"room_name": self.room_name}
                            )
                            if audio:
                                call_url += "?mode=audio"

                            # Окно «Ответить / Сбросить» (сначала, чтобы сбой push его не отменил)
                            await self.channel_layer.group_send(
                                user_group(callee.id),
                                {
                                    "type": "notify",
                                    "content": {
                                        "type": "incoming-call",
                                        "room": self.room_name,
                                        "caller": user.get_username(),
                                        "url": call_url,
                                        "audio": audio,
                                    },
                                },
                            )

                            # Push на телефон
                            print("sending push to", callee.id)
                            await send_push(callee.id, {
                                "title": "Входящий аудиозвонок" if audio else "Входящий видеозвонок",
                                "body": user.get_username(),
                                "tag": f"call-{self.room_name}",
                                "url": call_url,
                            })

                    except Exception as e:
                        print("Не удалось отправить уведомление о звонке:", repr(e))

        # ---------------- Пересылка сигналов ----------------
        # Служебные данные WebRTC (offer / answer / ice) принимаем только от тех, кто уже в комнате
        elif msg_type == "signal" and self.room_name:
            if self.room_name in ROOMS:
                # Пересылаем сообщение всем в комнате, кроме отправителя
                # (при 2 участниках это ровно один собеседник)
                for channel_name in ROOMS[self.room_name]:
                    if channel_name != self.channel_name:
                        await self.channel_layer.send(
                            channel_name,
                            {
                                "type": "room_message",
                                # Пересылаем исходное сообщение как есть:
                                # {"type": "signal", "data": {...}}
                                "content": data,
                            },
                        )

    # Обработчик сообщений, пришедших через channel layer от других участников (вызывается Channels по "type": "room_message")
    async def room_message(self, event):
        await self.send(
            text_data=json.dumps(event["content"])
        )  # Достаём полезную часть и отправляем её своему клиенту по WebSocket


# Постоянный сокет пользователя для уведомлений о входящих звонках.
# Можно подключить с любой страницы скрипт incoming_call.js)
# Подключено на странице {% url 'calls:contacts' %}
class IncomingCallConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")

        if not user or not user.is_authenticated:  # Анонимам уведомления не нужны
            await self.close()
            return
        self.user = user
        self.group = user_group(user.id)

        await self.channel_layer.group_add(
            self.group, self.channel_name
        )  # Подписываемся на личную группу: сюда пишет CallConsumer
        await self.accept()

    async def disconnect(self, close_code):
        if getattr(self, "group", None):
            await self.channel_layer.group_discard(self.group, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        if (
                data.get("type") == "decline"
        ):  # Собеседник нажал «Сбросить» в окне входящего звонка
            room = data.get("room")
            if not room:
                return
            if not await get_other_participant(
                    room, self.user
            ):  # Защита: сбросить можно только вызов в своей комнате
                return

            for channel_name in ROOMS.get(
                    room, set()
            ):  # Сообщаем звонящему (он сидит в комнате) - он завершит звонок
                await self.channel_layer.send(
                    channel_name,
                    {"type": "room_message", "content": {"type": "call-declined"}},
                )

    # Обработчик событий группы (type "notify"): пересылаем их в браузер
    async def notify(self, event):
        await self.send(text_data=json.dumps(event["content"]))
