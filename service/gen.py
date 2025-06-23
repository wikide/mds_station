import os
import time
import requests
import subprocess
import json
import logging
import speech_recognition as sr
import base64
import csv
from pydub import AudioSegment
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from io import BytesIO
from PIL import Image

# Загрузка переменных окружения
load_dotenv()

# Конфигурация
AUDIO_STREAM_URL = "http://mds-station.com:8000/mds"
RECORD_DURATION = 30  # 10 минут в секундах
AUDIO_FILE = "../share/current_audio.wav"
TEXT_FILE = "../share/current_text.txt"
IMAGE_FILE = "../share/current_image.webp"
GENRE_CACHE_FILE = "../share/genre.csv"

# API Keys
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
FUSIONBRAIN_API_KEY = os.getenv('FUSIONBRAIN_API_KEY')
FUSIONBRAIN_API_SECRET_KEY = os.getenv('FUSIONBRAIN_API_SECRET_KEY')

# Инициализация распознавателя речи
recognizer = sr.Recognizer()

def record_audio():
    """Записывает аудио из потока с таймаутом"""
    try:
        # Добавляем таймаут 30 секунд на запись
        process = subprocess.Popen([
            "ffmpeg", "-y",
            "-i", AUDIO_STREAM_URL,
            "-t", str(RECORD_DURATION),
            "-acodec", "pcm_s16le",
            "-ar", "48000",
            "-ac", "1",
            AUDIO_FILE
        ], stderr=subprocess.PIPE, stdout=subprocess.PIPE)

        try:
            # Ждем завершения с таймаутом
            stdout, stderr = process.communicate(timeout=30)
            if process.returncode != 0:
                print(f"Ошибка записи аудио: {stderr.decode()}")
                return False
            return True
        except subprocess.TimeoutExpired:
            process.kill()
            print("Таймаут записи аудио (30 сек)")
            return False

    except Exception as e:
        print(f"Критическая ошибка записи: {str(e)}")
        return False

def transcribe_audio():
    """Распознаёт текст из аудио через Google Web Speech API"""
    try:
        with sr.AudioFile(AUDIO_FILE) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language="ru-RU")
            return text.strip()
    except sr.UnknownValueError:
        print("Google Speech Recognition не смог распознать аудио")
        return None
    except sr.RequestError as e:
        print(f"Ошибка запроса к Google API: {e}")
        return None
    except Exception as e:
        print(f"Ошибка распознавания: {e}")
        return None

def get_current_track_info():
    """Получает информацию о текущем треке"""
    try:
        response = requests.get("https://mds-station.com/api/current.json", timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Ошибка получения информации о треке: {e}")
        return None

def generate_keywords_to_prompt(genre):
    """
    Генерирует ключевые слова для промпта на основе жанра.

    Args:
        genre (str): Жанр произведения ('фантастика', 'киберпанк', 'ужасы', 'фэнтези', 'другое')

    Returns:
        list: Список ключевых слов для генерации промпта
    """
    genre_prompt_map = {
        'фантастика': [
            "космический корабль", "далёкая планета", "звёздные системы",
            "футуристические технологии", "научная фантастика", "космическая опера",
            "инопланетные цивилизации", "межгалактические путешествия", "терраформирование",
            "роботы", "синтетический интеллект", "колонизация планет"
        ],
        'киберпанк': [
            "неоновый город", "киберпространство", "высокие технологии",
            "искусственный интеллект", "виртуальная реальность", "дистопия",
            "хакеры", "биотехнологии", "киборги", "мегакорпорации",
            "дополненная реальность", "кибернетические импланты", "ночной дождь в городе"
        ],
        'ужасы': [
            "мрачная атмосфера", "сверхъестественное", "жуткий",
            "готическая архитектура", "тьма", "паранормальное",
            "необъяснимое", "тревожное", "мистическое", "заброшенный дом",
            "древнее проклятие", "тени", "кровь", "оккультизм"
        ],
        'фэнтези': [
            "волшебный лес", "средневековье", "магический",
            "мифические существа", "древние руины", "эпическое приключение",
            "заколдованные земли", "драконы", "магические артефакты", "королевства",
            "волшебники", "битвы", "древние пророчества", "мифические звери"
        ],
        'детектив': [
            "загадочное убийство", "частный сыщик", "улицы города",
            "улики", "преступный мир", "ночная улица", "тайна",
            "расследование", "полицейский участок", "подозреваемые",
            "досье", "фоторобот", "криминалистика", "загадочные обстоятельства"
        ],
        'другое': [
            "книжная иллюстрация", "литературный стиль", "художественное произведение",
            "атмосферное", "эмоциональное", "выразительное",
            "детализированное", "16:9", "высокое качество", "реалистичное",
            "живописное", "концепт-арт", "обложка книги"
        ]
    }

    # Возвращаем ключевые слова для указанного жанра или для жанра 'другое' по умолчанию
    return genre_prompt_map.get(genre.lower(), genre_prompt_map['другое'])

def generate_static_prompt(text, author, title, genre):
    """
    Генерирует промпт для генерации изображения на основе жанра

    Args:
        text (str): Распознанный текст из аудио
        author (str): Автор произведения
        title (str): Название произведения
        genre (str): Жанр произведения

    Returns:
        str: Сгенерированный промпт
    """
    # Получаем ключевые слова для жанра
    keywords = generate_keywords_to_prompt(genre)

    # Берем первые 30 слов из текста (для краткости)
    short_text = ' '.join(text.split()[:30])

    # Выбираем 3 случайных ключевых слова
    import random
    selected_keywords = random.sample(keywords, min(3, len(keywords)))

    # Формируем промпт
    prompt_parts = [
        f"Иллюстрация к произведению '{title}' автора {author}",
        f"Жанр: {genre}",
        f"Ключевые элементы: {', '.join(selected_keywords)}",
        f"Контекст: {short_text}...",
        "Высокое качество, детализированное, соотношение 16:9"
    ]

    return '. '.join(prompt_parts)

def load_genre_cache():
    """Загружает кэш жанров из файла"""
    cache = {}
    try:
        with open(GENRE_CACHE_FILE, mode='r', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter=';')
            for row in reader:
                if len(row) >= 2:
                    cache[row[0]] = row[1]
    except FileNotFoundError:
        Path(GENRE_CACHE_FILE).parent.mkdir(parents=True, exist_ok=True)
    return cache

def save_genre_cache(cache):
    """Сохраняет кэш жанров в файл"""
    with open(GENRE_CACHE_FILE, mode='w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f, delimiter=';')
        for key, value in cache.items():
            writer.writerow([key, value])

def get_genre(author, title):
    """Определяет жанр произведения с кэшированием"""
    # Загружаем кэш
    genre_cache = load_genre_cache()

    # Формируем ключ для кэша
    cache_key = f"{author} {title}"

    # Проверяем кэш
    if cache_key in genre_cache:
        #print(f"Жанр взят из кэша: {genre_cache[cache_key]}")
        return genre_cache[cache_key]

    # Если нет в кэше, определяем жанр
    try:

        system_prompt = """Ты эксперт по литературе. Определи жанр произведения одним словом:
        фантастика, фэнтези, киберпанк, ужасы, детектив, роман, другое"""

        user_prompt = f"Произведение: {title} ({author})"

        payload = {
            "model": "openai/gpt-3.5-turbo",  # Более дешевая модель
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": 15,
            "temperature": 0.3
        }

        # Инициализация клиентов
        headers_openrouter = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers_openrouter,
            json=payload
        )
        response.raise_for_status()
        genre = response.json()['choices'][0]['message']['content'].strip().lower()

        # Нормализуем ответ
        genre = genre.split()[0]  # Берем первое слово
        if genre not in ['фантастика', 'фэнтези', 'киберпанк', 'ужасы', 'детектив', 'роман']:
            genre = "другое"

        #print(f"Жанр получен из модели: {genre}")

        # Сохраняем в кэш
        genre_cache[cache_key] = genre
        save_genre_cache(genre_cache)

        return genre

    except Exception as e:
        print(f"Ошибка определения жанра: {e}")
        # В случае ошибки возвращаем "другое" и сохраняем в кэш
        genre_cache[cache_key] = "другое"
        save_genre_cache(genre_cache)
        return "другое"

def generate_image_fusionbrain(prompt):
    """Генерирует изображение через FusionBrain AI с конвертацией в WebP"""
    try:
        # 1. Настройка клиента
        API_URL = "https://api-key.fusionbrain.ai/key/api/v1/"
        HEADERS = {
            'X-Key': f'Key {FUSIONBRAIN_API_KEY}',
            'X-Secret': f'Secret {FUSIONBRAIN_API_SECRET_KEY}'
        }

        # 2. Получаем список доступных пайплайнов
        models_response = requests.get(
            f"{API_URL}pipelines",
            headers=HEADERS,
            timeout=10
        )
        models_response.raise_for_status()
        pipelines = models_response.json()

        if not pipelines:
            raise Exception("Нет доступных пайплайнов")

        pipeline_id = pipelines[0]['id']

        # 3. Формируем параметры
        params = {
            "type": "GENERATE",
            "numImages": 1,
            "width": 1024,
            "height": 576,
            "generateParams": {
                "query": prompt
            }
        }

        # 4. Отправляем запрос
        files = {
            'pipeline_id': (None, pipeline_id),
            'params': (None, json.dumps(params), 'application/json')
        }

        generate_response = requests.post(
            f"{API_URL}pipeline/run",
            headers=HEADERS,
            files=files,
            timeout=30
        )
        generate_response.raise_for_status()

        task_id = generate_response.json().get('uuid')
        if not task_id:
            raise Exception("Не получили task_id в ответе")

        # 5. Проверяем статус
        for _ in range(30):
            status_response = requests.get(
                f"{API_URL}pipeline/status/{task_id}",
                headers=HEADERS,
                timeout=10
            )
            status_data = status_response.json()

            if status_data['status'] == 'DONE':

                censored = status_data['result']['censored']

                if censored:
                    raise Exception(f"Ошибка генерации: {status_data.get('errorDescription')}")

                # Получаем base64-строку из ответа
                base64_image = status_data['result']['files'][0]

                # Декодируем base64 в бинарные данные
                if base64_image.startswith('data:image'):
                    # Если пришел data URL (data:image/jpeg;base64,...)
                    base64_image = base64_image.split(',')[1]

                image_data = base64.b64decode(base64_image)

                # Конвертируем в WebP с помощью Pillow
                img = Image.open(BytesIO(image_data))

                # Сохраняем в формате WebP
                with open(IMAGE_FILE, "wb") as f:
                    img.save(f, format='WEBP', quality=90)

                return True

            elif status_data['status'] == 'FAILED':
                raise Exception(f"Ошибка генерации: {status_data.get('errorDescription')}")

            time.sleep(10)

        raise Exception("Превышено время ожидания генерации")

    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка сети: {str(e)}")
        return False
    except Exception as e:
        logging.error(f"FusionBrain Error: {str(e)}")
        return False

def process_cycle():
    """Основной цикл обработки"""
    #print(f"\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Начало цикла")

    # 1. Получаем информацию о текущем треке
    track_info = get_current_track_info()
    if not track_info:
        print("Не удалось получить информацию о треке")
        return False

    author = track_info.get('author', 'Неизвестный автор')
    title = track_info.get('name', 'Без названия')

    #print(f"Текущий трек: {author} - {title}")

    # 2. Запись аудио
    if not record_audio():
        return False

    # 3. Распознавание текста
    text = transcribe_audio()
    if not text:
        return False

    #print(f"Распознанный текст: {text[:200]}...")

    # 4. Генерация промпта с учётом автора и названия
    genre = get_genre(author, title)
    prompt = generate_static_prompt(text, author, title, genre)
    if not prompt:
        return False

    # print(f"Сгенерированный промпт: {prompt}")

    # 5. Генерация изображения
    if not generate_image_fusionbrain(prompt):
        return False

    # 6. Сохранение текста
    with open(TEXT_FILE, "w", encoding="utf-8") as f:
        f.write(f"{author} - {title}\n\n{text}")

    #print("Цикл успешно завершён!")
    return True

def main():
    # Создаем директории, если их нет
    os.makedirs("../share", exist_ok=True)

    while True:
        success = process_cycle()

        #if not success:
            #print("Используем старое изображение")

        # Ждём 10 минут до следующего цикла
        time.sleep(RECORD_DURATION)

if __name__ == "__main__":
    main()