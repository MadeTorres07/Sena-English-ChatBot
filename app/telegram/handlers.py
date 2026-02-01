# Manejadores de comandos

import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from telegram import Update, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from ..database.models import EnglishLevel
from ..services.user_service import user_service
from ..services.vocab_service import vocab_service
from ..ai.groq_client import groq_client
from ..ai.prompts import PromptTemplates
from .keyboards import Keyboards
from ..database.sheets_client import sheets_client

logger = logging.getLogger(__name__)

class CommandHandlers:
    """Manejadores de comandos de Telegram"""
    
    def __init__(self):
        self.keyboards = Keyboards()
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manejador del comando /start"""
        chat_id = update.effective_chat.id
        user = update.effective_user
        
        logger.info(f"Nuevo usuario: {user.id} - {user.first_name}")
        
        # Obtener o crear perfil de usuario
        profile = await user_service.get_user_profile(
            chat_id=chat_id,
            username=user.username,
            first_name=user.first_name
        )
        
        # Mensaje de bienvenida personalizado
        welcome_message = await user_service.get_personalized_welcome(chat_id)
        
        # Enviar mensaje de bienvenida con menú principal
        await update.message.reply_text(
            welcome_message,
            reply_markup=self.keyboards.get_main_menu()
        )
        
        # Si es nuevo usuario, preguntar nivel
        if (datetime.now() - profile.registration_date).seconds < 60:  # Usuario nuevo
            await self._ask_user_level(update, context)
    
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manejador del comando /help"""
        help_text = """
        🤖 *SENA English Tutor Bot - Ayuda*
        
        *Comandos disponibles:*
        /start - Iniciar el bot
        /help - Mostrar esta ayuda
        /level - Cambiar nivel de inglés
        /vocabulary - Aprender vocabulario
        /practice - Practicar inglés
        /sena_info - Información sobre el SENA
        /progress - Ver tu progreso
        
        *Menús principales:*
        📚 Vocabulario - Aprende palabras nuevas por categoría
        💬 Practicar - Ejercicios y conversación
        🏫 Info SENA - Información sobre el SENA
        📊 Mi Progreso - Estadísticas de aprendizaje
        ⚙️ Cambiar Nivel - Ajusta tu nivel de inglés
        🆘 Ayuda - Muestra este mensaje
        
        *Características:*
        • Corrección automática de inglés
        • Vocabulario por niveles
        • Lecciones personalizadas
        • Seguimiento de progreso
        • Memoria conversacional
        
        ¿Necesitas más ayuda? ¡Solo escribe tu pregunta!
        """
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def change_level(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manejador del comando /level"""
        await self._ask_user_level(update, context)
    
    async def vocabulary(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manejador del comando /vocabulary"""
        message = "📚 *Selecciona una categoría de vocabulario:*"
        
        await update.message.reply_text(
            message,
            parse_mode='Markdown',
            reply_markup=self.keyboards.get_vocabulary_categories()
        )
    
    async def practice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manejador del comando /practice"""
        message = "💬 *¿Qué te gustaría practicar hoy?*"
        
        await update.message.reply_text(
            message,
            parse_mode='Markdown',
            reply_markup=self.keyboards.get_practice_options()
        )
    
    async def sena_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manejador del comando /sena_info"""
        message = "🏫 *Selecciona un tema sobre el SENA:*"
        
        await update.message.reply_text(
            message,
            parse_mode='Markdown',
            reply_markup=self.keyboards.get_sena_topics()
        )
    
    async def progress(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manejador del comando /progress"""
        chat_id = update.effective_chat.id
        
        # Obtener estadísticas del usuario
        stats = await user_service.get_user_statistics(chat_id)
        
        if not stats:
            await update.message.reply_text(
                "📊 *Tu progreso aparecerá aquí pronto.*\n"
                "¡Sigue practicando! 💪",
                parse_mode='Markdown'
            )
            return
        
        # Formatear mensaje de progreso
        progress_message = self._format_progress_message(stats)
        
        await update.message.reply_text(
            progress_message,
            parse_mode='Markdown',
            reply_markup=self.keyboards.get_main_menu()
        )
    
    async def _ask_user_level(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Pregunta al usuario su nivel de inglés"""
        message = (
            "📊 *¿Cuál es tu nivel de inglés?*\n\n"
            "🟢 *Básico*: Conoces lo fundamental\n"
            "🟡 *Intermedio*: Puedes mantener conversaciones\n"
            "🔴 *Avanzado*: Te expresas con fluidez\n\n"
            "O haz el *Test de Nivel* si no estás seguro."
        )
        
        await update.message.reply_text(
            message,
            parse_mode='Markdown',
            reply_markup=self.keyboards.get_level_selector()
        )
    
    def _format_progress_message(self, stats: Dict[str, Any]) -> str:
        """Formatea las estadísticas en un mensaje legible"""
        
        basic_info = stats.get("basic_info", {})
        learning_stats = stats.get("learning_stats", {})
        achievements = stats.get("achievements", [])
        level_progress = stats.get("level_progress", {})
        
        message = f"📊 *Progreso de {basic_info.get('name', 'Usuario')}*\n\n"
        
        # Información básica
        message += f"*Nivel actual:* {basic_info.get('level', 'Básico').title()}\n"
        message += f"*Miembro desde:* {basic_info.get('member_since', 'Reciente')}\n"
        message += f"*Días activo:* {basic_info.get('days_active', 0)}\n\n"
        
        # Estadísticas de aprendizaje
        message += "*📈 Estadísticas de aprendizaje:*\n"
        message += f"• Lecciones completadas: {learning_stats.get('lessons_completed', 0)}\n"
        message += f"• Palabras vistas: {learning_stats.get('vocabulary_seen', 0)}\n"
        message += f"• Última actividad: {learning_stats.get('last_activity', 'Hoy')}\n\n"
        
        # Progreso hacia siguiente nivel
        if level_progress.get("next_level"):
            next_level = level_progress["next_level"]
            progress_percent = level_progress.get("progress_percentage", 0)
            
            message += f"*🎯 Progreso hacia nivel {next_level.title()}:*\n"
            message += f"{progress_percent}% completado\n\n"
            
            # Barra de progreso visual
            bars = int(progress_percent / 10)
            progress_bar = "🟩" * bars + "⬜" * (10 - bars)
            message += f"{progress_bar}\n\n"
        
        # Logros
        if achievements:
            message += "*🏆 Logros desbloqueados:*\n"
            for achievement in achievements[:5]:  # Mostrar máximo 5
                message += f"{achievement.get('icon', '🎯')} {achievement.get('name', 'Logro')}\n"
        
        message += "\n¡Sigue así! Cada día de práctica te acerca a tu meta. 💪"
        
        return message

class MessageHandlers:
    """Manejadores de mensajes de texto y callback queries"""
    
    def __init__(self):
        self.keyboards = Keyboards()
        self.user_conversations = {}  # Cache de conversaciones activas
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manejador de mensajes de texto"""
        chat_id = update.effective_chat.id
        user_message = update.message.text
        
        logger.info(f"Mensaje de {chat_id}: {user_message}")
        
        # Verificar si es respuesta a menú principal
        if user_message in ["📚 Vocabulario", "💬 Practicar", "🏫 Info SENA", 
                          "📊 Mi Progreso", "⚙️ Cambiar Nivel", "🆘 Ayuda"]:
            await self._handle_main_menu_selection(update, user_message)
            return
        
        # Obtener perfil de usuario
        profile = await user_service.get_user_profile(chat_id)
        
        # Verificar si hay conversación activa
        if chat_id in self.user_conversations:
            conversation = self.user_conversations[chat_id]
            
            # Manejar respuestas a ejercicios específicos
            if conversation.get("type") == "vocabulary_exercise":
                await self._handle_vocabulary_exercise_response(update, conversation, user_message)
                return
            elif conversation.get("type") == "correction":
                await self._handle_correction_response(update, conversation, user_message)
                return
        
        # Procesamiento de mensaje normal con IA
        await self._process_with_ai(update, profile, user_message)
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manejador de callback queries (botones inline)"""
        query = update.callback_query
        await query.answer()
        
        chat_id = update.effective_chat.id
        callback_data = query.data
        
        logger.info(f"Callback de {chat_id}: {callback_data}")
        
        # Manejar diferentes tipos de callbacks
        if callback_data.startswith("level_"):
            await self._handle_level_selection(update, callback_data)
        
        elif callback_data.startswith("vocab_"):
            await self._handle_vocabulary_selection(update, callback_data)
        
        elif callback_data.startswith("practice_"):
            await self._handle_practice_selection(update, callback_data)
        
        elif callback_data.startswith("sena_"):
            await self._handle_sena_selection(update, callback_data)
        
        elif callback_data.startswith("quiz_"):
            await self._handle_quiz_answer(update, callback_data)
        
        elif callback_data == "main_menu":
            await self._return_to_main_menu(update)
        
        elif callback_data in ["yes", "no"]:
            await self._handle_yes_no_response(update, callback_data)
        
        else:
            await query.edit_message_text(
                "Opción no reconocida. Usa /help para ver las opciones disponibles."
            )
    
    async def handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manejador de mensajes de voz (para práctica de pronunciación)"""
        chat_id = update.effective_chat.id
        voice = update.message.voice
        
        message = (
            "🎤 *He recibido tu mensaje de voz!*\n\n"
            "Actualmente estoy trabajando en la funcionalidad de análisis de voz.\n"
            "Pronto podré ayudarte con tu pronunciación.\n\n"
            "Mientras tanto, puedes practicar escribiendo. ✍️"
        )
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manejador de documentos (PDFs, textos)"""
        chat_id = update.effective_chat.id
        document = update.message.document
        
        message = (
            "📄 *He recibido tu documento!*\n\n"
            "Actualmente estoy procesando documentos en inglés para análisis.\n"
            "Pronto podré ayudarte a analizar textos y PDFs.\n\n"
            "Por ahora, puedes enviarme texto directamente. 📝"
        )
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def _handle_main_menu_selection(self, update: Update, selection: str):
        """Maneja selecciones del menú principal"""
        chat_id = update.effective_chat.id
        
        if selection == "📚 Vocabulario":
            await update.message.reply_text(
                "📚 *Selecciona una categoría de vocabulario:*",
                parse_mode='Markdown',
                reply_markup=self.keyboards.get_vocabulary_categories()
            )
        
        elif selection == "💬 Practicar":
            await update.message.reply_text(
                "💬 *¿Qué te gustaría practicar hoy?*",
                parse_mode='Markdown',
                reply_markup=self.keyboards.get_practice_options()
            )
        
        elif selection == "🏫 Info SENA":
            await update.message.reply_text(
                "🏫 *Selecciona un tema sobre el SENA:*",
                parse_mode='Markdown',
                reply_markup=self.keyboards.get_sena_topics()
            )
        
        elif selection == "📊 Mi Progreso":
            await update.message.reply_text(
                "📊 *Obteniendo tus estadísticas...*",
                parse_mode='Markdown'
            )
            # Llamar al handler de progreso
            from .handlers import CommandHandlers
            handler = CommandHandlers()
            await handler.progress(update, None)
        
        elif selection == "⚙️ Cambiar Nivel":
            await update.message.reply_text(
                "📊 *Selecciona tu nuevo nivel de inglés:*",
                parse_mode='Markdown',
                reply_markup=self.keyboards.get_level_selector()
            )
        
        elif selection == "🆘 Ayuda":
            from .handlers import CommandHandlers
            handler = CommandHandlers()
            await handler.help(update, None)
    
    async def _handle_level_selection(self, update: Update, callback_data: str):
        """Maneja selección de nivel de inglés"""
        query = update.callback_query
        chat_id = update.effective_chat.id
        
        if callback_data == "level_test":
            await self._start_level_test(update)
            return
        
        # Extraer nivel del callback data
        level_map = {
            "level_basic": EnglishLevel.BASIC,
            "level_intermediate": EnglishLevel.INTERMEDIATE,
            "level_advanced": EnglishLevel.ADVANCED
        }
        
        selected_level = level_map.get(callback_data)
        if not selected_level:
            await query.edit_message_text("Nivel no reconocido.")
            return
        
        # Actualizar nivel del usuario
        success, message = await user_service.update_user_level(chat_id, selected_level)
        
        if success:
            response = f"✅ *Nivel actualizado a {selected_level.value.title()}!*\n\n{message}"
            await query.edit_message_text(response, parse_mode='Markdown')
            
            # Ofrecer comenzar con vocabulario
            await self._offer_vocabulary_after_level(update)
        else:
            await query.edit_message_text("❌ Error actualizando el nivel. Intenta nuevamente.")
    
    async def _handle_vocabulary_selection(self, update: Update, callback_data: str):
        """Maneja selección de categoría de vocabulario"""
        query = update.callback_query
        chat_id = update.effective_chat.id
        
        # Mapear callback a categoría real
        category_map = {
            "vocab_daily": "daily_life",
            "vocab_work": "work",
            "vocab_education": "education",
            "vocab_shopping": "shopping",
            "vocab_food": "food",
            "vocab_transport": "transport",
            "vocab_health": "health",
            "vocab_art": "art_culture",
            "vocab_tech": "technology",
            "vocab_sports": "sports"
        }
        
        category = category_map.get(callback_data, "daily_life")
        
        # Obtener perfil del usuario
        profile = await user_service.get_user_profile(chat_id)
        
        # Obtener vocabulario de la categoría
        await query.edit_message_text(f"📖 *Buscando vocabulario de {category.replace('_', ' ').title()}...*", 
                                    parse_mode='Markdown')
        
        vocabulary = await vocab_service.get_category_vocabulary(
            category=category,
            user_level=profile.level,
            limit=10
        )
        
        if not vocabulary:
            await query.edit_message_text(
                f"❌ No se encontró vocabulario para *{category.replace('_', ' ').title()}*.\n"
                f"Intenta con otra categoría.",
                parse_mode='Markdown'
            )
            return
        
        # Crear y mostrar lección
        lesson = await vocab_service.create_vocabulary_lesson(vocabulary, profile.level)
        
        # Formatear mensaje de la lección
        lesson_message = self._format_vocabulary_lesson(lesson, category)
        
        await query.edit_message_text(
            lesson_message,
            parse_mode='Markdown'
        )
        
        # Preparar ejercicio basado en la lección
        if lesson.get("exercises"):
            await self._start_vocabulary_exercise(update, lesson, category)
    
    async def _handle_practice_selection(self, update: Update, callback_data: str):
        """Maneja selección de tipo de práctica"""
        query = update.callback_query
        chat_id = update.effective_chat.id
        
        practice_map = {
            "practice_conversation": "💬 Conversación libre",
            "practice_correction": "📝 Corrección de texto",
            "practice_exercises": "🎯 Ejercicios gramaticales",
            "practice_pronunciation": "🎤 Práctica de pronunciación",
            "practice_daily": "📚 Lección diaria",
            "practice_challenge": "🏆 Desafío del día"
        }
        
        practice_type = practice_map.get(callback_data, "💬 Conversación libre")
        
        await query.edit_message_text(
            f"🔄 *Preparando {practice_type.lower()}...*",
            parse_mode='Markdown'
        )
        
        # Iniciar la práctica seleccionada
        if callback_data == "practice_conversation":
            await self._start_conversation_practice(update)
        elif callback_data == "practice_correction":
            await self._start_correction_practice(update)
        elif callback_data == "practice_exercises":
            await self._start_grammar_exercises(update)
        elif callback_data == "practice_daily":
            await self._start_daily_lesson(update)
        elif callback_data == "practice_challenge":
            await self._start_daily_challenge(update)
        else:
            # Práctica no implementada aún
            await query.edit_message_text(
                f"⚙️ *{practice_type}*\n\n"
                f"Esta funcionalidad estará disponible pronto.\n"
                f"Mientras tanto, puedes usar otras prácticas. 😊",
                parse_mode='Markdown'
            )
    
    async def _handle_sena_selection(self, update: Update, callback_data: str):
        """Maneja selección de tema del SENA"""
        query = update.callback_query
        
        topic_map = {
            "sena_what": "general",
            "sena_programs": "programs",
            "sena_locations": "locations",
            "sena_events": "events",
            "sena_employment": "employment",
            "sena_website": "website"
        }
        
        topic = topic_map.get(callback_data, "general")
        
        # Obtener información del SENA
        sena_info = await sheets_client.get_sena_information(topic)
        
        # Formatear respuesta según nivel del usuario
        profile = await user_service.get_user_profile(update.effective_chat.id)
        
        if profile.level == EnglishLevel.BASIC:
            content = sena_info.get("content_basic", sena_info.get("content_intermediate", ""))
        elif profile.level == EnglishLevel.INTERMEDIATE:
            content = sena_info.get("content_intermediate", sena_info.get("content_basic", ""))
        else:
            content = sena_info.get("content_advanced", sena_info.get("content_intermediate", ""))
        
        # Crear mensaje
        message = f"🏫 *{sena_info.get('title', 'Información SENA')}*\n\n"
        message += f"{content}\n\n"
        
        if sena_info.get("links"):
            message += "*Enlaces útiles:*\n"
            for link in sena_info["links"][:3]:  # Máximo 3 enlaces
                message += f"• {link}\n"
        
        await query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=self.keyboards.get_main_menu_inline()
        )
    
    async def _process_with_ai(self, update: Update, profile, user_message: str):
        """Procesa mensaje del usuario con IA"""
        chat_id = update.effective_chat.id
        
        # Obtener contexto de conversación previa
        context_messages = []
        if chat_id in self.user_conversations:
            conv = self.user_conversations[chat_id]
            if "messages" in conv:
                context_messages = conv["messages"][-3:]  # Últimos 3 mensajes
        
        # Crear prompt con contexto
        prompt = PromptTemplates.get_conversation_prompt(
            user_message=user_message,
            context=context_messages,
            level=profile.level.value
        )
        
        system_prompt = PromptTemplates.get_level_based_system_prompt(
            level=profile.level.value,
            user_name=profile.first_name or "Estudiante"
        )
        
        # Generar respuesta con IA
        await update.message.reply_chat_action("typing")
        
        try:
            ai_response = await groq_client.generate_response(
                prompt=prompt,
                system_message=system_prompt,
                temperature=0.7
            )
            
            # Guardar en historial de conversación
            if chat_id not in self.user_conversations:
                self.user_conversations[chat_id] = {"messages": []}
            
            self.user_conversations[chat_id]["messages"].append({
                "user": user_message,
                "bot": ai_response
            })
            
            # Limitar historial a 10 mensajes
            if len(self.user_conversations[chat_id]["messages"]) > 10:
                self.user_conversations[chat_id]["messages"] = \
                    self.user_conversations[chat_id]["messages"][-10:]
            
            # Enviar respuesta
            await update.message.reply_text(
                ai_response,
                parse_mode='Markdown',
                reply_markup=self.keyboards.get_main_menu()
            )
            
            # Guardar conversación en Google Sheets
            await sheets_client.save_conversation_context(
                chat_id=chat_id,
                user_message=user_message,
                bot_response=ai_response
            )
            
        except Exception as e:
            logger.error(f"Error procesando mensaje con IA: {str(e)}")
            
            error_response = (
                "😅 *Ups, hubo un problema procesando tu mensaje.*\n\n"
                "Puedes intentar:\n"
                "1. Reformular tu pregunta\n"
                "2. Usar el menú de opciones\n"
                "3. Intentar más tarde\n\n"
                "¡Gracias por tu comprensión! 🙏"
            )
            
            await update.message.reply_text(
                error_response,
                parse_mode='Markdown',
                reply_markup=self.keyboards.get_main_menu()
            )
    
    def _format_vocabulary_lesson(self, lesson: Dict[str, Any], category: str) -> str:
        """Formatea una lección de vocabulario para mostrar"""
        message = f"📚 *Lección: {lesson.get('title', 'Vocabulario')}*\n\n"
        
        # Descripción
        message += f"{lesson.get('description', '')}\n\n"
        
        # Vocabulario (mostrar primeras 5 palabras)
        vocab_list = lesson.get("vocabulary", [])
        if vocab_list:
            message += "*📖 Palabras nuevas:*\n"
            for i, word in enumerate(vocab_list[:5], 1):
                message += f"{i}. *{word.get('english_word', '')}*"
                if word.get('pronunciation'):
                    message += f" {word.get('pronunciation')}"
                message += f" - {word.get('spanish_translation', '')}\n"
                if word.get('example_sentence'):
                    message += f"   _Ej: {word.get('example_sentence')}_\n"
                message += "\n"
        
        # Objetivos de aprendizaje
        objectives = lesson.get("learning_objectives", [])
        if objectives:
            message += "*🎯 Objetivos de aprendizaje:*\n"
            for obj in objectives[:3]:
                message += f"• {obj}\n"
        
        message += f"\n⏱️ *Tiempo estimado:* {lesson.get('estimated_time', '10-15 minutos')}"
        
        return message
    
    async def _start_vocabulary_exercise(self, update: Update, lesson: Dict[str, Any], category: str):
        """Inicia un ejercicio de vocabulario"""
        query = update.callback_query
        chat_id = update.effective_chat.id
        
        exercises = lesson.get("exercises", [])
        if not exercises:
            return
        
        # Seleccionar primer ejercicio
        exercise = exercises[0]
        
        # Guardar estado de ejercicio
        self.user_conversations[chat_id] = {
            "type": "vocabulary_exercise",
            "lesson": lesson,
            "current_exercise": 0,
            "category": category,
            "score": 0,
            "start_time": datetime.now().isoformat()
        }
        
        # Preparar mensaje del ejercicio
        exercise_message = self._format_exercise_message(exercise)
        
        # Enviar ejercicio
        if exercise["type"] == "matching":
            # Para emparejamiento, mostrar instrucciones
            await query.message.reply_text(
                exercise_message,
                parse_mode='Markdown',
                reply_markup=self.keyboards.get_main_menu()
            )
            
            # Pedir que escriban los pares
            await query.message.reply_text(
                "✍️ *Escribe los pares separados por guión:*\n"
                "Ejemplo: hello-hola, goodbye-adiós",
                parse_mode='Markdown'
            )
        
        elif exercise["type"] == "fill_blank":
            # Para completar oraciones, mostrar opciones
            await query.message.reply_text(
                exercise_message,
                parse_mode='Markdown',
                reply_markup=self.keyboards.get_main_menu()
            )
            
            # Para cada oración
            for i, sentence in enumerate(exercise.get("sentences", []), 1):
                options = sentence.get("options", [])
                if len(options) >= 3:
                    # Crear teclado con opciones
                    options_keyboard = self.keyboards.get_quiz_options(options, f"ex1_{i}")
                    await query.message.reply_text(
                        f"*Oración {i}:* {sentence.get('sentence', '')}",
                        parse_mode='Markdown',
                        reply_markup=options_keyboard
                    )
    
    def _format_exercise_message(self, exercise: Dict[str, Any]) -> str:
        """Formatea un ejercicio para mostrar"""
        message = f"🎯 *Ejercicio: {exercise.get('title', 'Práctica')}*\n\n"
        message += f"{exercise.get('instructions', 'Completa el ejercicio:')}\n\n"
        
        if exercise["type"] == "matching":
            pairs = exercise.get("pairs", [])
            if pairs:
                english_words = [pair["english"] for pair in pairs]
                if exercise.get("shuffle", False):
                    import random
                    random.shuffle(english_words)
                
                message += "*Palabras en inglés:*\n"
                for word in english_words:
                    message += f"• {word}\n"
                
                message += "\n*Traducciones en español:*\n"
                spanish_words = [pair["spanish"] for pair in pairs]
                if exercise.get("shuffle", False):
                    random.shuffle(spanish_words)
                
                for word in spanish_words:
                    message += f"• {word}\n"
        
        elif exercise["type"] == "fill_blank":
            sentences = exercise.get("sentences", [])
            if sentences:
                message += "*Completa las oraciones:*\n"
                for i, sentence in enumerate(sentences, 1):
                    message += f"{i}. {sentence.get('sentence', '')}\n"
        
        return message
    
    async def _start_conversation_practice(self, update: Update):
        """Inicia práctica de conversación"""
        query = update.callback_query
        chat_id = update.effective_chat.id
        
        # Obtener perfil del usuario
        profile = await user_service.get_user_profile(chat_id)
        
        # Generar tema de conversación según nivel
        topics_by_level = {
            "basic": ["Your family", "Your daily routine", "Your favorite food", "Your hobbies"],
            "intermediate": ["Your job or studies", "Travel experiences", "Future plans", "Cultural differences"],
            "advanced": ["Current events", "Professional challenges", "Philosophical questions", "Global issues"]
        }
        
        topics = topics_by_level.get(profile.level.value, topics_by_level["basic"])
        import random
        topic = random.choice(topics)
        
        # Crear prompt para iniciar conversación
        prompt = PromptTemplates.get_conversation_prompt(
            user_message=f"Let's talk about {topic}. Please ask me a question to start the conversation.",
            context=[],
            level=profile.level.value
        )
        
        system_prompt = PromptTemplates.get_level_based_system_prompt(
            level=profile.level.value,
            user_name=profile.first_name or "Student"
        )
        
        # Generar pregunta inicial
        initial_question = await groq_client.generate_response(
            prompt=prompt,
            system_message=system_prompt
        )
        
        # Guardar estado de conversación práctica
        self.user_conversations[chat_id] = {
            "type": "conversation_practice",
            "topic": topic,
            "messages": [],
            "start_time": datetime.now().isoformat(),
            "level": profile.level.value
        }
        
        await query.edit_message_text(
            f"💬 *Práctica de Conversación*\n\n"
            f"*Tema:* {topic}\n\n"
            f"*Instrucciones:* Responde en inglés a las preguntas. "
            f"Te ayudaré a mejorar tu fluidez.\n\n"
            f"*Pregunta inicial:*\n{initial_question}",
            parse_mode='Markdown',
            reply_markup=self.keyboards.get_main_menu()
        )
    
    async def _start_correction_practice(self, update: Update):
        """Inicia práctica de corrección"""
        query = update.callback_query
        
        await query.edit_message_text(
            "📝 *Práctica de Corrección*\n\n"
            "Escribe una oración o párrafo en inglés y la corregiré, "
            "dándote sugerencias para mejorar.\n\n"
            "*Ejemplos:*\n"
            "• 'I has a dog'\n"
            "• 'She go to school yesterday'\n"
            "• 'We are enjoy the movie'\n\n"
            "¡Escribe tu texto ahora! ✍️",
            parse_mode='Markdown',
            reply_markup=self.keyboards.get_main_menu()
        )
        
        # Marcar que esperamos texto para corrección
        self.user_conversations[update.effective_chat.id] = {
            "type": "awaiting_correction"
        }
    
    async def _start_grammar_exercises(self, update: Update):
        """Inicia ejercicios gramaticales"""
        query = update.callback_query
        
        await query.edit_message_text(
            "⚙️ *Ejercicios Gramaticales*\n\n"
            "Esta funcionalidad estará disponible en la próxima actualización.\n\n"
            "Mientras tanto, puedes:\n"
            "• Practicar conversación 💬\n"
            "• Aprender vocabulario 📚\n"
            "• Solicitar correcciones 📝",
            parse_mode='Markdown',
            reply_markup=self.keyboards.get_main_menu()
        )
    
    async def _start_daily_lesson(self, update: Update):
        """Inicia lección diaria"""
        query = update.callback_query
        chat_id = update.effective_chat.id
        
        # Obtener perfil del usuario
        profile = await user_service.get_user_profile(chat_id)
        
        # Generar lección diaria
        prompt = f"""
        Create a daily English lesson for a {profile.level.value} level student.
        Include:
        1. A grammar point with explanation
        2. 5 new vocabulary words related to the grammar
        3. 3 practice sentences
        4. A short dialogue using the new concepts
        
        Format the response for a Telegram message with Markdown.
        """
        
        await query.edit_message_text(
            "📚 *Generando tu lección diaria...*",
            parse_mode='Markdown'
        )
        
        try:
            daily_lesson = await groq_client.generate_response(
                prompt=prompt,
                temperature=0.7,
                max_tokens=1500
            )
            
            await query.edit_message_text(
                f"📅 *Lección Diaria - {datetime.now().strftime('%d/%m/%Y')}*\n\n"
                f"{daily_lesson}",
                parse_mode='Markdown',
                reply_markup=self.keyboards.get_main_menu()
            )
            
        except Exception as e:
            logger.error(f"Error generando lección diaria: {str(e)}")
            
            await query.edit_message_text(
                "😅 *No pude generar la lección diaria en este momento.*\n\n"
                "Puedes intentar:\n"
                "• Aprender vocabulario 📚\n"
                "• Practicar conversación 💬\n"
                "• Volver más tarde ⏰",
                parse_mode='Markdown',
                reply_markup=self.keyboards.get_main_menu()
            )

async def _start_daily_challenge(self, update: Update):
    """Inicia desafío diario"""
    query = update.callback_query
    chat_id = update.effective_chat.id
    
    challenge = await user_service.get_daily_challenge(chat_id)
    
    if not challenge or "error" in challenge:
        await query.edit_message_text(
            "🏆 *Desafío Diario*\n\n"
            "No hay desafíos disponibles en este momento.\n\n"
            "¡Vuelve mañana para un nuevo desafío! ⭐",
            parse_mode='Markdown',
            reply_markup=self.keyboards.get_main_menu()
        )
        return
    
    # Formatear desafío
    message = f"🏆 *Desafío Diario - {challenge.get('date', 'Hoy')}*\n\n"
    message += f"*Dificultad:* {challenge.get('difficulty', '').title()}\n"
    message += f"*Puntos posibles:* {challenge.get('points', 100)}\n\n"
    
    # Mostrar diálogo
    if "dialogue" in challenge:
        dialogue = challenge["dialogue"]
        message += f"*Diálogo:* {dialogue.get('context', '')}\n\n"
        
        missing_parts = dialogue.get('missing_parts', [])
        options = dialogue.get('options', [])
        
        for i, part in enumerate(missing_parts, 1):
            message += f"*Parte {i}:* {part}\n"
    
    # Mostrar vocabulario
    if "vocabulary" in challenge:
        message += "\n*📖 Vocabulario nuevo:*\n"
        for vocab in challenge["vocabulary"][:3]:
            message += f"• *{vocab.get('word', '')}*: {vocab.get('meaning', '')}\n"
    
    message += "\n*Instrucciones:* Responde a cada parte del diálogo y ejercicios."
    
    await query.edit_message_text(
        message,
        parse_mode='Markdown',
        reply_markup=self.keyboards.get_main_menu()
    )
    
    # Guardar desafío para seguimiento
    self.user_conversations[chat_id] = {
        "type": "daily_challenge",
        "challenge": challenge,
        "current_question": 0,
        "score": 0
    }

async def _handle_vocabulary_exercise_response(self, update: Update, conversation: Dict[str, Any], user_message: str):
    """Maneja respuestas a ejercicios de vocabulario"""
    chat_id = update.effective_chat.id
    
    if conversation.get("type") != "vocabulary_exercise":
        return
    
    exercise_type = conversation.get("exercise_type")
    
    if exercise_type == "matching":
        await self._check_matching_exercise(update, conversation, user_message)
    elif exercise_type == "fill_blank":
        # Las respuestas de fill_blank vienen por callback, no por texto
        pass

async def _handle_correction_response(self, update: Update, conversation: Dict[str, Any], user_message: str):
    """Maneja texto para corrección"""
    chat_id = update.effective_chat.id
    
    await update.message.reply_chat_action("typing")
    
    # Obtener perfil del usuario
    profile = await user_service.get_user_profile(chat_id)
    
    # Corregir texto usando Groq AI
    correction = await groq_client.correct_english_text(user_message, profile.level.value)
    
    if "error" in correction:
        await update.message.reply_text(
            "❌ No pude analizar tu texto en este momento.\n"
            "Por favor, inténtalo de nuevo más tarde.",
            parse_mode='Markdown'
        )
        return
    
    # Formatear respuesta de corrección
    response = self._format_correction_response(correction)
    
    await update.message.reply_text(
        response,
        parse_mode='Markdown',
        reply_markup=self.keyboards.get_main_menu()
    )
    
    # Limpiar estado de conversación
    if chat_id in self.user_conversations:
        del self.user_conversations[chat_id]

def _format_correction_response(self, correction: Dict[str, Any]) -> str:
    """Formatea la respuesta de corrección"""
    message = "📝 *Corrección de Texto*\n\n"
    
    message += f"*Original:* {correction.get('original', '')}\n\n"
    message += f"*Corregido:* {correction.get('corrected', '')}\n\n"
    
    if "score" in correction:
        score = correction["score"]
        message += f"*Puntuación:* {score}/100\n"
        
        if score >= 80:
            message += "🎉 *¡Excelente trabajo!*\n"
        elif score >= 60:
            message += "👍 *¡Buen esfuerzo!*\n"
        else:
            message += "💪 *¡Sigue practicando!*\n"
    
    if "grammar_errors" in correction and correction["grammar_errors"]:
        message += "\n*✏️ Errores gramaticales encontrados:*\n"
        for error in correction["grammar_errors"][:3]:  # Mostrar máximo 3
            message += f"• {error}\n"
    
    if "vocabulary_suggestions" in correction and correction["vocabulary_suggestions"]:
        message += "\n*💡 Sugerencias de vocabulario:*\n"
        for word in correction["vocabulary_suggestions"]:
            message += f"• {word}\n"
    
    if "feedback" in correction:
        message += f"\n*📌 Retroalimentación:*\n{correction['feedback']}\n"
    
    return message

async def _check_matching_exercise(self, update: Update, conversation: Dict[str, Any], user_message: str):
    """Verifica ejercicio de emparejamiento"""
    chat_id = update.effective_chat.id
    
    # Obtener pares correctos del ejercicio
    exercise = conversation.get("current_exercise_data", {})
    correct_pairs = exercise.get("pairs", [])
    
    # Parsear respuesta del usuario
    user_pairs = []
    for pair in user_message.split(','):
        pair = pair.strip()
        if '-' in pair:
            eng, esp = pair.split('-', 1)
            user_pairs.append({
                "english": eng.strip(),
                "spanish": esp.strip()
            })
    
    # Verificar respuestas
    correct_count = 0
    total_pairs = len(correct_pairs)
    
    feedback = "*Resultados del ejercicio:*\n\n"
    
    for i, correct_pair in enumerate(correct_pairs, 1):
        user_pair = user_pairs[i-1] if i-1 < len(user_pairs) else None
        
        if user_pair and user_pair["english"].lower() == correct_pair["english"].lower() and \
           user_pair["spanish"].lower() == correct_pair["spanish"].lower():
            correct_count += 1
            feedback += f"✅ *Pareja {i}:* Correcta\n"
        else:
            feedback += f"❌ *Pareja {i}:* Debería ser: {correct_pair['english']} - {correct_pair['spanish']}\n"
            if user_pair:
                feedback += f"   Tu respuesta: {user_pair['english']} - {user_pair['spanish']}\n"
    
    score = int((correct_count / total_pairs) * 100) if total_pairs > 0 else 0
    
    feedback += f"\n*Puntuación:* {score}% ({correct_count}/{total_pairs} correctas)\n"
    
    if score == 100:
        feedback += "🎉 *¡Perfecto! ¡Excelente trabajo!*\n"
    elif score >= 70:
        feedback += "👍 *¡Buen trabajo! Sigue practicando.*\n"
    else:
        feedback += "💪 *¡Sigue intentándolo! La práctica hace al maestro.*\n"
    
    await update.message.reply_text(
        feedback,
        parse_mode='Markdown',
        reply_markup=self.keyboards.get_main_menu()
    )
    
    # Actualizar progreso si es necesario
    if score >= 70:
        await user_service.add_vocabulary_seen(chat_id, [pair["english"] for pair in correct_pairs])
    
    # Limpiar estado de conversación
    if chat_id in self.user_conversations:
        del self.user_conversations[chat_id]

async def _handle_quiz_answer(self, update: Update, callback_data: str):
    """Maneja respuestas de quiz"""
    query = update.callback_query
    chat_id = update.effective_chat.id
    
    # Extraer datos del callback
    parts = callback_data.split('_')
    if len(parts) < 3:
        await query.answer("Error en la respuesta")
        return
    
    question_id = parts[1]
    selected_option = int(parts[2])
    
    # Aquí deberías tener lógica para verificar la respuesta correcta
    # Por ahora, solo damos feedback genérico
    
    await query.answer("Respuesta recibida ✓")
    
    await query.edit_message_text(
        "✅ *Respuesta recibida*\n\n"
        "¡Gracias por participar en el ejercicio!\n"
        "Tu progreso ha sido registrado.\n\n"
        "¿Quieres practicar más? Usa el menú de opciones.",
        parse_mode='Markdown',
        reply_markup=self.keyboards.get_main_menu()
    )

async def _handle_yes_no_response(self, update: Update, callback_data: str):
    """Maneja respuestas Sí/No"""
    query = update.callback_query
    
    if callback_data == "yes":
        response = "✅ *¡Excelente! Continuemos practicando.*"
    else:
        response = "👌 *Entendido. Puedes seleccionar otra opción del menú.*"
    
    await query.edit_message_text(
        response,
        parse_mode='Markdown',
        reply_markup=self.keyboards.get_main_menu()
    )

async def _return_to_main_menu(self, update: Update):
    """Regresa al menú principal"""
    query = update.callback_query
    
    await query.edit_message_text(
        "🏠 *Menú Principal*\n\n"
        "Selecciona una opción del menú inferior:",
        parse_mode='Markdown',
        reply_markup=self.keyboards.get_main_menu()
    )

async def _offer_vocabulary_after_level(self, update: Update):
    """Ofrece vocabulario después de cambiar nivel"""
    query = update.callback_query
    
    # Añadir botón para ir directamente a vocabulario
    keyboard = [
        [
            InlineKeyboardButton("📚 Aprender Vocabulario", callback_data="vocab_daily"),
            InlineKeyboardButton("💬 Practicar", callback_data="practice_conversation")
        ],
        [InlineKeyboardButton("🔙 Menú Principal", callback_data="main_menu")]
    ]
    
    await query.message.reply_text(
        "🎯 *¿Qué te gustaría hacer ahora?*\n\n"
        "Puedes empezar con vocabulario de tu nuevo nivel o practicar conversación.",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def _start_level_test(self, update: Update):
    """Inicia test de nivel de inglés"""
    query = update.callback_query
    
    await query.edit_message_text(
        "📝 *Test de Nivel de Inglés*\n\n"
        "Esta funcionalidad estará disponible en la próxima actualización.\n\n"
        "Por ahora, puedes seleccionar tu nivel manualmente:\n"
        "• 🟢 Básico: Si estás empezando\n"
        "• 🟡 Intermedio: Si puedes mantener conversaciones simples\n"
        "• 🔴 Avanzado: Si te expresas con fluidez\n\n"
        "No te preocupes, puedes cambiar tu nivel en cualquier momento.",
        parse_mode='Markdown',
        reply_markup=self.keyboards.get_level_selector()
    )