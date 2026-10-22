// Окно входящего звонка.
// Держит постоянный WebSocket /ws/incoming/ и показывает окно «Ответить / Сбросить» + играет рингтон

(function () {
  if (window.__incomingCallInit) return; // Не запускаем дважды, если скрипт подключён и в base.html, и в блоке страницы
  window.__incomingCallInit = true;

  // На странице самого звонка (есть #remoteWrapper) окно не нужно - там свой сокет, и пользователь уже в звонке
  if (document.getElementById('remoteWrapper')) return;

  let socket = null;
  let current = null;      // текущий входящий вызов: { room, url, caller }
  let overlay = null;      // DOM-окно вызова

  // Рингтон
  const ringtone = new Audio('/static/sounds/ringtone.mp3');
  ringtone.loop = true;

  function startRingtone() {
    ringtone.currentTime = 0;
    ringtone.play().catch(() => {
      // Браузер запрещает звук, пока пользователь не взаимодействовал со страницей
      // Окно уже показано, звук включится при первом клике/нажатии
      const retry = () => {
        if (current) ringtone.play().catch(() => {});
        ['click', 'keydown', 'touchstart'].forEach(ev => document.removeEventListener(ev, retry));
      };
      ['click', 'keydown', 'touchstart'].forEach(ev => document.addEventListener(ev, retry));
    });
  }

  function stopRingtone() {
    ringtone.pause();
    ringtone.currentTime = 0;
  }

  // Окно вызова
  function showIncoming(call) {
    if (current) return; // Уже идёт другой вызов - второй не показываем
    current = call;

    overlay = document.createElement('div');
    overlay.className = 'position-fixed top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center';
    overlay.style.cssText = 'background: rgba(0,0,0,.6); z-index: 2000;';
    overlay.innerHTML = `
      <div class="card shadow-lg border-0 rounded-4 text-center p-4 bg-dark text-white" style="width: 320px;">
        <div class="small text-secondary mb-1">Входящий звонок</div>
        <div id="incomingAvatar" class="rounded-circle overflow-hidden bg-secondary d-flex align-items-center justify-content-center fw-bold fs-1 mx-auto mb-3" style="width: 96px; height: 96px;"></div>
        <h4 class="fw-bold mb-4"></h4>
        <div class="d-flex justify-content-center gap-4">
          <button id="incomingDeclineBtn" class="btn btn-danger rounded-circle p-0" style="width:56px;height:56px;" title="Сбросить">
          <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" fill="currentColor" class="bi bi-telephone-x" viewBox="0 0 16 16">
              <path d="M3.654 1.328a.678.678 0 0 0-1.015-.063L1.605 2.3c-.483.484-.661 1.169-.45 1.77a17.6 17.6 0 0 0 4.168 6.608 17.6 17.6 0 0 0 6.608 4.168c.601.211 1.286.033 1.77-.45l1.034-1.034a.678.678 0 0 0-.063-1.015l-2.307-1.794a.68.68 0 0 0-.58-.122l-2.19.547a1.75 1.75 0 0 1-1.657-.459L5.482 8.062a1.75 1.75 0 0 1-.46-1.657l.548-2.19a.68.68 0 0 0-.122-.58zM1.884.511a1.745 1.745 0 0 1 2.612.163L6.29 2.98c.329.423.445.974.315 1.494l-.547 2.19a.68.68 0 0 0 .178.643l2.457 2.457a.68.68 0 0 0 .644.178l2.189-.547a1.75 1.75 0 0 1 1.494.315l2.306 1.794c.829.645.905 1.87.163 2.611l-1.034 1.034c-.74.74-1.846 1.065-2.877.702a18.6 18.6 0 0 1-7.01-4.42 18.6 18.6 0 0 1-4.42-7.009c-.362-1.03-.037-2.137.703-2.877z"/>
              <path fill-rule="evenodd" d="M11.146 1.646a.5.5 0 0 1 .708 0L13 2.793l1.146-1.147a.5.5 0 0 1 .708.708L13.707 3.5l1.147 1.146a.5.5 0 0 1-.708.708L13 4.207l-1.146 1.147a.5.5 0 0 1-.708-.708L12.293 3.5l-1.147-1.146a.5.5 0 0 1 0-.708"/>
           </svg>
          </button>

          <button id="incomingAnswerBtn" class="btn btn-success rounded-circle p-0" style="width:56px;height:56px;" title="Ответить">
          <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" fill="currentColor" class="bi bi-telephone" viewBox="0 0 16 16">
              <path d="M3.654 1.328a.678.678 0 0 0-1.015-.063L1.605 2.3c-.483.484-.661 1.169-.45 1.77a17.6 17.6 0 0 0 4.168 6.608 17.6 17.6 0 0 0 6.608 4.168c.601.211 1.286.033 1.77-.45l1.034-1.034a.678.678 0 0 0-.063-1.015l-2.307-1.794a.68.68 0 0 0-.58-.122l-2.19.547a1.75 1.75 0 0 1-1.657-.459L5.482 8.062a1.75 1.75 0 0 1-.46-1.657l.548-2.19a.68.68 0 0 0-.122-.58zM1.884.511a1.745 1.745 0 0 1 2.612.163L6.29 2.98c.329.423.445.974.315 1.494l-.547 2.19a.68.68 0 0 0 .178.643l2.457 2.457a.68.68 0 0 0 .644.178l2.189-.547a1.75 1.75 0 0 1 1.494.315l2.306 1.794c.829.645.905 1.87.163 2.611l-1.034 1.034c-.74.74-1.846 1.065-2.877.702a18.6 18.6 0 0 1-7.01-4.42 18.6 18.6 0 0 1-4.42-7.009c-.362-1.03-.037-2.137.703-2.877z"/>
          </svg>
          </button>
        </div>
      </div>`;

    // Подпись и имя только после создания разметки выше
    overlay.querySelector('.small').textContent =
      call.audio ? 'Входящий аудиозвонок' : 'Входящий видеозвонок';
    overlay.querySelector('h4').textContent = call.caller || 'Неизвестно';

    const av = overlay.querySelector('#incomingAvatar');
    if (call.avatar) {
      const img = document.createElement('img');
      img.src = call.avatar;
      img.className = 'w-100 h-100 object-fit-cover';
      av.appendChild(img);
    } else {
      av.textContent = (call.caller || '?').charAt(0).toUpperCase();
    }

    document.body.appendChild(overlay);

    // Вызов считаем активным только когда окно успешно создано
    startRingtone();

    overlay.querySelector('#incomingAnswerBtn').onclick = () => {
      stopRingtone();
      window.location.href = call.url;
    };

    overlay.querySelector('#incomingDeclineBtn').onclick = () => {
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: 'decline', room: call.room }));
      }
      hideIncoming();
    };
  }

  function hideIncoming() {
    stopRingtone();
    if (overlay) { overlay.remove(); overlay = null; }
    current = null;
  }

  // WebSocket
  function connect() {
    const proto = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
    socket = new WebSocket(`${proto}${window.location.host}/ws/incoming/`);

    socket.onmessage = ev => {
      let msg;
      try { msg = JSON.parse(ev.data); } catch (e) { return; }

      if (msg.type === 'incoming-call') {
        showIncoming({ room: msg.room, url: msg.url, caller: msg.caller, audio: msg.audio, avatar: msg.avatar });      } else if (msg.type === 'call-cancelled') {
        // Звонящий бросил трубку, пока мы не ответили: закрываем окно (только если это тот же вызов)
        if (current && current.room === msg.room) hideIncoming();
      }
    };

    // Сокет должен жить постоянно: при обрыве переподключаемся через 3 с.
    socket.onclose = () => setTimeout(connect, 3000);
  }

  connect();
})();
