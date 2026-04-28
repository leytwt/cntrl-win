import requests
import json
import re

TOKEN = "eyJhbGciOiJIUzM4NCJ9.eyJzY29wZXMiOlsibGxhbWEiLCJzZCIsInlhQXJ0Il0sInN1YiI6ImhhY2thdGhvbl8yNl8wNiIsImlhdCI6MTc3Njk0OTEzMCwiZXhwIjoxNzc3NjQwMzMwfQ.gyxa9WiLcIG0FBCAkL7rm_Af-9mqxFnuZREwGVI-EsSjTn9UD-6aPPiMBbg1_qQd"

URL = "https://ai.rt.ru/api/1.0/llama/chat"


def clean_json_response(text: str) -> str:
    """
    Очищает ответ от лишних символов и извлекает JSON
    """
    # Удаляем маркдаун блоки
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)

    # Ищем JSON массив
    start = text.find('[')
    end = text.rfind(']') + 1

    if start != -1 and end > start:
        return text[start:end]

    return text


def generate_presentation_content(
        prompt: str,
        document_text: str,
        slides_count: int,
        style: str,
        tone: str
) -> list:
    """
    Генерирует структуру презентации через LLM API
    """
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }

    # Формируем промпт для модели
    full_prompt = f"""Создай структуру презентации со следующими параметрами:

Тема: {prompt}
Количество слайдов: {slides_count}
Стиль: {style}
Тон: {tone}

Содержимое документа для анализа:
{document_text[:2000] if document_text else "Документ не предоставлен"}

Верни ТОЛЬКО JSON массив в формате:
[
    {{
        "title": "Заголовок слайда",
        "content": "Текст слайда с пунктами, разделенными точкой с запятой или новой строкой"
    }}
]

ВАЖНО: Верни только JSON, без дополнительного текста."""

    payload = {
        "uuid": "00000000-0000-0000-0000-000000000000",
        "chat": {
            "model": "Qwen/Qwen2.5-72B-Instruct",
            "user_message": full_prompt,
            "contents": [
                {
                    "type": "text",
                    "text": full_prompt
                }
            ],
            "system_prompt": "Ты профессиональный создатель презентаций. Отвечай только JSON.",
            "max_new_tokens": 2048,
            "temperature": 0.3,
            "top_p": 0.9
        }
    }

    try:
        print("Отправка запроса к LLM API...")
        response = requests.post(
            URL,
            headers=headers,
            json=payload,
            timeout=30
        )

        print(f"Статус ответа: {response.status_code}")

        if response.status_code != 200:
            print(f"Ошибка API: {response.text}")
            return get_fallback_slides(prompt, slides_count)

        result = response.json()
        print(f"Ответ API: {json.dumps(result, ensure_ascii=False)[:500]}")

        # Извлекаем контент из ответа
        if isinstance(result, list) and len(result) > 0:
            content = result[0].get("message", {}).get("content", "")
        elif isinstance(result, dict):
            content = result.get("message", {}).get("content", "")
        else:
            content = str(result)

        # Очищаем и парсим JSON
        cleaned = clean_json_response(content)
        print(f"Очищенный JSON: {cleaned[:300]}")

        slides_data = json.loads(cleaned)

        if isinstance(slides_data, list) and len(slides_data) > 0:
            return slides_data
        else:
            print("Неверный формат данных от LLM")
            return get_fallback_slides(prompt, slides_count)

    except json.JSONDecodeError as e:
        print(f"Ошибка парсинга JSON: {e}")
        print(f"Сырой ответ: {content if 'content' in locals() else 'Нет ответа'}")
        return get_fallback_slides(prompt, slides_count)

    except requests.exceptions.Timeout:
        print("Таймаут запроса к LLM API")
        return get_fallback_slides(prompt, slides_count)

    except Exception as e:
        print(f"Неожиданная ошибка: {e}")
        return get_fallback_slides(prompt, slides_count)


def get_fallback_slides(prompt: str, slides_count: int) -> list:
    """
    Создает базовую структуру слайдов если LLM недоступен
    """
    slides = []

    templates = [
        {"title": "Введение", "content": "Обзор темы; Ключевые понятия; Цели и задачи"},
        {"title": "Анализ проблемы", "content": "Текущая ситуация; Основные вызовы; Статистика и данные"},
        {"title": "Решения", "content": "Предлагаемые подходы; Преимущества решений; Сравнительный анализ"},
        {"title": "Практическое применение", "content": "Примеры использования; Кейсы; Результаты внедрения"},
        {"title": "Рекомендации", "content": "Пошаговый план; Необходимые ресурсы; Ожидаемые результаты"},
        {"title": "Заключение", "content": "Основные выводы; Ключевые takeaways; Следующие шаги"},
    ]

    for i in range(slides_count):
        template = templates[min(i, len(templates) - 1)]
        slides.append({
            "title": f"{template['title']}: {prompt[:50]}" if prompt else template['title'],
            "content": template['content']
        })

    return slides