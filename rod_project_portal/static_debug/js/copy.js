document.addEventListener('DOMContentLoaded', function() {
    const copyButtons = document.querySelectorAll('.copy-btn');
    copyButtons.forEach(button => {
        button.addEventListener('click', function() {
            const input = this.parentElement.querySelector('.copy-input');
            input.select();
            document.execCommand('copy');

            const originalText = this.innerHTML;
            this.innerHTML = '<i class="bi bi-check"></i> ☑️';

            setTimeout(() => {
                this.innerHTML = originalText;
            }, 2000);
        });
    });
});