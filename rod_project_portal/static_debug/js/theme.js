(function () {
    var LIGHT_FROM = 19;   // светлая тема с 19:00
    var LIGHT_TO = 8;      // и до 08:00

    function applyTheme() {
        var hour = new Date().getHours();   // локальное время пользователя
        var theme = (hour >= LIGHT_FROM || hour < LIGHT_TO) ? 'dark' : 'light';
        if (document.documentElement.getAttribute('data-bs-theme') !== theme) {
            document.documentElement.setAttribute('data-bs-theme', theme);
        }
    }

    applyTheme();
    setInterval(applyTheme, 60000);   // проверка раз в минуту
})();