# Manejo de Telegram

import logging
from typing import Optional, Dict, Any
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from ..config import settings
from .keyboards import Keyboards
from .handlers import CommandHandlers, MessageHandlers
from ..services.user_service import UserService

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class SenaEnglishBot:
    """Bot principal de Telegram para el SENA"""
    
    def __init__(self):
        self.application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
        self.keyboards = Keyboards()
        self.command_handlers = CommandHandlers()
        self.message_handlers = MessageHandlers()
        self.user_service = UserService()
        
        # Registrar handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Registra todos los handlers de comandos y mensajes"""
        
        # Comandos
        self.application.add_handler(CommandHandler("start", self.command_handlers.start))
        self.application.add_handler(CommandHandler("help", self.command_handlers.help))
        self.application.add_handler(CommandHandler("level", self.command_handlers.change_level))
        self.application.add_handler(CommandHandler("vocabulary", self.command_handlers.vocabulary))
        self.application.add_handler(CommandHandler("practice", self.command_handlers.practice))
        self.application.add_handler(CommandHandler("sena_info", self.command_handlers.sena_info))
        self.application.add_handler(CommandHandler("progress", self.command_handlers.progress))
        
        # Callback queries (botones)
        self.application.add_handler(CallbackQueryHandler(self.message_handlers.handle_callback))
        
        # Mensajes de texto
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.message_handlers.handle_text)
        )
        
        # Mensajes de voz (para práctica de pronunciación)
        self.application.add_handler(
            MessageHandler(filters.VOICE, self.message_handlers.handle_voice)
        )
        
        # Documentos (PDFs para análisis)
        self.application.add_handler(
            MessageHandler(filters.Document.ALL, self.message_handlers.handle_document)
        )
    
    async def start_webhook(self):
        """Inicia el bot en modo webhook (para producción)"""
        await self.application.bot.set_webhook(
            url=f"{settings.WEBHOOK_URL}/webhook",
            allowed_updates=Update.ALL_TYPES
        )
        logger.info("Webhook configurado correctamente")
    
    async def start_polling(self):
        """Inicia el bot en modo polling (para desarrollo)"""
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        logger.info("Bot iniciado en modo polling")
    
    async def stop(self):
        """Detiene el bot"""
        await self.application.stop()

# Singleton del bot
bot_instance = None

def get_bot() -> SenaEnglishBot:
    """Retorna la instancia única del bot"""
    global bot_instance
    if bot_instance is None:
        bot_instance = SenaEnglishBot()
    return bot_instance