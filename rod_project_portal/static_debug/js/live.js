document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("downloadForm");

    form.addEventListener("submit", async function(e) {
        e.preventDefault();

        try {
            const formData = new FormData(form);
            const urlValue = formData.get("url");

            const validationResponse = await fetch(`/portal/validate_url?url=${encodeURIComponent(urlValue)}`);
            if (!validationResponse.ok) {
                alert("Ошибка: некорректная ссылка на видео");
                return;
            }

            const response = await fetch(`/portal/live_play?url=${encodeURIComponent(urlValue)}`);
            const data = await response.json();

            if (data.stream_url) {
                const block = document.getElementById("videoBlock");
                const player = document.getElementById("videoPlayer");
                const source = document.getElementById("videoSource");

                source.src = `/portal/stream?stream_url=${encodeURIComponent(data.stream_url)}`;
                player.load();
                block.classList.remove("d-none");
                player.play();
            } else {
                alert("Не удалось получить прямой поток.");
            }
        } catch (err) {
            console.error("Ошибка:", err);
            alert("Произошла ошибка, напишите нам на почту что произошло");
        }
    });
});