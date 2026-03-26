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

# Verificación de variables de entorno
if not TOKEN_TELEGRAM or not IG_USER or not IG_PASS:
    print("ERROR: Faltan variables de entorno (TOKEN_TELEGRAM, IG_USER, IG_PASS).")
    print("Asegúrate de configurarlas en tu servidor.")
    exit()

# Inicialización
bot = telebot.TeleBot(TOKEN_TELEGRAM)
cl = Client()

# Carpeta para descargas temporales
DOWNLOAD_FOLDER = "downloads"
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# ============================================
# LOGIN INSTAGRAM
# ============================================
def login_instagram():
    """Intenta loguearse en Instagram."""
    try:
        SESSION_FILE = "session.json"
        if os.path.exists(SESSION_FILE):
            cl.load_settings(SESSION_FILE)
        
        print("Intentando login en Instagram...")
        cl.login(IG_USER, IG_PASS)
        cl.dump_settings(SESSION_FILE)
        print("✅ Login exitoso.")
        return True
    except Exception as e:
        print(f"❌ Error de login en Instagram: {e}")
        return False

# Ejecutar login al arrancar
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
    """Comando /start - Mensaje de bienvenida."""
    welcome_text = """
👋 *¡Bienvenido al Bot de Instagram!*

Descarga contenido de Instagram de forma rápida y sencilla.

*✨ Tipos soportados:*
📸 Fotos
🎬 Videos / Reels
📁 Carruseles completos
⭐ Stories

*📌 Cómo usar:*
Simplemente envía un enlace de Instagram y yo me encargo.

*💡 Ejemplos:*
`https://instagram.com/p/xxxxx/`
`https://instagram.com/reel/xxxxx/`
`https://instagram.com/stories/usuario/xxxxx/`

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
    """Comando /help - Mostrar ayuda."""
    help_text = """
📚 *Ayuda del Bot*

*🔧 Comandos disponibles:*
/start - Iniciar el bot
/help - Mostrar esta ayuda
/status - Ver estado del bot

*📥 Enlaces soportados:*
• `instagram.com/p/...` → Posts
• `instagram.com/reel/...` → Reels
• `instagram.com/stories/...` → Stories

*ℹ️ Notas:*
⚠️ Solo funciona con perfiles públicos
⚠️ Los carruseles se envían completos
⚠️ Máximo 10 archivos por mensaje (límite de Telegram)
"""
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown')


@bot.message_handler(commands=['status'])
def handle_status(message):
    """Comando /status - Estado del bot."""
    ig_status = '✅ Conectado' if cl.user_id else '❌ No conectado'
    session_status = '✅ Guardada' if os.path.exists('session.json') else '❌ No guardada'
    
    status_text = f"""
📊 *Estado del Bot*

🤖 Bot: ✅ En línea
📸 Instagram: {ig_status}
💾 Sesión: {session_status}

_Multi-procesamiento activado._
"""
    bot.send_message(message.chat.id, status_text, parse_mode='Markdown')


# ============================================
# MANEJO DE BOTONES DEL TECLADO
# ============================================
@bot.message_handler(func=lambda m: m.text in ["📥 Cómo usar", "ℹ️ Info", "📊 Estado", "❓ Ayuda"])
def handle_buttons(message):
    """Maneja los botones del teclado principal."""
    if message.text == "📥 Cómo usar":
        text = """
📥 *¿Cómo descargar?*

1️⃣ Copia un enlace de Instagram
2️⃣ Pégalo en este chat
3️⃣ Espera la reacción 👀
4️⃣ Recibe tu archivo ✅

_¡Así de simple!_
"""
        bot.send_message(message.chat.id, text, parse_mode='Markdown')
    
    elif message.text == "ℹ️ Info":
        text = """
ℹ️ *Sobre este Bot*

*Versión:* 2.0
*Creado con:* Python + Telebot + Instagrapi

*Funciones:*
✅ Descarga fotos y videos
✅ Soporte para Reels
✅ Carruseles completos
✅ Stories de Instagram
✅ Procesamiento paralelo
✅ Indicadores de progreso
"""
        bot.send_message(message.chat.id, text, parse_mode='Markdown')
    
    elif message.text == "📊 Estado":
        handle_status(message)
    
    elif message.text == "❓ Ayuda":
        handle_help(message)


# ============================================
# FUNCIÓN PARA PROCESAR STORIES
# ============================================
def process_story(message, url):
    """Procesa una story de Instagram."""
    try:
        # Extraer usuario de la URL
        # Formato: instagram.com/stories/USERNAME/STORY_ID
        parts = url.split('/stories/')
        if len(parts) < 2:
            raise Exception("URL de story inválida")
        
        story_part = parts[1].split('?')[0].rstrip('/')
        story_parts = story_part.split('/')
        
        username = story_parts[0] if story_parts else None
        story_id = story_parts[1] if len(story_parts) > 1 else None
        
        if not username:
            raise Exception("No se pudo extraer el usuario de la URL")
        
        # Obtener user_id
        user_id = cl.user_id_from_username(username)
        
        # Descargar story
        if story_id:
            file_path = cl.story_download(int(story_id), folder=DOWNLOAD_FOLDER)
        else:
            # Descargar la última story del usuario
            stories = cl.user_stories(user_id)
            if stories:
                file_path = cl.story_download(stories[0].id, folder=DOWNLOAD_FOLDER)
            else:
                raise Exception("Este usuario no tiene stories disponibles")
        
        # Enviar archivo
        if file_path:
            if str(file_path).endswith('.mp4'):
                with open(file_path, 'rb') as video_file:
                    bot.send_video(message.chat.id, video_file, caption="✅ Story descargada")
            else:
                with open(file_path, 'rb') as photo_file:
                    bot.send_photo(message.chat.id, photo_file, caption="✅ Story descargada")
            
            # Eliminar archivo temporal
            if os.path.exists(file_path):
                os.remove(file_path)
        
        # Reacción: Completado ✅
        bot.set_message_reaction(
            message.chat.id, 
            message.message_id, 
            reaction=[telebot.types.ReactionTypeEmoji('✅')]
        )
        
    except Exception as e:
        print(f"Error en story: {e}")
        bot.set_message_reaction(
            message.chat.id, 
            message.message_id, 
            reaction=[telebot.types.ReactionTypeEmoji('❌')]
        )
        bot.reply_to(message, f"❌ Error con la story: {str(e)[:100]}")


# ============================================
# FUNCIÓN PARA PROCESAR POSTS/REELS/CARRUSELES
# ============================================
def process_post(message, url):
    """Procesa un post, reel o carrusel de Instagram."""
    try:
        media_pk = cl.media_pk_from_url(url)
        media_info = cl.media_info(media_pk)
        
        # ============================================
        # FOTO SIMPLE
        # ============================================
        if media_info.media_type == 1:
            file_path = cl.photo_download(media_pk, folder=DOWNLOAD_FOLDER)
            with open(file_path, 'rb') as photo_file:
                bot.send_photo(message.chat.id, photo_file, caption="✅ Foto descargada")
            if os.path.exists(file_path):
                os.remove(file_path)
        
        # ============================================
        # VIDEO O REEL
        # ============================================
        elif media_info.media_type == 2:
            file_path = cl.video_download(media_pk, folder=DOWNLOAD_FOLDER)
            with open(file_path, 'rb') as video_file:
                bot.send_video(message.chat.id, video_file, caption="✅ Video descargado")
            if os.path.exists(file_path):
                os.remove(file_path)
        
        # ============================================
        # CARRUSEL (descargar TODO)
        # ============================================
        elif media_info.media_type == 8:
            total_items = len(media_info.resources)
            bot.send_message(message.chat.id, f"📁 Carrusel detectado ({total_items} elementos)")
            
            files_to_send = []
            
            # Descargar cada elemento
            for i, resource in enumerate(media_info.resources):
                try:
                    # Mostrar progreso
                    bot.send_message(
                        message.chat.id, 
                        f"⬇️ Descargando {i+1}/{total_items}..."
                    )
                    
                    if resource.media_type == 2:  # Video
                        file_path = cl.video_download(resource.pk, folder=DOWNLOAD_FOLDER)
                    else:  # Foto
                        file_path = cl.photo_download(resource.pk, folder=DOWNLOAD_FOLDER)
                    
                    files_to_send.append((str(file_path), resource.media_type))
                    
                except Exception as e:
                    print(f"Error descargando elemento {i+1}: {e}")
                    bot.send_message(message.chat.id, f"⚠️ Error en elemento {i+1}, continuando...")
            
            # Enviar archivos en grupos de máximo 10 (límite de Telegram)
            if files_to_send:
                for i in range(0, len(files_to_send), 10):
                    batch = files_to_send[i:i+10]
                    media_group = []
                    
                    for file_path, media_type in batch:
                        try:
                            if media_type == 2:  # Video
                                with open(file_path, 'rb') as f:
                                    media_group.append(telebot.types.InputMediaVideo(f))
                            else:  # Foto
                                with open(file_path, 'rb') as f:
                                    media_group.append(telebot.types.InputMediaPhoto(f))
                        except Exception as e:
                            print(f"Error preparando archivo: {e}")
                    
                    if media_group:
                        bot.send_media_group(message.chat.id, media_group)
                
                # Eliminar archivos temporales
                for file_path, _ in files_to_send:
                    if os.path.exists(file_path):
                        os.remove(file_path)
        
        # Reacción: Completado ✅
        bot.set_message_reaction(
            message.chat.id, 
            message.message_id, 
            reaction=[telebot.types.ReactionTypeEmoji('✅')]
        )
            
    except Exception as e:
        print(f"Error procesando post: {e}")
        bot.set_message_reaction(
            message.chat.id, 
            message.message_id, 
            reaction=[telebot.types.ReactionTypeEmoji('❌')]
        )
        bot.reply_to(message, f"❌ Error: {str(e)[:100]}")


# ============================================
# FUNCIÓN PRINCIPAL DE PROCESAMIENTO
# ============================================
def process_instagram_link(message, url):
    """Función principal que determina el tipo de contenido y lo procesa."""
    try:
        # Reacción: Procesando 👀
        bot.set_message_reaction(
            message.chat.id, 
            message.message_id, 
            reaction=[telebot.types.ReactionTypeEmoji('👀')]
        )
        
        # Detectar tipo de contenido
        if '/stories/' in url:
            process_story(message, url)
        else:
            process_post(message, url)
            
    except Exception as e:
        print(f"Error general: {e}")
        bot.set_message_reaction(
            message.chat.id, 
            message.message_id, 
            reaction=[telebot.types.ReactionTypeEmoji('❌')]
        )
        bot.reply_to(message, f"❌ Error: {str(e)[:100]}")


# ============================================
# MANEJADOR DE ENLACES DE INSTAGRAM
# ============================================
@bot.message_handler(func=lambda message: "instagram.com" in message.text)
def handle_instagram_link(message):
    """Detecta enlaces de Instagram y los procesa en paralelo."""
    url = message.text.strip()
    
    # Procesar en un hilo separado (permite múltiples enlaces simultáneos)
    thread = threading.Thread(target=process_instagram_link, args=(message, url))
    thread.daemon = True
    thread.start()


# ============================================
# MENSAJE POR DEFECTO
# ============================================
@bot.message_handler(func=lambda message: True)
def handle_unknown(message):
    """Maneja mensajes que no son comandos ni enlaces de Instagram."""
    bot.send_message(
        message.chat.id,
        "🤔 No reconozco ese comando.\n\n"
        "📌 Envía un *enlace de Instagram* para descargar contenido.\n\n"
        "Escribe /help para ver las opciones disponibles.",
        parse_mode='Markdown',
        reply_markup=main_keyboard
    )


# ============================================
# INICIAR BOT
# ============================================
if __name__ == '__main__':
    print("🤖 Bot iniciado y escuchando mensajes...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)