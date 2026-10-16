(function () {
  const btn = document.getElementById('enablePushBtn');
  if (!btn) return;
  const vapidKey = btn.dataset.vapidKey;
  const csrf = btn.dataset.csrf;

  // Ключ из формата base64url в байты — так его требует браузер.
  function urlBase64ToUint8Array(b64) {
    const pad = '='.repeat((4 - b64.length % 4) % 4);
    const raw = atob((b64 + pad).replace(/-/g, '+').replace(/_/g, '/'));
    return Uint8Array.from([...raw].map(c => c.charCodeAt(0)));
  }

  // Подписать устройство и отправить подписку на сервер.
  async function subscribe() {
    const reg = await navigator.serviceWorker.register('/sw.js');
    await navigator.serviceWorker.ready;
    const sub = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(vapidKey),
    });
    await fetch('/push/subscribe/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
      body: JSON.stringify(sub),
    });
  }

  // Если разрешение уже выдано - подписываемся молча и прячем кнопку
  if ('Notification' in window && Notification.permission === 'granted') {
    subscribe().then(() => btn.hidden = true).catch(console.error);
  }

  // Запрос разрешения должен быть по нажатию (требование)
  btn.onclick = async () => {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
      alert('Уведомления недоступны. На iPhone добавьте сайт на экран «Домой» и откройте с иконки.');
      return;
    }
    if (await Notification.requestPermission() !== 'granted') {
      alert('Уведомления запрещены. Разрешите их в настройках браузера/приложения.');
      return;
    }
    try {
      await subscribe();
      btn.hidden = true;
    } catch (e) {
      console.error(e);
      alert('Не удалось включить уведомления.');
    }
  };
})();