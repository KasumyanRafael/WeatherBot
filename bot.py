import logging
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import Update
import requests
from datetime import time
import pytz

# Конфигурация

TOKEN = "7843232490:AAFVQx20mngb8X63kWAAUyF1O4JrNwF_nyw"
OWM_API_KEY = "459d6e47fe64424ccfaafade5576c2e1"
VLADIKAVKAZ_LAT = 43.0367
VLADIKAVKAZ_LON = 44.6678
TIMEZONE = pytz.timezone('Europe/Moscow')

# Настройка логов
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class WeatherBot:
    def __init__(self):
        self.session = requests.Session()  # Сессия для запросов
        self.session.headers.update({'User-Agent': 'Mozilla/5.0'})

    async def get_weather(self):
        """Улучшенный метод получения погоды с обработкой всех ошибок"""
        try:
            url = f"https://api.openweathermap.org/data/2.5/weather?lat={VLADIKAVKAZ_LAT}&lon={VLADIKAVKAZ_LON}&units=metric&lang=ru&appid={OWM_API_KEY}"
            
            # Таймауты для запроса (5 сек на подключение, 10 сек на чтение)
            response = self.session.get(url, timeout=(5, 10))
            response.raise_for_status()  # Проверка HTTP ошибок
            
            data = response.json()
            
            # Проверка структуры ответа
            if not all(key in data for key in ['weather', 'main']):
                raise ValueError("Некорректная структура данных от API")
            
            weather_desc = data['weather'][0]['description']
            temp = data['main']['temp']
            temp_min = data['main']['temp_min']
            temp_max = data['main']['temp_max']
            
            # Словарь эмодзи с учетом русских описаний
            weather_emojis = {
                'ясно': '☀️', 'солнечно': '☀️',
                'облачно': '☁️', 'пасмурно': '☁️',
                'дождь': '🌧', 'ливень': '🌧',
                'гроза': '⛈', 'молния': '⚡',
                'снег': '❄️', 'туман': '🌫',
                'малооблачно': '🌤'
            }
            
            # Ищем подходящий эмодзи
            emoji = '🌡'  # По умолчанию
            for key in weather_emojis:
                if key in weather_desc.lower():
                    emoji = weather_emojis[key]
                    break
            
            return (
                f"Доброе утро!👋\n\n"
                f"Сейчас во Владикавказе: {weather_desc.capitalize()} {emoji}\n"
                f"🌡 Температура: {round(temp)}°C (мин {round(temp_min)}°C, макс {round(temp_max)}°C)\n"
                f"💨 Ветер: {data.get('wind', {}).get('speed', 'N/A')} м/с\n\n"
                f"Хорошего дня! ☕"
            )
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка запроса к API: {str(e)}")
        except ValueError as e:
            logger.error(f"Ошибка данных: {str(e)}")
        except Exception as e:
            logger.error(f"Неожиданная ошибка: {str(e)}")
        
        return "Извините, не удалось получить данные о погоде. Попробуйте позже."

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "🌤 Я бот погоды для Владикавказа!\n"
            "Команды:\n"
            "/weather - текущая погода\n"
            "/setup - ежедневный прогноз в 6:30"
        )

    async def send_weather(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отправка погоды с индикатором загрузки"""
        msg = await update.message.reply_text("🔄 Запрашиваю данные о погоде...")
        weather_msg = await self.get_weather()
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=msg.message_id,
            text=weather_msg
        )

    async def setup_daily_weather(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.job_queue:
            await update.message.reply_text("⚠️ Ошибка инициализации")
            return

        chat_id = update.effective_chat.id
        jobs = context.job_queue.get_jobs_by_name(str(chat_id))
        
        if jobs:
            await update.message.reply_text("✅ Рассылка уже настроена")
            return
            
        context.job_queue.run_daily(
            self.daily_weather_handler,
            time=time(hour=6, minute=30, tzinfo=TIMEZONE),
            chat_id=chat_id,
            name=str(chat_id))
            
        await update.message.reply_text(
            "⏰ Ежедневная рассылка настроена на 6:30!\n"
            "Используйте /weather для текущего прогноза"
        )

    async def daily_weather_handler(self, context: ContextTypes.DEFAULT_TYPE):
        try:
            weather_msg = await self.get_weather()
            await context.bot.send_message(
                chat_id=context.job.chat_id,
                text=weather_msg
            )
        except Exception as e:
            logger.error(f"Ошибка в daily_weather_handler: {e}")

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        logger.error(f"Ошибка: {context.error}", exc_info=True)
        if update and hasattr(update, 'message'):
            await update.message.reply_text("⚠️ Произошла ошибка. Мы уже работаем над исправлением!")

    def run(self):
        app = Application.builder().token(TOKEN).build()
        
        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(CommandHandler("weather", self.send_weather))
        app.add_handler(CommandHandler("setup", self.setup_daily_weather))
        app.add_error_handler(self.error_handler)
        
        logger.info("Бот запущен и готов к работе")
        app.run_polling()

if __name__ == '__main__':
    bot = WeatherBot()
    bot.run()