# Gestión usuarios

import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from ..database.models import UserProfile, EnglishLevel
from ..database.sheets_client import sheets_client
from ..ai.groq_client import groq_client
from ..ai.prompts import PromptTemplates
import logging

logger = logging.getLogger(__name__)

class UserService:
    """Servicio avanzado de gestión de usuarios"""
    
    def __init__(self):
        self._user_sessions = {}  # Cache en memoria para sesiones activas
        self._session_timeout = timedelta(minutes=30)
    
    async def get_user_profile(self, chat_id: int, **kwargs) -> UserProfile:
        """Obtiene perfil completo del usuario con cache inteligente"""
        
        # Verificar cache de sesión
        if chat_id in self._user_sessions:
            session_data = self._user_sessions[chat_id]
            if datetime.now() < session_data["expires"]:
                return session_data["profile"]
        
        # Obtener de Google Sheets
        profile = await sheets_client.get_or_create_user(chat_id, **kwargs)
        
        # Actualizar cache de sesión
        self._user_sessions[chat_id] = {
            "profile": profile,
            "expires": datetime.now() + self._session_timeout
        }
        
        return profile
    
    async def update_user_level(self, chat_id: int, new_level: EnglishLevel) -> bool:
        """Actualiza nivel del usuario y ajusta contenido"""
        success = await sheets_client.update_user_level(chat_id, new_level)
        
        if success:
            # Invalidar cache
            if chat_id in self._user_sessions:
                del self._user_sessions[chat_id]
            
            logger.info(f"Usuario {chat_id} actualizado a nivel {new_level.value}")
            
            # Generar mensaje personalizado para el cambio de nivel
            level_messages = {
                "basic": "🎉 ¡Felicidades! Ahora estás en nivel Básico. Empezaremos con lo fundamental.",
                "intermediate": "🚀 ¡Excelente! Has alcanzado el nivel Intermedio. Desafíos más interesantes te esperan.",
                "advanced": "🏆 ¡Impresionante! Nivel Avanzado alcanzado. Perfeccionaremos tu inglés profesional."
            }
            
            return True, level_messages.get(new_level.value, "Nivel actualizado correctamente.")
        
        return False, "Error actualizando el nivel."
    
    async def add_vocabulary_seen(self, chat_id: int, words: List[str]) -> bool:
        """Registra palabras de vocabulario vistas por el usuario"""
        try:
            profile = await self.get_user_profile(chat_id)
            
            # Añadir nuevas palabras (evitar duplicados)
            new_words = [w for w in words if w not in profile.vocabulary_seen]
            profile.vocabulary_seen.extend(new_words)
            
            # Limitar a 1000 palabras máximo
            if len(profile.vocabulary_seen) > 1000:
                profile.vocabulary_seen = profile.vocabulary_seen[-1000:]
            
            # TODO: Actualizar en Google Sheets
            # (Implementación específica dependiendo de estructura de datos)
            
            return True
        except Exception as e:
            logger.error(f"Error añadiendo vocabulario: {str(e)}")
            return False
    
    async def increment_lessons_completed(self, chat_id: int) -> bool:
        """Incrementa contador de lecciones completadas"""
        try:
            profile = await self.get_user_profile(chat_id)
            profile.lessons_completed += 1
            
            # TODO: Actualizar en Google Sheets
            
            # Verificar si merece un logro
            if profile.lessons_completed % 5 == 0:
                await self._award_achievement(chat_id, f"completed_{profile.lessons_completed}_lessons")
            
            return True
        except Exception as e:
            logger.error(f"Error incrementando lecciones: {str(e)}")
            return False
    
    async def get_personalized_welcome(self, chat_id: int) -> str:
        """Genera mensaje de bienvenida personalizado"""
        profile = await self.get_user_profile(chat_id)
        
        welcome_templates = {
            "basic": f"""
            👋 ¡Hola {profile.first_name or 'estudiante'}! 
            
            Soy tu tutor de inglés del SENA. 
            Estoy aquí para ayudarte a aprender inglés paso a paso.
            
            Comenzaremos con lo básico:
            • Saludos y presentaciones
            • Vocabulario esencial
            • Frases cotidianas
            
            ¡Vamos a aprender juntos! 🎓
            """,
            
            "intermediate": f"""
            🌟 ¡Bienvenido de nuevo {profile.first_name or 'estudiante'}!
            
            Veo que ya tienes bases sólidas de inglés.
            Ahora profundizaremos en:
            • Conversaciones más complejas
            • Gramática avanzada
            • Vocabulario específico
            
            ¿Listo para el siguiente nivel? 🚀
            """,
            
            "advanced": f"""
            🏆 ¡Excelente tenerte aquí {profile.first_name or 'estudiante'}!
            
            Tu nivel avanzado significa que trabajaremos en:
            • Perfeccionamiento de pronunciación
            • Inglés profesional/empresarial
            • Expresiones idiomáticas complejas
            • Redacción avanzada
            
            ¡Al máximo nivel! 💫
            """
        }
        
        return welcome_templates.get(profile.level.value, welcome_templates["basic"])
    
    async def get_daily_challenge(self, chat_id: int) -> Dict[str, Any]:
        """Genera desafío diario personalizado"""
        profile = await self.get_user_profile(chat_id)
        
        prompt = f"""
        Crea un desafío de inglés diario para un estudiante de nivel {profile.level.value}.
        Incluye:
        1. Un mini-dialogo para completar
        2. 3 palabras nuevas para aprender
        3. Un ejercicio de gramática
        4. Una pregunta de comprensión
        
        Formato JSON:
        {{
            "date": "{datetime.now().strftime('%Y-%m-%d')}",
            "difficulty": "{profile.level.value}",
            "dialogue": {{
                "context": "contexto del diálogo",
                "missing_parts": ["parte1", "parte2"],
                "options": [["op1", "op2"], ["op1", "op2"]]
            }},
            "vocabulary": [
                {{
                    "word": "palabra",
                    "meaning": "significado",
                    "example": "ejemplo"
                }}
            ],
            "grammar_exercise": {{
                "description": "descripción",
                "sentence": "oración a completar",
                "options": ["op1", "op2", "op3"]
            }},
            "comprehension": {{
                "short_text": "texto corto",
                "question": "pregunta",
                "options": ["A", "B", "C", "D"]
            }},
            "points": 100
        }}
        """
        
        try:
            response = await groq_client.generate_response(prompt)
            import json
            challenge = json.loads(response)
            
            # Añadir metadata
            challenge["user_chat_id"] = chat_id
            challenge["completed"] = False
            challenge["score"] = 0
            
            return challenge
        except Exception as e:
            logger.error(f"Error generando desafío: {str(e)}")
            return self._get_default_challenge(profile.level)
    
    def _get_default_challenge(self, level: EnglishLevel) -> Dict[str, Any]:
        """Desafío por defecto en caso de error"""
        defaults = {
            "basic": {
                "dialogue": {
                    "context": "En un restaurante",
                    "missing_parts": ["¿Qué desea ordenar?", "La cuenta, por favor"],
                    "options": [["What would you like to order?", "How are you?"], 
                              ["The check, please", "Thank you"]]
                }
            },
            "intermediate": {
                "dialogue": {
                    "context": "En una entrevista de trabajo",
                    "missing_parts": ["¿Por qué quiere trabajar aquí?", "Mis fortalezas son..."],
                    "options": [["Why do you want to work here?", "What's your name?"],
                              ["My strengths are...", "I don't know"]]
                }
            },
            "advanced": {
                "dialogue": {
                    "context": "Negociación empresarial",
                    "missing_parts": ["Nuestra propuesta incluye...", "¿Cuáles son sus términos?"],
                    "options": [["Our proposal includes...", "We want money"],
                              ["What are your terms?", "How much?"]]
                }
            }
        }
        
        level_data = defaults.get(level.value, defaults["basic"])
        
        return {
            "date": datetime.now().strftime('%Y-%m-%d'),
            "difficulty": level.value,
            "dialogue": level_data["dialogue"],
            "vocabulary": [
                {
                    "word": "essential" if level.value == "basic" else "comprehensive" if level.value == "intermediate" else "meticulous",
                    "meaning": "fundamental" if level.value == "basic" else "exhaustivo" if level.value == "intermediate" else "meticuloso",
                    "example": "Water is essential for life." if level.value == "basic" else 
                              "We need a comprehensive analysis." if level.value == "intermediate" else 
                              "She is meticulous in her work."
                }
            ],
            "points": 100
        }
    
    async def _award_achievement(self, chat_id: int, achievement_key: str):
        """Otorga un logro al usuario"""
        # TODO: Implementar sistema de logros
        logger.info(f"Logro {achievement_key} otorgado a usuario {chat_id}")
    
    async def get_user_statistics(self, chat_id: int) -> Dict[str, Any]:
        """Obtiene estadísticas detalladas del usuario"""
        progress = await sheets_client.get_user_progress(chat_id)
        
        if not progress:
            profile = await self.get_user_profile(chat_id)
            
            return {
                "basic_info": {
                    "chat_id": chat_id,
                    "name": profile.first_name or "Usuario",
                    "level": profile.level.value,
                    "member_since": profile.registration_date.strftime("%Y-%m-%d"),
                    "days_active": (datetime.now() - profile.registration_date).days
                },
                "learning_stats": {
                    "lessons_completed": profile.lessons_completed,
                    "vocabulary_seen": len(profile.vocabulary_seen),
                    "last_activity": profile.last_activity.strftime("%Y-%m-%d %H:%M")
                },
                "message": "Estadísticas completas disponibles próximamente."
            }
        
        return progress
    
    async def cleanup_inactive_sessions(self):
        """Limpia sesiones inactivas"""
        now = datetime.now()
        inactive_users = []
        
        for chat_id, session_data in list(self._user_sessions.items()):
            if now > session_data["expires"]:
                inactive_users.append(chat_id)
                del self._user_sessions[chat_id]
        
        if inactive_users:
            logger.info(f"Sesiones limpiadas: {len(inactive_users)} usuarios inactivos")

# Instancia global
user_service = UserService()