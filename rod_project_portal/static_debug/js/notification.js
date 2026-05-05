setTimeout(() => {
    const alerts = document.querySelectorAll('#flash-messages .alert');
    alerts.forEach(a => {
        const bsAlert = new bootstrap.Alert(a);
        bsAlert.close();
    });
}, 5000);
