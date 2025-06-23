document.getElementById('year').textContent = new Date().getFullYear();
function copyWalletAddress(e) {
    navigator.clipboard.writeText(e.textContent).then(() => {

    }).catch(err => {
        console.error('Ошибка копирования: ', err);
    });
    return false;
}

// Элементы DOM
const audioPlayer = document.getElementById('audio-player');
const playBtn = document.getElementById('play-btn');
const pauseBtn = document.getElementById('pause-btn');
const stopBtn = document.getElementById('stop-btn');
const volumeControl = document.getElementById('volume');
const trackNameElement = document.getElementById('track-name');
const trackAuthorElement = document.getElementById('track-author');
const trackGenre = document.getElementById('track-genre');
const trackProgress =  document.getElementById('track-progress');
const trackTimeElement = document.getElementById('track-time');
const currentImageElement = document.getElementById('current-image');
const imagePlaceholder = document.getElementById('image-placeholder');
const lastUpdatedElement = document.getElementById('last-updated');
const updateIndicator = document.getElementById('update-indicator');
const nextAuthor = document.getElementById('next-author');
const nextName = document.getElementById('next-name');

// URL прокси
const proxyUrl = 'https://proxy.mds.d0h.ru/';

// Переменная для хранения текущего изображения
let currentImageUrl = '';
let lastUpdateTime = 0;

// Функция для проверки обновлений изображения
async function checkForUpdates(first) {
    try {
        //updateIndicator.textContent = '🔄 Проверка обновлений...';
        //updateIndicator.classList.add('loading');

        const response = await fetch(`${proxyUrl}?t=${Date.now()}`);
        const result = await response.json(); // Получаем весь объект ответа

        // Проверяем success и извлекаем data
        if (result.success && result.data) {
            const data = result.data; // Основные данные теперь здесь
            if (first) {
                audioPlayer.src = data.stream;
            }
            audioPlayer.crossOrigin = "anonymous";
            // Обновляем текст (data.text вместо data.current_track)
            if (data.text)   {
                trackNameElement.textContent = data.current_track.name;
            }

            if (data.current_track?.genre) {
                trackGenre.textContent = data.current_track?.genre;
            }

            // Обновляем автора (если нужно)
            if (data.current_track?.author) {
                trackAuthorElement.textContent = data.current_track.author;
            }

            if (data.played_percent) {
                trackProgress.style.width = data.played_percent + '%';
            }

            if (data.playlist?.next?.[0]?.author) {
                nextAuthor.textContent = data.playlist?.next?.[0]?.author;
            }

            if (data.playlist?.next?.[0]?.name) {
                nextName.textContent = data.playlist?.next?.[0]?.name;
            }

            // Обновляем изображение (data.image_url)
            if (data.image_url && data.image_url !== currentImageUrl) {
                currentImageUrl = data.image_url;
                currentImageElement.style.display = 'none';
                imagePlaceholder.style.display = 'block';
                imagePlaceholder.textContent = 'Загрузка новой иллюстрации...';

                const img = new Image();
                img.onload = () => {
                    currentImageElement.src = currentImageUrl;
                    currentImageElement.style.display = 'block';
                    imagePlaceholder.style.display = 'none';
                    lastUpdatedElement.textContent = new Date(data.timestamp * 1000).toLocaleTimeString();
                };
                img.onerror = () => {
                    imagePlaceholder.textContent = 'Ошибка загрузки иллюстрации';
                };
                img.src = currentImageUrl;
            }
        }

        //updateIndicator.textContent = '✔ Актуально';
        //updateIndicator.classList.remove('loading');
    } catch (error) {
        console.error('Ошибка при проверке обновлений:', error);
        updateIndicator.textContent = '❌ Ошибка';
        updateIndicator.classList.remove('loading');
    }
}

setInterval(checkForUpdates, 600);

// Первоначальная загрузка
checkForUpdates(true);

playBtn.addEventListener('click', async () => {
    try {

        // 2. Проверяем, что источник аудио установлен
        if (!audioPlayer.src) {
            throw new Error("Аудиопоток не загружен");
        }

        // 3. Пытаемся воспроизвести
        await audioPlayer.play();

        // 4. Обновляем состояние кнопок
        playBtn.disabled = true;
        pauseBtn.disabled = false;
        stopBtn.disabled = false;

    } catch (error) {
        console.error('Ошибка воспроизведения:', error);
        //alert(`Ошибка: ${error.message}`);
    }
});

pauseBtn.addEventListener('click', () => {
    audioPlayer.pause();
    playBtn.disabled = false;
    pauseBtn.disabled = true;
});

stopBtn.addEventListener('click', () => {
    audioPlayer.pause();
    audioPlayer.currentTime = 0;
    playBtn.disabled = false;
    pauseBtn.disabled = true;
    stopBtn.disabled = true;
});

// Контроль громкости
volumeControl.addEventListener('input', () => {
    audioPlayer.volume = volumeControl.value;
});

// Обработчики событий аудиоплеера
audioPlayer.addEventListener('playing', () => {
    console.log('Воспроизведение начато');
});

audioPlayer.addEventListener('error', () => {
    console.error('Ошибка аудиоплеера:', audioPlayer.error);
    alert('Произошла ошибка при воспроизведении потока.');
});