<?php

// Основной класс прокси
class MDSProxy {
    private $baseUrl = 'https://mds-station.com/api/';
    private $imagePath = '../share/current_image.webp';
    private $textPath = '../share/current_text.txt';

    public function __construct() {
        if (file_exists(__DIR__ . '/.env')) {
            $env = parse_ini_file(__DIR__ . '/.env');
            foreach ($env as $key => $value) {
                putenv("$key=$value");
            }
        }
    }

    // Получение данных с удаленного API
    private function fetchRemoteData($endpoint) {
        $url = $this->baseUrl . $endpoint;
        $ch = curl_init();

        curl_setopt($ch, CURLOPT_URL, $url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        curl_setopt($ch, CURLOPT_TIMEOUT, 5);

        $response = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);

        curl_close($ch);

        if ($httpCode !== 200) {
            return null;
        }

        return $response;
    }

    // Получение информации о текущем треке
    public function getCurrentTrack() {
        $response = $this->fetchRemoteData('current.json');
        return $response ? json_decode($response, true) : null;
    }

    // Получение процента проигранного трека
    public function getPlayedPercent() {
        $response = $this->fetchRemoteData('percent.html');
        return $response !== null ? intval(trim($response)) : null;
    }

    // Получение плейлиста
    public function getPlaylist() {
        $response = $this->fetchRemoteData('playlist.json');
        return $response ? json_decode($response, true) : null;
    }

    // Получение объединенных данных
    public function getCombinedData() {
        $result = [
            'success' => true,
            'data' => [],
            'errors' => []
        ];

        // Получаем текущий трек
        $currentTrack = $this->getCurrentTrack();
        if ($currentTrack) {
            $result['data']['current_track'] = $currentTrack;
        } else {
            $result['errors'][] = 'Не удалось получить текущий трек';
        }

        // Получаем процент проигрывания
        $percent = $this->getPlayedPercent();
        if ($percent !== null) {
            $result['data']['played_percent'] = $percent;
        } else {
            $result['errors'][] = 'Не удалось получить процент проигрывания';
        }

        // Проверяем существование файлов
        $imageExists = file_exists($this->imagePath);
        $textExists = file_exists($this->textPath);

        $result['data']['image_url'] = $imageExists ? getenv('BASE_URL') . '?img&t=' . filemtime($this->imagePath) : null;
        $textExists = file_exists($this->textPath);
        $result['data']['text'] = $textExists ? file_get_contents($this->textPath) : null;
        $result['data']['timestamp'] = time();

        $result['data']['stream'] = 'http://mds-station.com:8000/mds';

        // Получаем плейлист
        $playlist = $this->getPlaylist();
        if ($playlist) {
            $result['data']['playlist'] = $playlist;
        } else {
            $result['errors'][] = 'Не удалось получить плейлист';
        }

        // Если есть ошибки, отмечаем success как false
        if (!empty($result['errors'])) {
            $result['success'] = false;
        }

        return $result;
    }
}

if (isset($_GET['img'])) {
    header("Content-Type: image/webp");
    readfile('../share/current_image.webp');
    exit;
} else {
    header('Content-Type: application/json');
    header('Access-Control-Allow-Origin: *');
    header('Access-Control-Allow-Methods: GET');

    // Обработка запроса
    $proxy = new MDSProxy();
    $response = $proxy->getCombinedData();

    echo json_encode($response, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT);
}