import os
import telebot
from instagrapi import Client
import threading

# ============================================
# CONFIGURACIÓN
# ============================================
TOKEN_TELEGRAM = os.environ.get('TOKEN_TELEGRAM')
IG_USER = os.environ.get('IG_USER')
IG_PASS = os.environ.get('IG_PASS')

if not TOKEN_TELEGRAM or not IG_USER or not IG_PASS:
    print("ERROR: Faltan variables de entorno (TOKEN_TELEGRAM, IG_USER, IG_PASS).")
    exit()

bot = telebot.TeleBot(TOKEN_TELEGRAM)
cl = Client()

DOWNLOAD_FOLDER = "downloads"
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# ============================================
# LOGIN INSTAGRAM
# ============================================
def login_instagram():
    """Carga la sesión existente SIN hacer login nuevo."""
    try:
        SESSION_FILE = "session.json"
        if os.path.exists(SESSION_FILE):
            cl.load_settings(SESSION_FILE)
            print("✅ Sesión cargada correctamente.")
            return True
        else:
            print("❌ No existe session.json. Sube el archivo a Railway.")
            return False
    except Exception as e:
        print(f"❌ Error cargando sesión: {e}")
        return False

login_instagram()

# ============================================
# TECLADO PRINCIPAL
# ============================================
main_keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
main_keyboard.add("📥 Cómo usar", "ℹ️ Info")
main_keyboard.add("📊 Estado", "❓ Ayuda")

# ============================================
# COMANDOS
# ============================================
@bot.message_handler(commands=['start'])
def handle_start(message):
    welcome_text = """
👋 *¡Bienvenido al Bot de Instagram!*

Descarga contenido de Instagram de forma rápida.

*✨ Tipos soportados:*
📸 Fotos
🎬 Videos / Reels
📁 Carruseles completos
⭐ Stories

*📌 Cómo usar:*
Envía un enlace de Instagram.

👇 Usa los botones o envía un enlace.
"""
    bot.send_message(
        message.chat.id, 
        welcome_text, 
        parse_mode='Markdown',
        reply_markup=main_keyboard
    )


@bot.message_handler(commands=['help'])
def handle_help(message):
    help_text = """
📚 *Ayuda del Bot*

*🔧 Comandos:*
/start - Iniciar el bot
/help - Mostrar ayuda
/status - Estado del bot

*📥 Enlaces soportados:*
• instagram.com/p/...
• instagram.com/reel/...
• instagram.com/stories/...

⚠️ Solo perfiles públicos.
"""
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown')


@bot.message_handler(commands=['status'])
def handle_status(message):
    ig_status = '✅ Conectado' if cl.user_id else '❌ No conectado'
    session_status = '✅ Guardada' if os.path.exists('session.json') else '❌ No guardada'
    
    status_text = f"""
📊 *Estado del Bot*

🤖 Bot: ✅ En línea
📸 Instagram: {ig_status}
💾 Sesión: {session_status}
"""
    bot.send_message(message.chat.id, status_text, parse_mode='Markdown')


# ============================================
# MANEJO DE BOTONES
# ============================================
@bot.message_handler(func=lambda m: m.text in ["📥 Cómo usar", "ℹ️ Info", "📊 Estado", "❓ Ayuda"])
def handle_buttons(message):
    if message.text == "📥 Cómo usar":
        text = "📥 *¿Cómo descargar?*\n\n1️⃣ Copia un enlace de Instagram\n2️⃣ Pégalo aquí\n3️⃣ Recibe tu archivo ✅"
        bot.send_message(message.chat.id, text, parse_mode='Markdown')
    
    elif message.text == "ℹ️ Info":
        text = "ℹ️ *Bot de Instagram v2.0*\n\n✅ Fotos y Videos\n✅ Reels\n✅ Carruseles\n✅ Stories"
        bot.send_message(message.chat.id, text, parse_mode='Markdown')
    
    elif message.text == "📊 Estado":
        handle_status(message)
    
    elif message.text == "❓ Ayuda":
        handle_help(message)


# ============================================
# FUNCIÓN PARA REACCIONES (EMOJIS VÁLIDOS)
# ============================================
def set_reaction(chat_id, message_id, emoji):
    """Pone una reacción válida en el mensaje."""
    valid_emojis = ['👍', '❤️', '🔥', '🎉', '😢', '😡', '✅', '❌']
    if emoji not in valid_emojis:
        emoji = '👍'  # Emoji por defecto si no es válido
    
    try:
        bot.set_message_reaction(
            chat_id, 
            message_id, 
            reaction=[telebot.types.ReactionTypeEmoji(emoji)]
        )
    except Exception as e:
        print(f"No se pudo poner reacción: {e}")


# ============================================
# FUNCIÓN PARA PROCESAR STORIES
# ============================================
def process_story(message, url):
    """Procesa una story de Instagram."""
    try:
        set_reaction(message.chat.id, message.message_id, '🔥')
        
        parts = url.split('/stories/')
        if len(parts) < 2:
            raise Exception("URL de story inválida")
        
        story_part = parts[1].split('?')[0].rstrip('/')
        story_parts = story_part.split('/')
        
        username = story_parts[0] if story_parts else None
        story_id = story_parts[1] if len(story_parts) > 1 else None
        
        if not username:
            raise Exception("No se pudo extraer el usuario")
        
        user_id = cl.user_id_from_username(username)
        
        if story_id:
            file_path = cl.story_download(int(story_id), folder=DOWNLOAD_FOLDER)
        else:
            stories = cl.user_stories(user_id)
            if stories:
                file_path = cl.story_download(stories[0].id, folder=DOWNLOAD_FOLDER)
            else:
                raise Exception("No hay stories disponibles")
        
        if file_path:
            if str(file_path).endswith('.mp4'):
                with open(file_path, 'rb') as video_file:
                    bot.send_video(message.chat.id, video_file, caption="✅ Story descargada")
            else:
                with open(file_path, 'rb') as photo_file:
                    bot.send_photo(message.chat.id, photo_file, caption="✅ Story descargada")
            
            if os.path.exists(file_path):
                os.remove(file_path)
        
        set_reaction(message.chat.id, message.message_id, '✅')
        
    except Exception as e:
        print(f"Error en story: {e}")
        set_reaction(message.chat.id, message.message_id, '❌')
        bot.reply_to(message, f"❌ Error: {str(e)[:80]}")


# ============================================
# FUNCIÓN PARA PROCESAR POSTS/REELS/CARRUSELES
# ============================================
def process_post(message, url):
    """Procesa un post, reel o carrusel de Instagram."""
    try:
        media_pk = cl.media_pk_from_url(url)
        media_info = cl.media_info(media_pk)
        
        # FOTO SIMPLE
        if media_info.media_type == 1:
            file_path = cl.photo_download(media_pk, folder=DOWNLOAD_FOLDER)
            with open(file_path, 'rb') as photo_file:
                bot.send_photo(message.chat.id, photo_file, caption="✅ Foto descargada")
            if os.path.exists(file_path):
                os.remove(file_path)
        
        # VIDEO O REEL
        elif media_info.media_type == 2:
            file_path = cl.video_download(media_pk, folder=DOWNLOAD_FOLDER)
            with open(file_path, 'rb') as video_file:
                bot.send_video(message.chat.id, video_file, caption="✅ Video descargado")
            if os.path.exists(file_path):
                os.remove(file_path)
        
        # CARRUSEL
        elif media_info.media_type == 8:
            total_items = len(media_info.resources)
            bot.send_message(message.chat.id, f"📁 Carrusel ({total_items} elementos)")
            
            files_to_send = []
            
            for i, resource in enumerate(media_info.resources):
                try:
                    bot.send_message(message.chat.id, f"⬇️ {i+1}/{total_items}...")
                    
                    if resource.media_type == 2:
                        file_path = cl.video_download(resource.pk, folder=DOWNLOAD_FOLDER)
                    else:
                        file_path = cl.photo_download(resource.pk, folder=DOWNLOAD_FOLDER)
                    
                    files_to_send.append((str(file_path), resource.media_type))
                    
                except Exception as e:
                    print(f"Error elemento {i+1}: {e}")
            
            # Enviar en grupos de 10
            if files_to_send:
                for i in range(0, len(files_to_send), 10):
                    batch = files_to_send[i:i+10]
                    media_group = []
                    
                    for file_path, media_type in batch:
                        try:
                            if media_type == 2:
                                with open(file_path, 'rb') as f:
                                    media_group.append(telebot.types.InputMediaVideo(f))
                            else:
                                with open(file_path, 'rb') as f:
                                    media_group.append(telebot.types.InputMediaPhoto(f))
                        except Exception as e:
                            print(f"Error preparando archivo: {e}")
                    
                    if media_group:
                        bot.send_media_group(message.chat.id, media_group)
                
                for file_path, _ in files_to_send:
                    if os.path.exists(file_path):
                        os.remove(file_path)
        
        set_reaction(message.chat.id, message.message_id, '✅')
            
    except Exception as e:
        print(f"Error procesando: {e}")
        set_reaction(message.chat.id, message.message_id, '❌')
        bot.reply_to(message, f"❌ Error: {str(e)[:80]}")


# ============================================
# FUNCIÓN PRINCIPAL DE PROCESAMIENTO
# ============================================
def process_instagram_link(message, url):
    """Función principal que procesa enlaces de Instagram."""
    try:
        set_reaction(message.chat.id, message.message_id, '🔥')
        
        if '/stories/' in url:
            process_story(message, url)
        else:
            process_post(message, url)
            
    except Exception as e:
        print(f"Error general: {e}")
        set_reaction(message.chat.id, message.message_id, '❌')
        bot.reply_to(message, f"❌ Error: {str(e)[:80]}")


# ============================================
# MANEJADOR DE ENLACES
# ============================================
@bot.message_handler(func=lambda message: "instagram.com" in message.text)
def handle_instagram_link(message):
    url = message.text.strip()
    thread = threading.Thread(target=process_instagram_link, args=(message, url))
    thread.daemon = True
    thread.start()


# ============================================
# MENSAJE POR DEFECTO
# ============================================
@bot.message_handler(func=lambda message: True)
def handle_unknown(message):
    bot.send_message(
        message.chat.id,
        "🤔 No reconozco eso.\n\nEnvía un enlace de Instagram o usa /help",
        parse_mode='Markdown',
        reply_markup=main_keyboard
    )


# ============================================
# INICIAR BOT
# ============================================
if __name__ == '__main__':
    print("🤖 Bot iniciado...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)