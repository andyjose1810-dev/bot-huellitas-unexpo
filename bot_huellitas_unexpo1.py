import logging
import os
import json
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    ConversationHandler,
)
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
from urllib.parse import parse_qs, urlparse

# --- Configuraciones del bot (ahora se leen de variables de entorno) ---
# Asegúrate de configurar estas variables en la consola de AWS Lambda o Replit Secrets
TOKEN = os.environ.get("TELEGRAM_TOKEN")
GRUPO_CHAT_ID_STR = os.environ.get("GRUPO_CHAT_ID")
GRUPO_CHAT_ID = int(GRUPO_CHAT_ID_STR) if GRUPO_CHAT_ID_STR else None

# Define los estados de la conversación
(
    PEDIR_TIPO_ANIMAL,
    PEDIR_UBICACION,
    PEDIR_ESTADO_SALUD,
    PEDIR_NOMBRE_CONTACTO,
    PEDIR_NUMERO_CONTACTO,
    PEDIR_DESCRIPCION,
    PEDIR_FOTO,
    CONFIRMAR_REPORTE,
) = range(8)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# --- Mensajes ---
MENSAJE_BIENVENIDA = (
    "👋 ¡Bienvenido al bot de Ayuda para Animales: Huellitas Unexpo!\n\n"
    "Estos son los comandos disponibles:\n"
    "✅ /reportar - Reporta un animal en necesidad.\n"
    "💚 /donacion - Información para hacer una donación.\n"
    "🐶 /adoptar - Ver los animalitos disponibles para adopción.\n\n"
    "Estoy para ayudarte ❤️"
)

MENSAJE_ADOPTAR = (
    "🐾 *¡Dale un hogar a un amigo peludo!* 🐾\n\n"
    "En nuestro campus universitario hay muchos perritos y gatitos "
    "buscando un hogar lleno de amor. ¿Te gustaría adoptar a un compañero fiel?\n\n"
    "✨ *Beneficios de adoptar:*\n"
    "• Un amigo incondicional\n"
    "• Reduces el abandono animal\n"
    "• Mejoras tu salud emocional\n"
    "• Le das una segunda oportunidad\n\n"
    "📲 Conoce a nuestros peluditos disponibles:\n"
    "Visita nuestro Instagram [@huellitas_unexpo](https://www.instagram.com/huellitas_unexpo?igsh=MXFnc3pmM29vcGJyZw==) "
    "para ver fotos y características de cada uno.\n\n"
    "💚 *La adopción es un acto de amor y responsabilidad.*\n"
    "¡Transforma una vida hoy! 🐶🐱"
)

MENSAJE_DONACION = (
    "👋 ¡Bienvenido al bot de Ayuda para Animales: Huellitas Unexpo!\n\n"
    "Estos son los métodos disponibles:\n\n"
    "Donación Monetaria:\n"
    "Banco de Venezuela (0102)\n"
    "Tlfn: 04241228086\n"
    "6367083\n\n"
    "Sitio para llevar insumos (Medicina, comida, entre otros):\n"
    "La UNEXPO en Caracas se encuentra en el kilómetro 1, vía El Junquito, La Yaguara, Parroquia Antímano, Municipio Libertador.\n\n"
    "Muchas gracias por su ayuda ❤️"
)

# --- Funciones del formulario ---

async def iniciar_reporte(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia la conversación del formulario y pide el tipo de animal."""
    await update.message.reply_text(
        "📝 Ingrese el tipo de animal (ej. perro, gato, ave):",
        reply_markup=ReplyKeyboardRemove(),
    )
    return PEDIR_TIPO_ANIMAL

async def recibir_tipo_animal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda el tipo de animal y pide la ubicación."""
    context.user_data["tipo_animal"] = update.message.text
    await update.message.reply_text("📍 ¿Cuál es la ubicación exacta del animal?")
    return PEDIR_UBICACION

async def recibir_ubicacion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda la ubicación y pide el estado de salud."""
    context.user_data["ubicacion"] = update.message.text
    await update.message.reply_text("❤️ ¿Cuál es el estado de salud del animal? (ej. herido, sano, desnutrido)")
    return PEDIR_ESTADO_SALUD

async def recibir_estado_salud(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda el estado de salud y pide el nombre de contacto."""
    context.user_data["estado_salud"] = update.message.text
    await update.message.reply_text("📞 Por favor, ingrese un nombre de contacto. Si no desea proporcionarlo, escriba 'Anónimo' o 'Omitir'.")
    return PEDIR_NOMBRE_CONTACTO

async def recibir_nombre_contacto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda el nombre de contacto. Si es anónimo, omite el número y pasa a la descripción."""
    nombre_contacto = update.message.text.strip().lower()

    if nombre_contacto in ["anónimo", "anonimo", "omitir"]:
        context.user_data["nombre_contacto"] = "Anónimo"
        context.user_data["numero_contacto"] = "Omitido"
        await update.message.reply_text("✅ Entendido. El reporte será anónimo. Por favor, escriba una descripción adicional.")
        return PEDIR_DESCRIPCION
    else:
        context.user_data["nombre_contacto"] = update.message.text
        await update.message.reply_text("📱 Por favor, ingrese un número de contacto:")
        return PEDIR_NUMERO_CONTACTO

async def recibir_numero_contacto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda el número de contacto y pide la descripción."""
    context.user_data["numero_contacto"] = update.message.text
    await update.message.reply_text("✍️ Por favor, escriba una descripción adicional del reporte.")
    return PEDIR_DESCRIPCION

async def recibir_descripcion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda la descripción y pide la foto."""
    context.user_data["descripcion"] = update.message.text
    await update.message.reply_text("📸 Ahora, si tiene una foto, envíela. Si no, escriba 'omitir'.")
    return PEDIR_FOTO

async def recibir_foto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda la foto y confirma el reporte."""
    if update.message.photo:
        context.user_data["foto"] = update.message.photo[-1].file_id
        await update.message.reply_text("✅ Foto recibida.")
    else:
        context.user_data["foto"] = None
        await update.message.reply_text("✅ Foto omitida.")

    reporte_resumen = (
        f"**✅ Resumen de su reporte:**\n\n"
        f"**Tipo de animal:** {context.user_data.get('tipo_animal')}\n"
        f"**Ubicación:** {context.user_data.get('ubicacion')}\n"
        f"**Estado de salud:** {context.user_data.get('estado_salud')}\n"
    )

    if context.user_data.get('nombre_contacto') != "Anónimo":
        reporte_resumen += f"**Nombre de contacto:** {context.user_data.get('nombre_contacto')}\n"
        reporte_resumen += f"**Número de contacto:** {context.user_data.get('numero_contacto')}\n"

    reporte_resumen += f"**Descripción:** {context.user_data.get('descripcion')}\n"

    await update.message.reply_text(reporte_resumen, parse_mode="Markdown")
    await update.message.reply_text("¿Desea enviar el reporte? Escriba 'Enviar' para confirmar o /cancelar para detener.")
    return CONFIRMAR_REPORTE

async def confirmar_reporte(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Envía el reporte final y termina la conversación."""
    if update.message.text and update.message.text.lower() == 'enviar':
        user = update.effective_user
        
        if context.user_data.get('nombre_contacto') == "Anónimo":
            reporte_final = f"⚠️ **NUEVO REPORTE ANÓNIMO** ⚠️\n\n"
        else:
            reporte_final = f"⚠️ **NUEVO REPORTE** ⚠️\n\n"
            reporte_final += f"**De:** @{user.username} (ID: `{user.id}`)\n"

        reporte_final += (
            f"**Tipo de animal:** {context.user_data.get('tipo_animal')}\n"
            f"**Ubicación:** {context.user_data.get('ubicacion')}\n"
            f"**Estado de salud:** {context.user_data.get('estado_salud')}\n"
        )
        
        if context.user_data.get('nombre_contacto') != "Anónimo":
            reporte_final += f"**Nombre del contacto:** {context.user_data.get('nombre_contacto')}\n"
            reporte_final += f"**Número de contacto:** {context.user_data.get('numero_contacto')}\n"

        reporte_final += f"**Descripción:** {context.user_data.get('descripcion')}\n"

        await context.bot.send_message(
            chat_id=GRUPO_CHAT_ID, text=reporte_final, parse_mode="Markdown"
        )

        if context.user_data.get("foto"):
            await context.bot.send_photo(
                chat_id=GRUPO_CHAT_ID, photo=context.user_data.get("foto")
            )
        
        await update.message.reply_text(
            f"✅ ¡Reporte enviado con éxito! Un rescatista tomará el caso pronto. "
            f"Si necesita ayuda inmediata, puede comunicarse a este número: **04241228086**."
        )

        context.user_data.clear()
        return ConversationHandler.END
    else:
        await update.message.reply_text("Por favor, escriba 'Enviar' para confirmar.")
        return CONFIRMAR_REPORTE

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela y termina el formulario."""
    await update.message.reply_text(
        "❌ El reporte ha sido cancelado. Puedes usar /start para empezar de nuevo."
    )
    context.user_data.clear()
    return ConversationHandler.END

# --- Funciones principales (mantienen tu lógica original) ---
async def say_hello(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(MENSAJE_BIENVENIDA)
    
async def donacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(MENSAJE_DONACION)

async def adoptar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        MENSAJE_ADOPTAR, 
        parse_mode='Markdown',
        disable_web_page_preview=True
    )
# --- Esta es la NUEVA sección para Cloudflare Workers ---
# Es el punto de entrada que Cloudflare espera.
class MyRequestHandler(BaseHTTPRequestHandler):
    async def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        body = json.loads(post_data)

        # Crea la aplicación del bot
        application = Application.builder().token(TOKEN).build()
    
        # Define los manejadores como antes
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("reportar", iniciar_reporte)],
            states={
                PEDIR_TIPO_ANIMAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_tipo_animal)],
                PEDIR_UBICACION: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_ubicacion)],
                PEDIR_ESTADO_SALUD: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_estado_salud)],
                PEDIR_NOMBRE_CONTACTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_nombre_contacto)],
                PEDIR_NUMERO_CONTACTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_numero_contacto)],
                PEDIR_DESCRIPCION: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_descripcion)],
                PEDIR_FOTO: [MessageHandler(filters.PHOTO | filters.TEXT & ~filters.COMMAND, recibir_foto)],
                CONFIRMAR_REPORTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirmar_reporte)],
            },
            fallbacks=[CommandHandler("cancelar", cancelar)],
        )

        application.add_handler(conv_handler)
        application.add_handler(CommandHandler("start", say_hello))
        application.add_handler(CommandHandler("donacion", donacion))
        application.add_handler(CommandHandler("adoptar", adoptar))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, say_hello))
        
        update = Update.de_json(body, application.bot)
        await application.process_update(update)

        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps("OK").encode())

async def serve():
    server = HTTPServer(('0.0.0.0', 8000), MyRequestHandler)
    await server.serve_forever()

# Punto de entrada para Cloudflare
async def fetch(request):
    try:
        from pyodide import serve
        return await serve.serve(request, MyRequestHandler)
    except Exception as e:
        return Response(f"Error: {e}", status=500)
