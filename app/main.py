# FastAPI app principal

# app/main.py

import logging
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from contextlib import asynccontextmanager
from telegram import Update
from telegram.ext import Application

from .config import settings
from .telegram.bot import get_bot
from .services.user_service import user_service

# Configurar logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Lifespan manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestión del ciclo de vida de la aplicación"""
    # Startup
    logger.info("Starting SENA English Tutor Bot...")
    
    # Inicializar bot de Telegram
    bot = get_bot()
    
    # Configurar webhook si está configurado
    if settings.WEBHOOK_URL:
        logger.info("Configuring webhook mode...")
        await bot.start_webhook()
    else:
        logger.info("Configuring polling mode...")
        # En producción usaríamos webhook, pero polling es útil para desarrollo
        await bot.application.initialize()
        await bot.application.start()
        if bot.application.updater:
            await bot.application.updater.start_polling()
    
    logger.info("Bot started successfully!")
    
    yield
    
    # Shutdown
    logger.info("Shutting down SENA English Tutor Bot...")
    bot = get_bot()
    await bot.stop()
    logger.info("Bot stopped successfully")

# Crear aplicación FastAPI
app = FastAPI(
    title="SENA English Tutor Bot API",
    description="API para el chatbot educativo de inglés del SENA",
    version="1.0.0",
    lifespan=lifespan
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Endpoint para health check
@app.get("/")
async def root():
    """Endpoint raíz para health check"""
    return {
        "status": "online",
        "service": "SENA English Tutor Bot",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Endpoint para webhook de Telegram
@app.post("/webhook")
async def telegram_webhook(request: Request):
    """Endpoint para recibir updates de Telegram"""
    try:
        # Obtener el bot
        bot = get_bot()
        
        # Verificar que sea una solicitud de Telegram
        if not await bot.application.bot.get_webhook_info():
            raise HTTPException(status_code=400, detail="Webhook not configured")
        
        # Procesar el update
        update_data = await request.json()
        update = Update.de_json(update_data, bot.application.bot)
        
        # Procesar el update
        await bot.application.process_update(update)
        
        return JSONResponse(content={"status": "ok"})
    
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Endpoints para estadísticas y administración
@app.get("/api/stats")
async def get_stats():
    """Obtener estadísticas generales del bot"""
    # Esta sería una implementación básica
    # En una implementación real, obtendrías datos de Google Sheets
    return {
        "status": "online",
        "service": "SENA English Tutor Bot",
        "uptime": "0 days",
        "active_users": 0,
        "total_messages": 0
    }

@app.get("/api/user/{chat_id}")
async def get_user_info(chat_id: int):
    """Obtener información de un usuario específico"""
    try:
        profile = await user_service.get_user_profile(chat_id)
        return {
            "chat_id": profile.chat_id,
            "username": profile.username,
            "first_name": profile.first_name,
            "level": profile.level.value,
            "registration_date": profile.registration_date.isoformat(),
            "lessons_completed": profile.lessons_completed,
            "vocabulary_seen_count": len(profile.vocabulary_seen)
        }
    except Exception as e:
        logger.error(f"Error getting user info: {str(e)}")
        raise HTTPException(status_code=404, detail="User not found")

# Endpoint para limpiar cache
@app.post("/api/admin/clear-cache")
async def clear_cache(admin_key: str = None):
    """Endpoint para limpiar cache (solo para administración)"""
    # Verificar clave de administración (en producción usarías autenticación real)
    if admin_key != "SENA_ADMIN_123":  # Esto debería estar en variables de entorno
        raise HTTPException(status_code=403, detail="Forbidden")
    
    try:
        # Limpiar cache de servicios
        await user_service.cleanup_inactive_sessions()
        
        # También limpiar cache de Google Sheets si es necesario
        from ..database.sheets_client import sheets_client
        await sheets_client.clear_cache()
        
        return {"status": "cache_cleared", "message": "All caches cleared successfully"}
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        raise HTTPException(status_code=500, detail="Error clearing cache")

# Ejecutar la aplicación
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )