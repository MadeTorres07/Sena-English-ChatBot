# Botones y menús

from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from typing import List, Dict

class Keyboards:
    """Generador de teclados y menús para Telegram"""
    
    @staticmethod
    def get_main_menu() -> ReplyKeyboardMarkup:
        """Menú principal permanente"""
        keyboard = [
            [KeyboardButton("📚 Vocabulario"), KeyboardButton("💬 Practicar")],
            [KeyboardButton("🏫 Info SENA"), KeyboardButton("📊 Mi Progreso")],
            [KeyboardButton("⚙️ Cambiar Nivel"), KeyboardButton("🆘 Ayuda")]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, persistent=True)
    
    @staticmethod
    def get_level_selector() -> InlineKeyboardMarkup:
        """Selector de nivel de inglés"""
        keyboard = [
            [
                InlineKeyboardButton("🟢 Básico", callback_data="level_basic"),
                InlineKeyboardButton("🟡 Intermedio", callback_data="level_intermediate"),
            ],
            [
                InlineKeyboardButton("🔴 Avanzado", callback_data="level_advanced"),
                InlineKeyboardButton("📊 Test de Nivel", callback_data="level_test")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_vocabulary_categories() -> InlineKeyboardMarkup:
        """Categorías de vocabulario"""
        categories = [
            ("🏠 Vida Diaria", "vocab_daily"),
            ("💼 Trabajo", "vocab_work"),
            ("🏫 Educación", "vocab_education"),
            ("🛒 Compras", "vocab_shopping"),
            ("🍔 Comida", "vocab_food"),
            ("🚗 Transporte", "vocab_transport"),
            ("🏥 Salud", "vocab_health"),
            ("🎨 Arte y Cultura", "vocab_art"),
            ("💻 Tecnología", "vocab_tech"),
            ("⚽ Deportes", "vocab_sports")
        ]
        
        # Crear botones en filas de 2
        keyboard = []
        for i in range(0, len(categories), 2):
            row = []
            row.append(InlineKeyboardButton(categories[i][0], callback_data=categories[i][1]))
            if i + 1 < len(categories):
                row.append(InlineKeyboardButton(categories[i+1][0], callback_data=categories[i+1][1]))
            keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton("🔙 Menú Principal", callback_data="main_menu")])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_practice_options() -> InlineKeyboardMarkup:
        """Opciones de práctica"""
        keyboard = [
            [
                InlineKeyboardButton("💬 Conversación", callback_data="practice_conversation"),
                InlineKeyboardButton("📝 Corrección", callback_data="practice_correction")
            ],
            [
                InlineKeyboardButton("🎯 Ejercicios", callback_data="practice_exercises"),
                InlineKeyboardButton("🎤 Pronunciación", callback_data="practice_pronunciation")
            ],
            [
                InlineKeyboardButton("📚 Lección Diaria", callback_data="practice_daily"),
                InlineKeyboardButton("🏆 Desafío", callback_data="practice_challenge")
            ],
            [InlineKeyboardButton("🔙 Menú Principal", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_sena_topics() -> InlineKeyboardMarkup:
        """Temas sobre el SENA"""
        keyboard = [
            [
                InlineKeyboardButton("📖 Qué es el SENA", callback_data="sena_what"),
                InlineKeyboardButton("🎓 Programas", callback_data="sena_programs")
            ],
            [
                InlineKeyboardButton("📍 Sedes", callback_data="sena_locations"),
                InlineKeyboardButton("📅 Eventos", callback_data="sena_events")
            ],
            [
                InlineKeyboardButton("💼 Empleabilidad", callback_data="sena_employment"),
                InlineKeyboardButton("🌐 Página Web", callback_data="sena_website")
            ],
            [InlineKeyboardButton("🔙 Menú Principal", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_yes_no_keyboard() -> InlineKeyboardMarkup:
        """Teclado Sí/No simple"""
        keyboard = [
            [
                InlineKeyboardButton("✅ Sí", callback_data="yes"),
                InlineKeyboardButton("❌ No", callback_data="no")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_quiz_options(options: List[str], question_id: str) -> InlineKeyboardMarkup:
        """Opciones para quiz de múltiple opción"""
        keyboard = []
        letters = ["A", "B", "C", "D", "E"]
        
        for i, option in enumerate(options[:5]):  # Máximo 5 opciones
            keyboard.append([
                InlineKeyboardButton(
                    f"{letters[i]}. {option[:30]}...", 
                    callback_data=f"quiz_{question_id}_{i}"
                )
            ])
        
        return InlineKeyboardMarkup(keyboard)

    # Añadir este método a la clase Keyboards en keyboards.py

@staticmethod
def get_main_menu_inline() -> InlineKeyboardMarkup:
    """Menú principal en formato inline"""
    keyboard = [
        [
            InlineKeyboardButton("📚 Vocabulario", callback_data="vocab_daily"),
            InlineKeyboardButton("💬 Practicar", callback_data="practice_conversation")
        ],
        [
            InlineKeyboardButton("🏫 Info SENA", callback_data="sena_what"),
            InlineKeyboardButton("📊 Progreso", callback_data="show_progress")
        ],
        [
            InlineKeyboardButton("⚙️ Nivel", callback_data="level_select"),
            InlineKeyboardButton("🆘 Ayuda", callback_data="show_help")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)