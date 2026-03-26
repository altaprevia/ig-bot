import os
import telebot
from instagrapi import Client
import threading
import subprocess
import json

# ============================================
# CONFIGURACIÓN
# ============================================
TOKEN_TELEGRAM = os.environ.get('TOKEN_TELEGRAM')
IG_USER = os.environ.get('IG_USER')
IG_PASS = os.environ.get('IG_PASS')

if not TOKEN_TELEGRAM or not IG_USER or not IG_PASS:
    print("ERROR: Faltan variables de entorno.")
    exit()

bot = telebot.TeleBot(TOKEN_TELEGRAM)
cl = Client()

DOWNLOAD_FOLDER = "downloads"
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# ============================================
# FUNCIONES DE VIDEO
# ============================================
def get_video_codec(file_path):
    """Detecta el códec del video usando ffprobe."""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet',
            '-print_format', 'json',
            '-show_streams',
            file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        data = json.loads(result.stdout)
        
        for stream in data.get('streams', []):
            if stream.get('codec_type') == 'video':
                return stream.get('codec_name', 'unknown')
        return 'unknown'
    except Exception as e:
        print(f"Error detectando códec: {e}")
        return 'unknown'


def convert_to_h264(input_path, output_path):
    """Convierte video HEVC a H.264 (más compatible)."""
    try:
        print(f"🔄 Convirtiendo {input_path} a H.264...")
        
        cmd = [
            'ffmpeg', '-y',
            '-i', input_path,
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '23',
            '-c:a', 'aac',
            '-b:a', '128k',
            '-movflags', '+faststart',
            output_path
        ]
        
        subprocess.run(cmd, capture_output=True)
        
        if os.path.exists(output_path):
            print("✅ Conversión exitosa")
            return True
        return False
    except Exception as e:
        print(f"Error convirtiendo: {e}")
        return False


def process_video_for_sending(file_path):
    """Procesa el video antes de enviar: detecta códec y convierte si es necesario."""
    codec = get_video_codec(file_path)
    print(f"📹 Códec detectado: {codec}")
    
    # Si es HEVC/H.265, convertir a H.264
    if codec in ['hevc', 'h265', 'libx265']:
        print("⚠️ Video en HEVC, convirtiendo a H.264...")
        output_path = file_path.replace('.mp4', '_h264.mp4')
        
        if convert_to_h264(file_path, output_path):
            # Eliminar original y usar el convertido
            os.remove(file_path)
            return output_path
    
    # Si no es HEVC, devolver original
    return file_path


# ============================================
# LOGIN INSTAGRAM
# ============================================
def login_instagram():
    try:
        SESSION_FILE = "session.json"
        if os.path.exists(SESSION_FILE):
            cl.load_settings(SESSION_FILE)
            print("✅ Sesión cargada.")
            return True
        print("❌ No existe session.json")
        return False
    except Exception as e:
        print(f"❌ Error cargando sesión: {e}")
        return False

login_instagram()

# ============================================
# TECLADO
# ============================================
main_keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
main_keyboard.add("📥 Cómo usar", "ℹ️ Info")
main_keyboard.add("📊 Estado", "❓ Ayuda")

# ============================================
# COMANDOS
# ============================================
@bot.message_handler(commands=['start'])
def handle_start(message):
    bot.send_message(
        message.chat.id, 
        "👋 *¡Bienvenido!*\n\nEnvía un enlace de Instagram para descargar.\n\n✅ Videos convertidos a formato compatible.",
        parse_mode='Markdown',
        reply_markup=main_keyboard
    )


@bot.message_handler(commands=['help'])
def handle_help(message):
    bot.send_message(
        message.chat.id, 
        "📚 *Ayuda*\n\nEnvía un enlace de Instagram.\n\nLos videos HEVC se convierten automáticamente a H.264 para máxima compatibilidad.",
        parse_mode='Markdown'
    )


@bot.message_handler(commands=['status'])
def handle_status(message):
    ig_status = '✅ Conectado' if cl.user_id else '❌ No conectado'
    bot.send_message(
        message.chat.id, 
        f"📊 Estado:\n\n🤖 Bot: ✅\n📸 Instagram: {ig_status}\n🎬 Conversión H.264: ✅",
        parse_mode='Markdown'
    )


# ============================================
# BOTONES
# ============================================
@bot.message_handler(func=lambda m: m.text in ["📥 Cómo usar", "ℹ️ Info", "📊 Estado", "❓ Ayuda"])
def handle_buttons(message):
    if message.text == "📥 Cómo usar":
        bot.send_message(message.chat.id, "📥 Pega un enlace de Instagram.\n\nLos videos se convierten automáticamente para ser compatibles con todos los dispositivos.", parse_mode='Markdown')
    elif message.text == "ℹ️ Info":
        bot.send_message(message.chat.id, "ℹ️ Bot Instagram v2.1\n\n✅ Posts\n✅ Reels\n✅ Stories\n✅ Carruseles\n✅ Conversión automática H.264", parse_mode='Markdown')
    elif message.text == "📊 Estado":
        handle_status(message)
    elif message.text == "❓ Ayuda":
        handle_help(message)


# ============================================
# FUNCIÓN REACCIÓN
# ============================================
def set_reaction(chat_id, message_id, emoji):
    valid = ['👍', '❤️', '🔥', '🎉', '😢', '😡', '✅', '❌']
    if emoji not in valid:
        emoji = '👍'
    try:
        bot.set_message_reaction(chat_id, message_id, reaction=[telebot.types.ReactionTypeEmoji(emoji)])
    except:
        pass


# ============================================
# PROCESAR STORY
# ============================================
def process_story(message, url):
    try:
        set_reaction(message.chat.id, message.message_id, '🔥')
        
        parts = url.split('/stories/')
        story_part = parts[1].split('?')[0].rstrip('/')
        story_parts = story_part.split('/')
        username = story_parts[0]
        story_id = story_parts[1] if len(story_parts) > 1 else None
        
        user_id = cl.user_id_from_username(username)
        
        if story_id:
            file_path = cl.story_download(int(story_id), folder=DOWNLOAD_FOLDER)
        else:
            stories = cl.user_stories(user_id)
            if stories:
                file_path = cl.story_download(stories[0].id, folder=DOWNLOAD_FOLDER)
            else:
                raise Exception("No hay stories")
        
        if file_path:
            file_path = str(file_path)
            
            # Si es video, procesar códec
            if file_path.endswith('.mp4'):
                bot.send_message(message.chat.id, "🎬 Procesando video...")
                file_path = process_video_for_sending(file_path)
            
            if file_path.endswith('.mp4'):
                with open(file_path, 'rb') as f:
                    bot.send_video(message.chat.id, f, caption="✅ Story")
            else:
                with open(file_path, 'rb') as f:
                    bot.send_photo(message.chat.id, f, caption="✅ Story")
            
            if os.path.exists(file_path):
                os.remove(file_path)
        
        set_reaction(message.chat.id, message.message_id, '✅')
    except Exception as e:
        print(f"Error story: {e}")
        set_reaction(message.chat.id, message.message_id, '❌')
        bot.reply_to(message, f"❌ Error: {str(e)[:60]}")


# ============================================
# PROCESAR POST/REEL/CARRUSEL
# ============================================
def process_post(message, url):
    try:
        media_pk = cl.media_pk_from_url(url)
        media_info = cl.media_info(media_pk)
        
        # Foto simple
        if media_info.media_type == 1:
            file_path = cl.photo_download(media_pk, folder=DOWNLOAD_FOLDER)
            with open(file_path, 'rb') as f:
                bot.send_photo(message.chat.id, f, caption="✅ Foto")
            os.remove(file_path)
        
        # Video/Reel
        elif media_info.media_type == 2:
            file_path = str(cl.video_download(media_pk, folder=DOWNLOAD_FOLDER))
            
            bot.send_message(message.chat.id, "🎬 Procesando video...")
            file_path = process_video_for_sending(file_path)
            
            with open(file_path, 'rb') as f:
                bot.send_video(message.chat.id, f, caption="✅ Video")
            os.remove(file_path)
        
        # Carrusel
        elif media_info.media_type == 8:
            total = len(media_info.resources)
            bot.send_message(message.chat.id, f"📁 Carrusel ({total} elementos)")
            
            files = []
            for i, r in enumerate(media_info.resources):
                try:
                    bot.send_message(message.chat.id, f"⬇️ {i+1}/{total}")
                    if r.media_type == 2:
                        fp = str(cl.video_download(r.pk, folder=DOWNLOAD_FOLDER))
                        # Procesar video
                        bot.send_message(message.chat.id, f"🎬 Procesando video {i+1}...")
                        fp = process_video_for_sending(fp)
                    else:
                        fp = str(cl.photo_download(r.pk, folder=DOWNLOAD_FOLDER))
                    files.append((fp, r.media_type))
                except Exception as e:
                    print(f"Error elemento {i+1}: {e}")
            
            # Enviar en grupos de 10
            for i in range(0, len(files), 10):
                batch = files[i:i+10]
                group = []
                for fp, mt in batch:
                    try:
                        if mt == 2:
                            with open(fp, 'rb') as f:
                                group.append(telebot.types.InputMediaVideo(f))
                        else:
                            with open(fp, 'rb') as f:
                                group.append(telebot.types.InputMediaPhoto(f))
                    except:
                        pass
                if group:
                    bot.send_media_group(message.chat.id, group)
            
            for fp, _ in files:
                if os.path.exists(fp):
                    os.remove(fp)
        
        set_reaction(message.chat.id, message.message_id, '✅')
    except Exception as e:
        print(f"Error post: {e}")
        set_reaction(message.chat.id, message.message_id, '❌')
        bot.reply_to(message, f"❌ Error: {str(e)[:60]}")


# ============================================
# PROCESAR ENLACE
# ============================================
def process_instagram_link(message, url):
    try:
        set_reaction(message.chat.id, message.message_id, '🔥')
        if '/stories/' in url:
            process_story(message, url)
        else:
            process_post(message, url)
    except Exception as e:
        print(f"Error: {e}")
        set_reaction(message.chat.id, message.message_id, '❌')


# ============================================
# MANEJADOR ENLACES
# ============================================
@bot.message_handler(func=lambda m: "instagram.com" in m.text)
def handle_link(message):
    thread = threading.Thread(target=process_instagram_link, args=(message, message.text.strip()))
    thread.daemon = True
    thread.start()


# ============================================
# MENSAJE POR DEFECTO
# ============================================
@bot.message_handler(func=lambda m: True)
def handle_unknown(message):
    bot.send_message(message.chat.id, "🤔 Envía un enlace de Instagram o usa /help", reply_markup=main_keyboard)


# ============================================
# INICIAR BOT
# ============================================
if __name__ == '__main__':
    print("🤖 Bot iniciado con soporte de conversión H.264...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5, skip_pending=True)