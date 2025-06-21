from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import re
import os
import asyncio
import time
from imdb import IMDb
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_ID = "29112823"
API_HASH = "cc2dc4952b0de509014ebf4c266d63f5"
BOT_TOKEN = "7917136466:AAGBCFvB-oLDdhvM0B-vjJDign_KAwCIsjU"
FROM_CHANNEL = [-1001304469351]
TO_CHANNEL_USERNAME = "@MBotupdates"

app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
ia = IMDb()

LANGUAGE_MAP = {
    "hin": "Hindi", "hindi": "Hindi", "eng": "English", "english": "English",
    "tam": "Tamil", "tamil": "Tamil", "mar": "Marathi", "marathi": "Marathi",
    "tel": "Telugu", "telugu": "Telugu", "mal": "Malayalam", "malayalam": "Malayalam",
    "kan": "Kannada", "kannada": "Kannada", "ben": "Bengali", "bengali": "Bengali",
    "pun": "Punjabi", "punjabi": "Punjabi", "urd": "Urdu", "urdu": "Urdu",
    "guj": "Gujarati", "gujarati": "Gujarati", "ori": "Odia", "odia": "Odia",
    "ass": "Assamese", "assamese": "Assamese", "kor": "Korean", "korean": "Korean",
    "rus": "Russian", "russian": "Russian", "chi": "Chinese", "chinese": "Chinese"
}

QUALITY_KEYWORDS = {
    "480p 10bit": "480p 10bit", "720p 10bit": "720p 10bit", "1080p 10bit": "1080p 10bit", 
    "2160p 10bit": "2160p 10bit", "480p hevc":"480p HEVC", "720p hevc":"720p HEVC",
    "1080p hevc":"1080p HEVC", "2160p hevc":"2160p HEVC", "480p": "480p", "720p": "720p",
    "1080p": "1080p", "2160p": "2160p", "4k":"4k"
}

recent_files = {}
recent_series = {}
movie_qualities = {}

TIME_WINDOW = 7

async def send_with_delay(chat_id, text, reply_markup=None):
    await asyncio.sleep(1)
    await app.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, disable_notification=True, disable_web_page_preview=True)

async def get_imdb_info(file_name):
    try:
        search_results = ia.search_movie(file_name)
        if search_results:
            movie = search_results[0]
            ia.update(movie, info=['main'])
            rating = movie.get('rating')
            imdb_id = movie.movieID
            imdb_url = f"https://www.imdb.com/title/tt{imdb_id}/"

            poster_url = movie.get('cover url')
            if poster_url:
                poster_url = re.sub(r'_V1_.*?(\.jpg)', r'\1', poster_url)

            return rating, imdb_url, poster_url
    except Exception as e:
        logger.error(f"Error fetching IMDb info: {e}")
    return None, None, None

@app.on_message(filters.chat(FROM_CHANNEL))
async def forward_message(client, message):
    try:
        if not message.chat.type == "private" and not message.poll:
            if message.document or message.video:
                media = message.document or message.video

                file_name = re.sub(r"[^\w\s'.-]", '', media.file_name)

                series_pattern = r'(S\d{2}(E\d{2})?)'
                movie_year_pattern = r'(19|20|21|22)\d{2}'

                series_match = re.search(series_pattern, file_name, flags=re.IGNORECASE)
                movie_year_match = re.search(movie_year_pattern, file_name)

                if series_match and movie_year_match:
                    last_series_index = series_match.end()
                    last_movie_year_index = movie_year_match.end()
                    last_index = max(last_series_index, last_movie_year_index)
                    file_name = file_name[:last_index]
                elif series_match:
                    file_name = file_name[:series_match.end()]
                elif movie_year_match:
                    file_name = file_name[:movie_year_match.end()]

                file_name = file_name.replace('_', ' ').replace('.', ' ').replace('-',' ')
                file_name = re.sub(r'\s+', ' ', file_name).strip()

                quality_pattern = r'\b(' + '|'.join(QUALITY_KEYWORDS.keys()) + r')\b'
                qualities_found = re.findall(quality_pattern, media.file_name + (message.caption or ""), flags=re.IGNORECASE)
                qualities_found = set(QUALITY_KEYWORDS[q.lower()] for q in qualities_found)

                base_name = re.sub(movie_year_pattern, '', file_name).strip()

                if base_name:
                    if base_name in movie_qualities:
                        movie_qualities[base_name].update(qualities_found)
                    else:
                        movie_qualities[base_name] = qualities_found

                current_time = time.time()
                if series_match:
                    season_identifier = series_match.group(1)[:3]
                    if season_identifier in recent_series:
                        if current_time - recent_series[season_identifier] < TIME_WINDOW:
                            return
                        else:
                            recent_series[season_identifier] = current_time
                    else:
                        recent_series[season_identifier] = current_time

                    file_name = file_name.split(season_identifier)[0].strip() + " " + season_identifier
                else:
                    if file_name in recent_files:
                        if current_time - recent_files[file_name] < TIME_WINDOW:
                            return
                        else:
                            recent_files[file_name] = current_time
                    else:
                        recent_files[file_name] = current_time

                await asyncio.sleep(TIME_WINDOW)

                consolidated_qualities = sorted(movie_qualities.get(base_name, []))

                languages_pattern = r'\b(' + '|'.join(LANGUAGE_MAP.keys()) + r')\b'
                caption_text = message.caption if message.caption else ""
                languages_found = re.findall(languages_pattern, caption_text, flags=re.IGNORECASE)

                if not languages_found:
                    languages_found = re.findall(languages_pattern, file_name, flags=re.IGNORECASE)

                full_language_names = [LANGUAGE_MAP[lang.lower()] for lang in set(languages_found)]

                quality_info = ', '.join(consolidated_qualities).lower()
                language_info = ', '.join(full_language_names)

                rating, imdb_url, poster_url = await get_imdb_info(file_name)

                caption = f"**<code>{file_name}</code> **"
                if quality_info:
                    caption += f"**{quality_info} **"
                if language_info:
                    caption += f"**{language_info}**"
                caption += f"** - Added ✅\n\n**"
                if rating:
                    caption += f"**IMDb ⭐ : [{rating}/10]({imdb_url})\n\n**"

                caption += "━━━━━━━━━━━━\n<i>Just copy the name👇and paste it here</i>"

                search_url = "https://t.me/+Ddx2A-Ho0HViYTAx"
                xyz_url = "https://t.me/StreeXDBot"
                search_button = InlineKeyboardMarkup([[
                    InlineKeyboardButton("Request Group", url=search_url),
                    InlineKeyboardButton("Request Bot", url=xyz_url)
                ]])

                if poster_url:
                    try:
                        await app.send_photo(
                            chat_id=TO_CHANNEL_USERNAME,
                            photo=poster_url,
                            caption=caption,
                            reply_markup=search_button
                        )
                    except Exception as photo_error:
                        logger.error(f"Error sending photo: {photo_error}")
                        await send_with_delay(TO_CHANNEL_USERNAME, caption, reply_markup=search_button)
                else:
                    await send_with_delay(TO_CHANNEL_USERNAME, caption, reply_markup=search_button)

                if base_name in movie_qualities:
                    del movie_qualities[base_name]

    except Exception as e:
        logger.error(f"Error forwarding message: {e}")

if __name__ == "__main__":
    logger.info("Bot starting...")
    try:
        import TgCrypto
        logger.info("TgCrypto is available - running in fast mode")
    except ImportError:
        logger.warning("TgCrypto is missing! Pyrogram will work but slower. Install with: pip install TgCrypto")

    app.run()
