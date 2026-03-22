import os
import random
import time
import schedule
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
from groq import Groq
from googletrans import Translator
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ========== КОНФИГУРАЦИЯ ==========
BOT_TOKEN = "7871294093:AAF1wOyxbZnCkKWOy05wiS2QDJSFuG-oCQU"
CHANNEL_ID = "-1003715243255"
GROQ_API_KEY = "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"
UNSPLASH_API_KEY = "XCTy4sQRyfZXyqSDMj_3eAOJV548p92IXMqERREifwk"

# Настройки
HOURS = list(range(9, 19))

# Инициализация
groq_client = Groq(api_key=GROQ_API_KEY)
translator = Translator()

def send_telegram_message(photo_path, caption):
    """Отправка фото и текста в Telegram"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    
    with open(photo_path, 'rb') as photo:
        files = {'photo': photo}
        data = {
            'chat_id': CHANNEL_ID,
            'caption': caption,
            'reply_markup': '{"inline_keyboard":[[{"text":"🔁 Поделиться каналом","url":"https://t.me/Businessmind1212"}]]}'
        }
        response = requests.post(url, files=files, data=data)
    
    if response.status_code == 200:
        logger.info("✅ Пост отправлен")
        return True
    else:
        logger.error(f"Ошибка: {response.text}")
        return False

def generate_quote():
    """Генерация цитаты через Groq"""
    try:
        prompt = """Придумай короткую мотивирующую цитату на русском языке про бизнес, успех, деньги или личностный рост. 
Цитата должна быть вдохновляющей, оригинальной и состоять из 1-2 предложений. Только цитата, без кавычек и пояснений."""
        
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9,
            max_tokens=100
        )
        
        quote = completion.choices[0].message.content.strip()
        logger.info(f"Цитата: {quote[:50]}...")
        return quote
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return "Успех — это умение двигаться от неудачи к неудаче, не теряя энтузиазма."

def translate_to_uzbek(text):
    """Перевод на узбекский"""
    try:
        translation = translator.translate(text, dest='uz')
        return translation.text
    except Exception as e:
        logger.error(f"Ошибка перевода: {e}")
        return "Muvaffaqiyat - bu muvaffaqiyatsizlikdan muvaffaqiyatsizlikka o'tish."

def search_image(keywords):
    """Поиск фото через Unsplash"""
    try:
        url = "https://api.unsplash.com/search/photos"
        params = {
            "query": keywords,
            "per_page": 10,
            "orientation": "landscape"
        }
        headers = {"Authorization": f"Client-ID {UNSPLASH_API_KEY}"}
        
        response = requests.get(url, params=params, headers=headers)
        data = response.json()
        
        if data["results"]:
            return random.choice(data["results"])["urls"]["regular"]
        else:
            return search_image("business success")
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return None

def add_text_to_image(image_url, text):
    """Наложение текста на фото"""
    try:
        response = requests.get(image_url)
        img = Image.open(BytesIO(response.content))
        img = img.resize((1280, 720))
        
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        draw_overlay = ImageDraw.Draw(overlay)
        draw_overlay.rectangle([(0, 0), (1280, 720)], fill=(0, 0, 0, 180))
        img = img.convert('RGBA')
        img = Image.alpha_composite(img, overlay)
        
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype("arial.ttf", 40)
        except:
            font = ImageFont.load_default()
        
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            current_line.append(word)
            test_line = ' '.join(current_line)
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] - bbox[0] > 1100:
                current_line.pop()
                lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        y_offset = 350
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            x = (1280 - (bbox[2] - bbox[0])) // 2
            draw.text((x, y_offset), line, fill=(255, 255, 255), font=font)
            y_offset += 50
        
        output_path = f"temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        img.save(output_path, "PNG")
        return output_path
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return None

def generate_hashtags(quote):
    """Генерация хештегов"""
    base = ["бизнес", "мотивация", "успех"]
    return " ".join(["#" + tag for tag in base]) + " #success #business"

def publish_post():
    """Публикация поста"""
    try:
        logger.info("Создаю пост...")
        
        quote_ru = generate_quote()
        quote_uz = translate_to_uzbek(quote_ru)
        
        image_url = search_image("business success")
        if not image_url:
            return
        
        image_path = add_text_to_image(image_url, quote_ru)
        if not image_path:
            return
        
        hashtags = generate_hashtags(quote_ru)
        caption = f"{quote_ru}\n\n{quote_uz}\n\n{hashtags}\n\n👉 @Businessmind1212"
        
        send_telegram_message(image_path, caption)
        os.remove(image_path)
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")

def job():
    current_hour = datetime.now().hour
    if current_hour in HOURS:
        logger.info(f"Час {current_hour}: публикую")
        publish_post()

def main():
    logger.info("🚀 Бот запущен!")
    logger.info(f"Канал: @Businessmind1212")
    logger.info(f"Расписание: с {min(HOURS)}:00 до {max(HOURS)}:00")
    
    publish_post()
    
    schedule.every().hour.at(":00").do(job)
    
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    main()