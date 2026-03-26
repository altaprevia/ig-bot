import os
import telebot
from instagrapi import Client
import time

# --- CONFIGURACIÓN SEGURA ---
# Leemos las variables de entorno (se configuran en Render.com)
TOKEN_TELEGRAM = os.environ.get('TOKEN_TELEGRAM')
IG_USER = os.environ.get('IG_USER')
IG_PASS = os.environ.get('IG_PASS')

# Verificación de seguridad
if not TOKEN_TELEGRAM or not IG_USER or not IG_PASS:
    print("ERROR: Faltan las variables de entorno (TOKEN_TELEGRAM, IG_USER, IG_PASS).")
    print("Asegúrate de configurarlas en tu servidor (Render).")
    exit()

# Inicialización
bot = telebot.TeleBot(TOKEN_TELEGRAM)
cl = Client()

# Carpeta para descargas temporales
DOWNLOAD_FOLDER = "downloads"
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

def login_instagram():
    """Intenta loguearse en Instagram."""
    try:
        # Intenta cargar una sesión previa (para evitar bloqueos)
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

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    url = message.text.strip()

    # Verificar si es un enlace de Instagram
    if "instagram.com" not in url:
        return # Ignorar mensajes que no sean links

    try:
        status_msg = bot.reply_to(message, "⏳ Procesando link, espera...")
        
        # Obtener el ID del post
        media_pk = cl.media_pk_from_url(url)
        media_info = cl.media_info(media_pk)
        
        file_path = None
        caption_text = "✅ Descargado con tu bot."

        # Lógica para determinar si es Video, Foto o Carrusel
        if media_info.media_type == 2: # Video o Reel
            file_path = cl.video_download(media_pk, folder=DOWNLOAD_FOLDER)
        elif media_info.media_type == 1: # Foto
            file_path = cl.photo_download(media_pk, folder=DOWNLOAD_FOLDER)
        elif media_info.media_type == 8: # Carrusel (Álbum)
            # Los carruseles tienen varios items. Descargamos el primero o todos?
            # Por simplicidad, descargamos el primero aquí.
            # Si quieres el álbum completo, se necesita lógica extra con send_media_group.
            resource_id = media_info.resources[0].pk
            if media_info.resources[0].media_type == 2:
                file_path = cl.video_download(resource_id, folder=DOWNLOAD_FOLDER)
            else:
                file_path = cl.photo_download(resource_id, folder=DOWNLOAD_FOLDER)
            
            bot.edit_message_text("ℹ️ Este es un carrusel. Enviando el primer elemento.", status_msg.chat.id, status_msg.message_id)

        # Enviar el archivo a Telegram
        if file_path:
            if str(file_path).endswith('.mp4'):
                with open(file_path, 'rb') as video_file:
                    bot.send_video(message.chat.id, video_file, caption=caption_text)
            else:
                with open(file_path, 'rb') as photo_file:
                    bot.send_photo(message.chat.id, photo_file, caption=caption_text)
            
            # Borrar archivo temporal para no llenar el servidor
            if os.path.exists(file_path):
                os.remove(file_path)
            
            # Borrar mensaje de "esperando"
            bot.delete_message(status_msg.chat.id, status_msg.message_id)

    except Exception as e:
        print(f"Error procesando: {e}")
        bot.reply_to(message, f"❌ Ocurrió un error. ¿El perfil es privado? \n(Detalle: {str(e)[:50]}...)")

# Iniciar el bot
if __name__ == '__main__':
    print("Bot iniciado y escuchando mensajes...")
    # Usamos infinity_polling para que no se caiga si hay errores de red
    bot.infinity_polling(timeout=10, long_polling_timeout=5)