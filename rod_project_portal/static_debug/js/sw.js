// Фоновый скрипт для уведомлений
// Реагирует на два события - приход push и нажатие на уведомление

// Событие 'push': сервер прислал уведомление (его отправляет send_push)
// Данные приходят как JSON: { title, body, tag, url }.
self.addEventListener('push', e => {
  const d = e.data ? e.data.json() : {}; // Разбираем присланные данные; если их нет - работаем с пустым объектом

  // waitUntil не даёт браузеру «усыпить» скрипт, пока уведомление не показано
  e.waitUntil(self.registration.showNotification(d.title || 'Уведомление', {
    body: d.body,                // второй, более мелкий текст (имя звонящего)
    tag: d.tag,                  // идентификатор: новое уведомление с тем же tag
                                 // заменяет старое, а не добавляется рядом
    renotify: true,              // при замене снова подать звук/вибрацию
    requireInteraction: true,    // не скрывать само (Android и компьютеры;
                                 // на iPhone игнорируется)
    icon: '/static/icons/icon-192.png',  // иконка в уведомлении
    data: { url: d.url || '/' }, // куда вести по нажатию (читается ниже)
  }));
});


// Событие 'notificationclick': пользователь нажал на уведомление
// Открываем страницу звонка: в уже открытой вкладке или в новой
self.addEventListener('notificationclick', e => {
  e.notification.close(); // Закрываем само уведомление
  const url = e.notification.data.url;

  e.waitUntil(
    // Ищем уже открытые вкладки/окна нашего сайта
    // (includeUncontrolled — включая те, которыми sw не управляет)
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {
      // Если сайт уже открыт — переводим эту вкладку на страницу звонка и выводим её на передний план
      if (list.length) return list[0].navigate(url).then(c => c && c.focus());
      // Если не открыт (приложение было закрыто) — открываем новое окно
      return clients.openWindow(url);
    })
  );
});