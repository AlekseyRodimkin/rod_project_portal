document.getElementById('avatarModal').addEventListener('show.bs.modal', e => {
    const t = e.relatedTarget;
    const name = t.dataset.name || '';
    const src = t.dataset.avatar;
    const circle = document.getElementById('avatarModalCircle');
    circle.textContent = '';
    if (src) {
        const img = document.createElement('img');
        img.src = src;
        img.className = 'w-100 h-100 object-fit-cover';
        circle.appendChild(img);
    } else {
        circle.textContent = name.charAt(0).toUpperCase();   // нет фото: буква
    }
    document.getElementById('avatarModalName').textContent = name;
});
