# Google Sheets

import gspread
from google.oauth2.service_account import Credentials
from typing import List, Dict, Any, Optional
import asyncio
from datetime import datetime, timedelta
import pandas as pd
from ..config import settings
from .models import UserProfile, VocabularyItem, EnglishLevel
import logging

logger = logging.getLogger(__name__)

class GoogleSheetsClient:
    """Cliente avanzado para Google Sheets con caching y optimización"""
    
    def __init__(self):
        self.scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        self._client = None
        self._spreadsheet = None
        self._cache = {}
        self._cache_expiry = {}
        self.CACHE_DURATION = timedelta(minutes=5)
        
    def _get_client(self):
        """Obtiene cliente de Google Sheets (singleton)"""
        if self._client is None:
            try:
                # Cargar credenciales desde variable de entorno o archivo
                if isinstance(settings.GOOGLE_SHEETS_CREDENTIALS, dict):
                    creds_dict = settings.GOOGLE_SHEETS_CREDENTIALS
                else:
                    import json
                    creds_dict = json.loads(settings.GOOGLE_SHEETS_CREDENTIALS)
                
                creds = Credentials.from_service_account_info(creds_dict, scopes=self.scopes)
                self._client = gspread.authorize(creds)
                logger.info("Cliente Google Sheets inicializado")
            except Exception as e:
                logger.error(f"Error inicializando Google Sheets: {str(e)}")
                raise
        
        return self._client
    
    def _get_spreadsheet(self):
        """Obtiene la spreadsheet principal"""
        if self._spreadsheet is None:
            client = self._get_client()
            self._spreadsheet = client.open_by_key(settings.SPREADSHEET_ID)
        return self._spreadsheet
    
    async def get_or_create_user(self, chat_id: int, username: str = None, 
                               first_name: str = None) -> UserProfile:
        """Obtiene o crea un usuario en Google Sheets"""
        
        # Verificar cache primero
        cache_key = f"user_{chat_id}"
        if cache_key in self._cache and self._is_cache_valid(cache_key):
            return self._cache[cache_key]
        
        try:
            sheet = self._get_spreadsheet().worksheet("users")
            
            # Buscar usuario existente
            records = sheet.get_all_records()
            user_row = None
            row_number = None
            
            for i, record in enumerate(records, start=2):  # start=2 porque la fila 1 es encabezados
                if str(record.get("chat_id")) == str(chat_id):
                    user_row = record
                    row_number = i
                    break
            
            if user_row:
                # Usuario existe, actualizar última actividad
                user_profile = UserProfile(
                    chat_id=chat_id,
                    username=user_row.get("username"),
                    first_name=user_row.get("first_name"),
                    level=EnglishLevel(user_row.get("level", "basic")),
                    registration_date=datetime.fromisoformat(user_row.get("registration_date")),
                    last_activity=datetime.now(),
                    vocabulary_seen=user_row.get("vocabulary_seen", "").split(",") if user_row.get("vocabulary_seen") else [],
                    lessons_completed=int(user_row.get("lessons_completed", 0))
                )
                
                # Actualizar última actividad
                sheet.update_cell(row_number, 6, datetime.now().isoformat())  # Columna F
                
            else:
                # Crear nuevo usuario
                user_profile = UserProfile(
                    chat_id=chat_id,
                    username=username,
                    first_name=first_name,
                    level=EnglishLevel.BASIC,
                    registration_date=datetime.now(),
                    last_activity=datetime.now()
                )
                
                # Añadir nueva fila
                new_row = [
                    chat_id,
                    username or "",
                    first_name or "",
                    user_profile.level.value,
                    user_profile.registration_date.isoformat(),
                    user_profile.last_activity.isoformat(),
                    "",
                    0,
                    datetime.now().isoformat()  # created_at
                ]
                sheet.append_row(new_row)
            
            # Actualizar cache
            self._cache[cache_key] = user_profile
            self._cache_expiry[cache_key] = datetime.now() + self.CACHE_DURATION
            
            return user_profile
            
        except Exception as e:
            logger.error(f"Error obteniendo/creando usuario: {str(e)}")
            # Retornar perfil básico en caso de error
            return UserProfile(
                chat_id=chat_id,
                username=username,
                first_name=first_name,
                level=EnglishLevel.BASIC
            )
    
    async def update_user_level(self, chat_id: int, new_level: EnglishLevel) -> bool:
        """Actualiza el nivel de inglés de un usuario"""
        try:
            sheet = self._get_spreadsheet().worksheet("users")
            records = sheet.get_all_records()
            
            for i, record in enumerate(records, start=2):
                if str(record.get("chat_id")) == str(chat_id):
                    sheet.update_cell(i, 4, new_level.value)  # Columna D = nivel
                    
                    # Invalidar cache
                    cache_key = f"user_{chat_id}"
                    if cache_key in self._cache:
                        del self._cache[cache_key]
                    
                    logger.info(f"Nivel actualizado para usuario {chat_id}: {new_level.value}")
                    return True
            
            return False
        except Exception as e:
            logger.error(f"Error actualizando nivel: {str(e)}")
            return False
    
    async def get_vocabulary_by_category(self, category: str, 
                                       level: Optional[EnglishLevel] = None,
                                       limit: int = 20) -> List[VocabularyItem]:
        """Obtiene vocabulario por categoría y nivel"""
        cache_key = f"vocab_{category}_{level.value if level else 'all'}"
        
        if cache_key in self._cache and self._is_cache_valid(cache_key):
            return self._cache[cache_key]
        
        try:
            sheet = self._get_spreadsheet().worksheet("vocabulary")
            records = sheet.get_all_records()
            
            vocabulary = []
            for record in records:
                if record.get("category", "").lower() == category.lower():
                    if level and record.get("complexity", "").lower() != level.value:
                        continue
                    
                    vocab_item = VocabularyItem(
                        id=record.get("id", ""),
                        category=record.get("category", ""),
                        english_word=record.get("english_word", ""),
                        spanish_translation=record.get("spanish_translation", ""),
                        example_sentence=record.get("example_sentence", ""),
                        complexity=EnglishLevel(record.get("complexity", "basic")),
                        pronunciation=record.get("pronunciation")
                    )
                    vocabulary.append(vocab_item)
                    
                    if len(vocabulary) >= limit:
                        break
            
            # Ordenar por complejidad si no hay nivel específico
            if not level:
                level_order = {"basic": 0, "intermediate": 1, "advanced": 2}
                vocabulary.sort(key=lambda x: level_order.get(x.complexity.value, 0))
            
            # Actualizar cache
            self._cache[cache_key] = vocabulary
            self._cache_expiry[cache_key] = datetime.now() + self.CACHE_DURATION
            
            return vocabulary
            
        except Exception as e:
            logger.error(f"Error obteniendo vocabulario: {str(e)}")
            return []
    
    async def get_categories(self) -> List[str]:
        """Obtiene todas las categorías de vocabulario disponibles"""
        cache_key = "categories"
        
        if cache_key in self._cache and self._is_cache_valid(cache_key):
            return self._cache[cache_key]
        
        try:
            sheet = self._get_spreadsheet().worksheet("vocabulary")
            records = sheet.get_all_records()
            
            categories = set()
            for record in records:
                category = record.get("category", "").strip()
                if category:
                    categories.add(category)
            
            sorted_categories = sorted(list(categories))
            
            # Actualizar cache
            self._cache[cache_key] = sorted_categories
            self._cache_expiry[cache_key] = datetime.now() + self.CACHE_DURATION
            
            return sorted_categories
            
        except Exception as e:
            logger.error(f"Error obteniendo categorías: {str(e)}")
            return ["daily_life", "work", "education", "food", "transport"]
    
    async def save_conversation_context(self, chat_id: int, user_message: str, 
                                      bot_response: str) -> bool:
        """Guarda contexto de conversación para memoria a largo plazo"""
        try:
            sheet = self._get_spreadsheet().worksheet("conversation_history")
            
            new_row = [
                chat_id,
                datetime.now().isoformat(),
                user_message,
                bot_response,
                "active"
            ]
            
            sheet.append_row(new_row)
            logger.info(f"Conversación guardada para usuario {chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error guardando conversación: {str(e)}")
            return False
    
    async def get_user_progress(self, chat_id: int) -> Dict[str, Any]:
        """Obtiene progreso detallado del usuario"""
        try:
            # Obtener datos de múltiples hojas
            users_sheet = self._get_spreadsheet().worksheet("users")
            vocab_sheet = self._get_spreadsheet().worksheet("vocabulary")
            history_sheet = self._get_spreadsheet().worksheet("conversation_history")
            
            # Datos del usuario
            user_data = await self.get_or_create_user(chat_id)
            
            # Conteo de palabras aprendidas
            vocab_records = vocab_sheet.get_all_records()
            learned_words = 0
            for record in vocab_records:
                if str(chat_id) in record.get("learned_by", ""):
                    learned_words += 1
            
            # Actividad reciente
            history_records = history_sheet.get_all_records()
            recent_messages = 0
            last_week = datetime.now() - timedelta(days=7)
            
            for record in history_records:
                if str(record.get("chat_id")) == str(chat_id):
                    message_date = datetime.fromisoformat(record.get("timestamp", ""))
                    if message_date > last_week:
                        recent_messages += 1
            
            # Calcular estadísticas
            days_active = (datetime.now() - user_data.registration_date).days + 1
            avg_daily_messages = recent_messages / 7 if recent_messages > 0 else 0
            
            progress = {
                "user": {
                    "chat_id": chat_id,
                    "username": user_data.username,
                    "first_name": user_data.first_name,
                    "level": user_data.level.value,
                    "days_active": days_active,
                    "registration_date": user_data.registration_date.strftime("%Y-%m-%d")
                },
                "stats": {
                    "lessons_completed": user_data.lessons_completed,
                    "words_learned": learned_words,
                    "vocabulary_seen": len(user_data.vocabulary_seen),
                    "recent_messages": recent_messages,
                    "avg_daily_messages": round(avg_daily_messages, 1)
                },
                "achievements": await self._calculate_achievements(chat_id, user_data, learned_words),
                "level_progress": await self._calculate_level_progress(user_data, learned_words)
            }
            
            return progress
            
        except Exception as e:
            logger.error(f"Error obteniendo progreso: {str(e)}")
            return {}
    
    async def _calculate_achievements(self, chat_id: int, user_data: UserProfile, 
                                    learned_words: int) -> List[Dict[str, Any]]:
        """Calcula logros desbloqueados"""
        achievements = []
        
        # Logros basados en lecciones
        if user_data.lessons_completed >= 1:
            achievements.append({"name": "Primera Lección", "icon": "🎯"})
        if user_data.lessons_completed >= 5:
            achievements.append({"name": "Aprendiz Dedicado", "icon": "📚"})
        if user_data.lessons_completed >= 10:
            achievements.append({"name": "Maestro en Formación", "icon": "🏆"})
        
        # Logros basados en vocabulario
        if learned_words >= 10:
            achievements.append({"name": "Vocabulario Básico", "icon": "🔤"})
        if learned_words >= 50:
            achievements.append({"name": "Vocabulario Intermedio", "icon": "📖"})
        if learned_words >= 100:
            achievements.append({"name": "Vocabulario Avanzado", "icon": "🧠"})
        
        # Logros basados en tiempo
        days_active = (datetime.now() - user_data.registration_date).days
        if days_active >= 7:
            achievements.append({"name": "Primera Semana", "icon": "🗓️"})
        if days_active >= 30:
            achievements.append({"name": "Un Mes de Estudio", "icon": "⭐"})
        
        return achievements
    
    async def _calculate_level_progress(self, user_data: UserProfile, 
                                      learned_words: int) -> Dict[str, Any]:
        """Calcula progreso hacia el siguiente nivel"""
        level_requirements = {
            "basic": {"words": 50, "lessons": 5, "messages": 20},
            "intermediate": {"words": 150, "lessons": 15, "messages": 50},
            "advanced": {"words": 300, "lessons": 30, "messages": 100}
        }
        
        current_level = user_data.level.value
        next_level = None
        
        if current_level == "basic":
            next_level = "intermediate"
        elif current_level == "intermediate":
            next_level = "advanced"
        else:
            return {"next_level": None, "progress_percentage": 100, "requirements": {}}
        
        requirements = level_requirements[current_level]
        
        # Calcular porcentaje de progreso
        word_progress = min(learned_words / requirements["words"] * 100, 100)
        lesson_progress = min(user_data.lessons_completed / requirements["lessons"] * 100, 100)
        
        total_progress = (word_progress * 0.4 + lesson_progress * 0.4) / 100
        
        return {
            "next_level": next_level,
            "progress_percentage": round(total_progress * 100, 1),
            "requirements": requirements,
            "current_stats": {
                "words_learned": learned_words,
                "lessons_completed": user_data.lessons_completed
            }
        }
    
    async def get_sena_information(self, topic: str = "general") -> Dict[str, Any]:
        """Obtiene información sobre el SENA"""
        try:
            sheet = self._get_spreadsheet().worksheet("sena_info")
            records = sheet.get_all_records()
            
            for record in records:
                if record.get("topic", "").lower() == topic.lower():
                    return {
                        "topic": record.get("topic"),
                        "title": record.get("title"),
                        "content_basic": record.get("content_basic"),
                        "content_intermediate": record.get("content_intermediate"),
                        "content_advanced": record.get("content_advanced"),
                        "links": record.get("links", "").split(",") if record.get("links") else [],
                        "updated": record.get("last_updated")
                    }
            
            # Información general por defecto
            return {
                "topic": "general",
                "title": "Servicio Nacional de Aprendizaje - SENA",
                "content_basic": "El SENA es una institución pública que ofrece educación gratuita en Colombia.",
                "content_intermediate": "El Servicio Nacional de Aprendizaje (SENA) es una institución pública colombiana que ofrece formación profesional integral para el trabajo.",
                "content_advanced": "Fundado en 1957, el SENA es una entidad pública descentralizada del Gobierno de Colombia adscrita al Ministerio del Trabajo, que ofrece formación profesional integral para la incorporación y desarrollo de las personas en actividades productivas que contribuyan al desarrollo social, económico y tecnológico del país.",
                "links": ["https://www.sena.edu.co", "https://oferta.senasofiaplus.edu.co"],
                "updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo información SENA: {str(e)}")
            return self._get_default_sena_info()
    
    def _get_default_sena_info(self) -> Dict[str, Any]:
        """Información por defecto del SENA"""
        return {
            "topic": "general",
            "title": "Servicio Nacional de Aprendizaje - SENA",
            "content_basic": "El SENA ofrece educación gratuita para trabajos en Colombia. Tiene muchos programas para aprender.",
            "content_intermediate": "El SENA es la principal institución de formación para el trabajo en Colombia, con presencia en todo el territorio nacional.",
            "content_advanced": "El SENA opera a través de centros de formación en todo el país, ofreciendo programas técnicos, tecnológicos y complementarios en diversas áreas del conocimiento.",
            "links": ["https://www.sena.edu.co"],
            "updated": datetime.now().isoformat()
        }
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Verifica si el cache es válido"""
        if cache_key not in self._cache_expiry:
            return False
        return datetime.now() < self._cache_expiry[cache_key]
    
    async def clear_cache(self):
        """Limpia toda la cache"""
        self._cache.clear()
        self._cache_expiry.clear()
        logger.info("Cache limpiada")
    
    async def backup_database(self, backup_name: str = None):
        """Crea un backup de la base de datos"""
        try:
            if not backup_name:
                backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            spreadsheet = self._get_spreadsheet()
            backup = spreadsheet.copy(title=backup_name)
            
            logger.info(f"Backup creado: {backup_name} (ID: {backup.id})")
            return backup.id
            
        except Exception as e:
            logger.error(f"Error creando backup: {str(e)}")
            return None

# Instancia global
sheets_client = GoogleSheetsClient()