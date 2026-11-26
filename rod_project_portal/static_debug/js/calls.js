// Видеозвонок 1 на 1: WebRTC + WebSocket для сигнализации
// Звонок стартует автоматически при загрузке страницы.

const $ = id => document.getElementById(id);
const status = t => {
  stopTimer();   // любой новый статус останавливает таймер
  $('status').textContent = t;
};

let ws = null; // WebSocket-соединение с сигнальным сервером
pc = null; // WebRTC-соединение с собеседником (RTCPeerConnection)
localStream = null; // свой поток (камера + микрофон)
let facingMode = 'user';       // какая камера сейчас: 'user' = фронтальная, 'environment' = основная
let switchingCamera = false;   // защита от повторного нажатия, пока идёт переключение

// Очередь промисов: заставляет асинхронные сигнальные операции
// выполняться строго по одной и в порядке поступления
// (иначе createOffer / setRemoteDescription могут перемешаться)
let queue = Promise.resolve();
let ended = false; // Флаг «звонок уже завершён» — защита от повторного завершения
const CONTACTS_URL = ($('room') && $('room').dataset.contactsUrl) || '/portal/contacts/';
const TURN_URL = ($('room') && $('room').dataset.turnUrl) || '/portal/calls/turn/';
const AUDIO_ONLY = new URLSearchParams(window.location.search).get('mode') === 'audio'; // Режим звонка: ?mode=audio — только звук, камера не запрашивается и не включается
const ringback = new Audio('/static/sounds/ringback.mp3');
ringback.loop = true;

let ringbackWanted = false;   // нужны ли сейчас гудки

let ICE_SERVERS = [{ urls: 'stun:stun.l.google.com:19302' }];

async function loadIceServers() {
  try {
    // Запрос к Django-view turn_credentials. Он выдаёт временные логин и пароль
    // для coturn. credentials: 'same-origin' отправляет cookie сессии, view
    // закрыт @login_required и без cookie отдал бы редирект на логин.
    const r = await fetch(TURN_URL, { credentials: 'same-origin' });
    // r.ok = статус 200–299. Если сервер ответил ошибкой (например, 302/403),
    // r.json() разбирает ответ вида {"iceServers": [{stun...}, {turn..., username, credential}]},
    // берём из него массив iceServers и подменяем им переменную.
    if (r.ok) ICE_SERVERS = (await r.json()).iceServers;
  } catch (e) { console.warn('TURN недоступен, только STUN', e); }   // Сеть недоступна, ответ не JSON и т. п. Пишем предупреждение в консоль и не падаем
}

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

  pc = new RTCPeerConnection({ iceServers: ICE_SERVERS });
  if (localStream) { // Добавляем свои дорожки (аудио и видео) - их увидит собеседник
    localStream.getTracks().forEach(t => pc.addTrack(t, localStream));
  }

  pc.ontrack = e => { // Сработает, когда придёт медиа собеседникаxs
    const remoteVideo = $('remote');
    remoteVideo.srcObject = e.streams[0]; // Показываем поток собеседника в <video id="remote">

    // Видео собеседника пошло: убираем обои (в аудиозвонке они остаются всегда)
    remoteVideo.onplaying = () => {
      if (!AUDIO_ONLY) $('callBackdrop').classList.add('d-none');
    };
  };

  // Нашёлся ICE-кандидат (возможный сетевой маршрут) - отправляем его собеседнику через сигнальный канал
  pc.onicecandidate = e => { if (e.candidate) sendSignal({ ice: e.candidate }); };
  // Показываем состояние соединения: connecting, connected, failed и т.д.
  pc.onconnectionstatechange = () => {
    if (!pc) return;
    if (pc.connectionState === 'connected') {
      stopRingback();
      startTimer();
    } else if (pc.connectionState === 'failed') {
      endCall('Соединение потеряно', 1500);
    }
  };
}

// Закрытие WebRTC-соединения и сброс окна собеседника
function closePeer() {
  if (pc) { pc.close(); pc = null; }
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

  if (message) status(message);
  stopRingback();
  stopTimer();

  if (ws) ws.close();
  closePeer();

   // без задержки
  setTimeout(() => {
    window.location.replace(CONTACTS_URL);
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
      endCall('Завершено', 1500);
    } else if (msg.type === 'call-declined') {
      endCall('Отклонено', 1500);
    } else if (msg.type === 'full') {
      endCall('Занято', 1500); // В комнате уже двое — закрываем сокет
    }
  };

  ws.onclose = () => {
    endCall('Сервер не отвечает', 1500);
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
    $('localWrapper').style.opacity = '1';
    $('toggleCamBtn').classList.remove('btn-danger');
    $('toggleCamBtn').classList.add('btn-dark');$('toggleCamBtn').title = 'Выключить камеру';
  } else {// Камера выключена - прячем превью и красим кнопку в красный
    $('localWrapper').style.opacity = '0';
    $('toggleCamBtn').classList.remove('btn-dark');
    $('toggleCamBtn').classList.add('btn-danger');$('toggleCamBtn').title = 'Включить камеру';
  }

};

// Подгоняет рамку превью «Вы» под реальный формат камеры
function fitLocalPreview() {}

// Пересоздаёт превью «Вы» с нуля: новый <video> и новый MediaStream.
// На iOS это надёжнее, чем менять трек внутри уже играющего видео
function rebuildLocalPreview() {
  const wrapper = $('localWrapper');
  const old = $('local');
  const fresh = document.createElement('video');
  fresh.id = 'local';
  fresh.autoplay = true;
  fresh.muted = true;
  fresh.playsInline = true;
  fresh.style.transform = facingMode === 'user' ? 'scaleX(-1)' : 'none';
  // отдельный поток только для превью: берём текущие видеотреки
  fresh.srcObject = new MediaStream(localStream.getVideoTracks());
  wrapper.replaceChild(fresh, old);
  fresh.play().catch(() => {});
}

// Смена камеры (фронтальная <-> основная) без разрыва звонка
async function switchCamera() {
  if (switchingCamera || !localStream) return;
  switchingCamera = true;

  const newFacing = facingMode === 'user' ? 'environment' : 'user';
  const oldTrack = localStream.getVideoTracks()[0];
  const wasEnabled = oldTrack ? oldTrack.enabled : true; // запоминаем, не выключена ли камера кнопкой

  try {
    // На телефонах (особенно iOS) нельзя держать две камеры сразу,
    // поэтому сначала останавливаем старый трек, затем запрашиваем новый
    if (oldTrack) oldTrack.stop();

    const newStream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: { ideal: newFacing } },
      audio: false   // микрофон не трогаем, он остаётся прежним
    });
    const newTrack = newStream.getVideoTracks()[0];
    newTrack.enabled = wasEnabled;

    // Подменяем трек в уже установленном соединении: собеседник увидит новую камеру без переподключения
    if (pc) {
      const sender = pc.getSenders().find(s => s.track && s.track.kind === 'video')
                  || pc.getSenders().find(s => !s.track);   // запасной вариант, если трек уже снят
      if (sender) await sender.replaceTrack(newTrack);
    }

    // Обновляем локальный поток и превью «Вы»
    if (oldTrack) localStream.removeTrack(oldTrack);
    localStream.addTrack(newTrack);

    facingMode = newFacing;      // сначала обновляем, функция ниже читает его для зеркала
    rebuildLocalPreview();

  } catch (err) {
    console.error('Не удалось сменить камеру', err);
    // Старый трек уже остановлен, пробуем вернуть прежнюю камеру, чтобы видео не пропало
    try {
      const back = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: facingMode } }, audio: false
      });
      const backTrack = back.getVideoTracks()[0];
      if (pc) {
        const s = pc.getSenders().find(x => x.track === null || (x.track && x.track.kind === 'video'));
        if (s) await s.replaceTrack(backTrack);
      }
      if (oldTrack) localStream.removeTrack(oldTrack);
      localStream.addTrack(backTrack);
      $('local').srcObject = localStream;
    } catch (e) { console.error(e); }
  } finally {
    switchingCamera = false;
  }
}

// Показываем кнопку смены камеры, только если на устройстве больше одной камеры
async function setupSwitchCamButton() {
  if (AUDIO_ONLY) return;   // в аудиозвонке камеры нет
  try {
    const devices = await navigator.mediaDevices.enumerateDevices();
    const cams = devices.filter(d => d.kind === 'videoinput');
    if (cams.length > 1) {
      const btn = $('switchCamBtn');
      btn.classList.remove('d-none');
      btn.classList.add('d-flex');
      btn.disabled = false;
      btn.onclick = switchCamera;
    }
  } catch (e) { console.warn('Не удалось получить список камер', e); }
}

// Кнопка «Завершить звонок»
$('leaveBtn').onclick = () => {
  endCall('Завершено'); // Закрываем сигнальный канал (сервер сообщит собеседнику об уходе)
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
    status('⁉️🎤🎥');

    // Автоматически запрашиваем доступ
//    localStream = await navigator.mediaDevices.getUserMedia({ video: !AUDIO_ONLY, audio: true });
    localStream = await navigator.mediaDevices.getUserMedia({
          video: AUDIO_ONLY ? false : { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'user' },
          audio: true
        });
    // Показываем своё видео в превью
    const localVideo = $('local');
    localVideo.srcObject = localStream;
    localVideo.style.display = 'block';

    // Пересчитываем размер рамки каждый раз, когда у видео меняется размер
    // (первая загрузка, смена камеры, поворот телефона)
    localVideo.onloadedmetadata = fitLocalPreview;
    localVideo.onresize = fitLocalPreview;

    // Разблокируем кнопки управления камерой/микрофоном
    $('toggleCamBtn').disabled = false;
    $('toggleMicBtn').disabled = false;
    setupSwitchCamButton();   // после выдачи доступа список камер содержит подписи и все устройства
    status('Подключение');

    await loadIceServers();   // получаем TURN-данные до входа в комнату
    // Сразу же запускаем вход в комнату по WebSocket (после получения потока, чтобы дорожки уже были готовы)
    autoJoinRoom();

  } catch (err) {
    // Отказ в доступе, нет устройств или небезопасный контекст (не HTTPS).
    // status('Ошибка доступа к камере/микрофону: ' + err.message);
     status('🚫🎤🎥🚫');
     console.log(err.message)
    console.error(err);
  }
});

// Таймер звонка: запускается, когда соединение установлено
let timerInterval = null;

function formatDuration(totalSeconds) {
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = totalSeconds % 60;
  const mm = String(m).padStart(2, '0');
  const ss = String(s).padStart(2, '0');
  return h > 0 ? `${h}:${mm}:${ss}` : `${mm}:${ss}`;
}

function startTimer() {
  if (timerInterval) return;
  const el = $('status');
  const startedAt = Date.now();
  const tick = () => {
    el.textContent = formatDuration(Math.floor((Date.now() - startedAt) / 1000));
  };
  tick();
  timerInterval = setInterval(tick, 1000);
}

function stopTimer() {
  if (timerInterval) {
    clearInterval(timerInterval);
    timerInterval = null;
  }
}