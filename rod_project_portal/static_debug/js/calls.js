// Видеозвонок 1 на 1: WebRTC + WebSocket для сигнализации
// Звонок стартует автоматически при загрузке страницы.

const $ = id => document.getElementById(id);
const status = t => $('status').textContent = t; // Вывод текущего состояния звонка пользователю в элемент #status

let ws = null; // WebSocket-соединение с сигнальным сервером
pc = null; // WebRTC-соединение с собеседником (RTCPeerConnection)
localStream = null; // свой поток (камера + микрофон)

// Очередь промисов: заставляет асинхронные сигнальные операции
// выполняться строго по одной и в порядке поступления
// (иначе createOffer / setRemoteDescription могут перемешаться)
let queue = Promise.resolve();
let ended = false; // Флаг «звонок уже завершён» — защита от повторного завершения
const CONTACTS_URL = ($('room') && $('room').dataset.contactsUrl) || '/portal/contacts/';
const AUDIO_ONLY = new URLSearchParams(window.location.search).get('mode') === 'audio'; // Режим звонка: ?mode=audio — только звук, камера не запрашивается и не включается
const ringback = new Audio('/static/sounds/ringback.mp3');
ringback.loop = true;

let ringbackWanted = false;   // нужны ли сейчас гудки

function startRingback() {
  ringbackWanted = true;
  ringback.currentTime = 0;
  ringback.play().catch(e => {
    console.warn('Звук вызова заблокирован браузером, включится после первого действия:', e);
    // Повторяем попытку при первом действии пользователя на странице
    const retry = () => {
      if (ringbackWanted) ringback.play().catch(() => {});
      ['click', 'keydown', 'touchstart'].forEach(ev => document.removeEventListener(ev, retry));
    };
    ['click', 'keydown', 'touchstart'].forEach(ev => document.addEventListener(ev, retry));
  });
}

function stopRingback() {
  ringbackWanted = false;   // чтобы отложенная попытка не включила звук после ответа
  ringback.pause();
  ringback.currentTime = 0;
}

// Создание нового WebRTC-соединения
function createPeer() {
  closePeer(); // Сначала убираем старое соединение, если оно было
  // STUN-сервер Google нужен, чтобы узнать свой публичный адрес и пробить NAT
  pc = new RTCPeerConnection({ iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] });
  if (localStream) { // Добавляем свои дорожки (аудио и видео) - их увидит собеседник
    localStream.getTracks().forEach(t => pc.addTrack(t, localStream));
  }

  pc.ontrack = e => { // Сработает, когда придёт медиа собеседникаxs
    const remoteVideo = $('remote');
    remoteVideo.srcObject = e.streams[0]; // Показываем поток собеседника в <video id="remote">

    // Когда известны размеры кадра — подгоняем контейнер под формат видео
    remoteVideo.onloadedmetadata = () => {
      const w = remoteVideo.videoWidth;
      const h = remoteVideo.videoHeight;
      const wrapper = $('remoteWrapper');
      if (w && h) {
        // Контейнер повторяет пропорции видео
        wrapper.style.aspectRatio = `${w} / ${h}`;
        if (w > h) {
          // Горизонтальное видео (с компьютера) - шире
          wrapper.style.maxWidth = '750px';
        } else {
          // Вертикальное видео (с телефона) - уже
          wrapper.style.maxWidth = '380px';
        }
      }
    };
  };

  // Нашёлся ICE-кандидат (возможный сетевой маршрут) - отправляем его собеседнику через сигнальный канал
  pc.onicecandidate = e => { if (e.candidate) sendSignal({ ice: e.candidate }); };
  // Показываем состояние соединения: connecting, connected, failed и т.д.
  pc.onconnectionstatechange = () => {
    if (!pc) return;
    status('Соединение: ' + pc.connectionState);
    if (pc.connectionState === 'connected') {
      stopRingback();
    } else if (pc.connectionState === 'failed') {
      endCall('Соединение потеряно', 1500);
    }
  };
}

// Закрытие WebRTC-соединения и сброс окна собеседника
function closePeer() {
  if (pc) { pc.close(); pc = null; } // Закрываем соединение и обнуляем переменную
  $('remote').srcObject = null; // Убираем видео собеседника
  // Возвращаем контейнер к вертикальному формату по умолчанию
  $('remoteWrapper').style.aspectRatio = '9/16';$('remoteWrapper').style.maxWidth = '380px';
}

// Единое завершение звонка
// Вызывается во всех случаях конца звонка:
//  - нажали Завершить
//  - собеседник вышел (peer-left)
//  - собеседник сбросил вызов (call-declined)
//  - обрыв соединения / сокета
// Освобождает камеру, сокет, соединение и уводит на страницу контактов
// message - текст статуса, delay - пауза (мс) перед редиректом, чтобы пользователь успел увидеть причину
function endCall(message, delay = 100) {
  if (ended) return;
  ended = true;

  stopRingback();
  if (message) status(message);

  if (ws) {
    ws.close();
  }

  if (localStream) {
    localStream.getTracks().forEach(track => track.stop());
    localStream = null;
  }
  const localVideo = $('local');
  if (localVideo) {
    localVideo.srcObject = null;
    localVideo.style.display = 'none';
  }

  closePeer();

  setTimeout(() => {
    window.location.href = CONTACTS_URL;
  }, delay);
}

// Отправка сигнального сообщения собеседнику (через сервер)
// data содержит одно из: offer, answer, ice
function sendSignal(data) { ws.send(JSON.stringify({ type: 'signal', data })); }
async function handleSignal(data) { // Обработка входящего сигнала от собеседника
  if (data.offer) {
    // Пришло предложение звонка: создаём соединение и отвечаем на него
    createPeer();
    await pc.setRemoteDescription(data.offer);
    const answer = await pc.createAnswer();
    await pc.setLocalDescription(answer);
    sendSignal({ answer: pc.localDescription });
  } else if (data.answer && pc) {
    // Пришёл ответ на наше предложение - завершаем обмен описаниями (SDP)
    await pc.setRemoteDescription(data.answer);
  } else if (data.ice && pc) {
    // Пришёл ICE-кандидат собеседника - добавляем его в соединение
    // Ошибку только логируем (кандидат мог прийти не вовремя)
    try { await pc.addIceCandidate(data.ice); } catch (e) { console.warn(e); }
  }
}

function autoJoinRoom() { // Автоматический вход в комнату через WebSocket
  const room = $('room').value.trim(); // Имя комнаты берём из поля #room; если пусто - ничего не делаем
  if (!room) return;

  // Для HTTPS-страниц нужен защищённый wss://, иначе ws://
  const wsProtocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
  ws = new WebSocket(`${wsProtocol}${window.location.host}/ws/call/`);

  ws.onopen = () => {
    ws.send(JSON.stringify({ type: 'join', room, audio: AUDIO_ONLY })); // Сообщаем серверу, в какую комнату входим
    const leaveBtn = $('leaveBtn');
    if (leaveBtn) leaveBtn.disabled = false; // Разблокируем кнопку «Завершить»
  };

  // Сообщения от сервера
  ws.onmessage = ev => {
    const msg = JSON.parse(ev.data);
    if (msg.type === 'waiting') {
      // Мы первые в комнате — ждём второго участника
      status('Вызов...');
      startRingback();
    } else if (msg.type === 'peer-joined') {
      // Вошёл второй участник — мы становимся инициатором звонка: создаём соединение и отправляем ему offer
      stopRingback();
      status('Звоним...');
      queue = queue.then(async () => {
        createPeer();
        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);
        sendSignal({ offer: pc.localDescription });
      });
    } else if (msg.type === 'signal') {
      // Служебные данные от собеседника (offer/answer/ice) — обрабатываем по очереди, ошибки выводим в консоль
      queue = queue.then(() => handleSignal(msg.data)).catch(console.error);
    } else if (msg.type === 'peer-left') {
      endCall('Собеседник завершил звонок', 1500);
    } else if (msg.type === 'call-declined') {
      endCall('Собеседник отклонил звонок', 1500);
    } else if (msg.type === 'full') {
      endCall('Комната занята.', 1500); // В комнате уже двое — закрываем сокет
    }
  };

  ws.onclose = () => {
    endCall('Связь с сервером потеряна', 1500);
  };
}

// Кнопка микрофона
$('toggleMicBtn').onclick = () => {
  if (!localStream) return; // Если своего потока нет — переключать нечего
  const audioTrack = localStream.getAudioTracks()[0];
  if (!audioTrack) return;

  audioTrack.enabled = !audioTrack.enabled; // «Глушим» / включаем звук. Дорожка не останавливается

  // Обновляем вид кнопки и подсказку
  if (audioTrack.enabled) {
    // Микрофон включён — тёмная кнопка
    $('toggleMicBtn').classList.remove('btn-danger');
    $('toggleMicBtn').classList.add('btn-dark');$('toggleMicBtn').title = 'Выключить микрофон';
  } else {
    // Микрофон выключен — красная кнопка
    $('toggleMicBtn').classList.remove('btn-dark');
    $('toggleMicBtn').classList.add('btn-danger');$('toggleMicBtn').title = 'Включить микрофон';
  }
};

// Кнопка камеры
$('toggleCamBtn').onclick = () => {
  if (!localStream) return;
  const videoTrack = localStream.getVideoTracks()[0];
  if (!videoTrack) return;

  // Включаем / выключаем передачу видео (собеседник увидит чёрный кадр)
  videoTrack.enabled = !videoTrack.enabled;
  const localVideo = $('local');

  if (videoTrack.enabled) { // Камера включена - показываем своё превью и тёмную кнопку
    localVideo.style.display = 'block';
    $('toggleCamBtn').classList.remove('btn-danger');
    $('toggleCamBtn').classList.add('btn-dark');$('toggleCamBtn').title = 'Выключить камеру';
  } else {// Камера выключена - прячем превью и красим кнопку в красный
    localVideo.style.display = 'none';
    $('toggleCamBtn').classList.remove('btn-dark');
    $('toggleCamBtn').classList.add('btn-danger');$('toggleCamBtn').title = 'Включить камеру';
  }
};

// Кнопка «Завершить звонок»
$('leaveBtn').onclick = () => {
  endCall('Звонок завершен'); // Закрываем сигнальный канал (сервер сообщит собеседнику об уходе)
};

// Автоматический старт после загрузки страницы
window.addEventListener('DOMContentLoaded', async () => {
  $('leaveBtn').disabled = false;

  if (AUDIO_ONLY) { // Аудиорежим: прячем своё превью и кнопку камеры, показываем заглушку
    $('localWrapper').style.display = 'none';
    $('toggleCamBtn').style.display = 'none';
    const ph = $('audioPlaceholder');
    if (ph) ph.classList.remove('d-none');
  }

  try {
    status('Запрос доступа к камере и микрофону...');

    // Автоматически запрашиваем доступ
    localStream = await navigator.mediaDevices.getUserMedia({ video: !AUDIO_ONLY, audio: true });
    // Показываем своё видео в превью
    const localVideo = $('local');
    localVideo.srcObject = localStream;
    localVideo.style.display = 'block';

    // Когда известны размеры своей камеры - подгоняем контейнер превью
    localVideo.onloadedmetadata = () => {
      const w = localVideo.videoWidth;
      const h = localVideo.videoHeight;
      const localWrapper = $('localWrapper');
      if (w && h) {
        localWrapper.style.aspectRatio = `${w} / ${h}`;
      }
    };

    // Разблокируем кнопки управления камерой/микрофоном
    $('toggleCamBtn').disabled = false;
    $('toggleMicBtn').disabled = false;

    status('Подключение...');

    // Сразу же запускаем вход в комнату по WebSocket (после получения потока, чтобы дорожки уже были готовы)
    autoJoinRoom();

  } catch (err) {
    // Отказ в доступе, нет устройств или небезопасный контекст (не HTTPS).
    status('Ошибка доступа к камере/микрофону: ' + err.message);
    console.error(err);
  }
});