# Vocabulario

import asyncio
import random
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from ..database.models import VocabularyItem, EnglishLevel
from ..database.sheets_client import sheets_client
from ..ai.groq_client import groq_client
import logging

logger = logging.getLogger(__name__)

class VocabularyService:
    """Servicio avanzado de gestión de vocabulario"""
    
    def __init__(self):
        self._spaced_repetition_cache = {}
    
    async def get_category_vocabulary(self, category: str, 
                                    user_level: Optional[EnglishLevel] = None,
                                    limit: int = 15) -> List[VocabularyItem]:
        """Obtiene vocabulario de categoría con algoritmo de selección inteligente"""
        
        # Obtener todo el vocabulario de la categoría
        all_vocab = await sheets_client.get_vocabulary_by_category(category, None, 100)
        
        if not all_vocab:
            logger.warning(f"No se encontró vocabulario para categoría: {category}")
            return await self._generate_vocabulary(category, user_level, limit)
        
        # Filtrar por nivel si se especifica
        if user_level:
            filtered_vocab = [v for v in all_vocab if v.complexity == user_level]
            
            # Si no hay suficiente vocabulario del nivel específico, mezclar
            if len(filtered_vocab) < limit:
                other_vocab = [v for v in all_vocab if v.complexity != user_level]
                
                # Ordenar otros niveles por cercanía al nivel del usuario
                level_order = {"basic": 0, "intermediate": 1, "advanced": 2}
                user_level_num = level_order.get(user_level.value, 1)
                
                other_vocab.sort(key=lambda x: abs(level_order.get(x.complexity.value, 1) - user_level_num))
                
                # Mezclar vocabulario
                filtered_vocab.extend(other_vocab[:limit - len(filtered_vocab)])
        else:
            filtered_vocab = all_vocab
        
        # Aplicar algoritmo de selección inteligente
        selected_vocab = self._intelligent_selection(filtered_vocab, limit)
        
        return selected_vocab
    
    def _intelligent_selection(self, vocabulary: List[VocabularyItem], 
                             limit: int) -> List[VocabularyItem]:
        """Selección inteligente de vocabulario usando múltiples criterios"""
        
        if len(vocabulary) <= limit:
            return vocabulary
        
        # Ponderación de criterios
        selected = []
        
        # 1. Diversidad de complejidad (30%)
        complexity_groups = {}
        for word in vocabulary:
            comp = word.complexity.value
            if comp not in complexity_groups:
                complexity_groups[comp] = []
            complexity_groups[comp].append(word)
        
        # Distribuir según complejidad
        for comp in ["basic", "intermediate", "advanced"]:
            if comp in complexity_groups:
                group_words = complexity_groups[comp]
                num_to_select = max(1, int(limit * 0.3))
                selected.extend(random.sample(group_words, min(num_to_select, len(group_words))))
        
        # 2. Diversidad temática (30%)
        # Agrupar por tema implícito en la palabra
        thematic_groups = {}
        for word in vocabulary:
            theme = self._extract_theme(word.english_word)
            if theme not in thematic_groups:
                thematic_groups[theme] = []
            thematic_groups[theme].append(word)
        
        for theme, group_words in list(thematic_groups.items())[:5]:  # Top 5 temas
            if group_words:
                num_to_select = max(1, int(limit * 0.3 / len(thematic_groups)))
                selected.extend(random.sample(group_words, min(num_to_select, len(group_words))))
        
        # 3. Utilidad práctica (20%)
        practical_words = [w for w in vocabulary if self._is_practical_word(w.english_word)]
        if practical_words:
            num_to_select = max(1, int(limit * 0.2))
            selected.extend(random.sample(practical_words, min(num_to_select, len(practical_words))))
        
        # 4. Novedad/Interés (20%)
        interesting_words = [w for w in vocabulary if self._is_interesting_word(w.english_word)]
        if interesting_words:
            num_to_select = max(1, int(limit * 0.2))
            selected.extend(random.sample(interesting_words, min(num_to_select, len(interesting_words))))
        
        # Eliminar duplicados y limitar
        unique_selected = []
        seen_ids = set()
        for word in selected:
            if word.id not in seen_ids:
                seen_ids.add(word.id)
                unique_selected.append(word)
        
        # Si no alcanzamos el límite, añadir aleatorios
        if len(unique_selected) < limit:
            remaining = [w for w in vocabulary if w.id not in seen_ids]
            needed = limit - len(unique_selected)
            if remaining:
                unique_selected.extend(random.sample(remaining, min(needed, len(remaining))))
        
        return unique_selected[:limit]
    
    def _extract_theme(self, word: str) -> str:
        """Extrae tema de una palabra"""
        word_lower = word.lower()
        
        themes = {
            "time": ["time", "hour", "minute", "second", "day", "week", "month", "year"],
            "family": ["mother", "father", "brother", "sister", "family", "parent", "child"],
            "work": ["work", "job", "office", "boss", "employee", "meeting", "project"],
            "food": ["food", "eat", "drink", "water", "coffee", "tea", "meal", "restaurant"],
            "home": ["house", "home", "room", "bed", "kitchen", "bathroom", "garden"],
            "school": ["school", "student", "teacher", "class", "lesson", "homework", "exam"],
            "health": ["health", "doctor", "hospital", "medicine", "sick", "healthy", "exercise"],
            "money": ["money", "bank", "pay", "price", "cost", "buy", "sell", "market"],
            "travel": ["travel", "trip", "airport", "hotel", "passport", "ticket", "destination"],
            "technology": ["computer", "phone", "internet", "email", "software", "data", "digital"]
        }
        
        for theme, keywords in themes.items():
            for keyword in keywords:
                if keyword in word_lower:
                    return theme
        
        return "general"
    
    def _is_practical_word(self, word: str) -> bool:
        """Determina si una palabra es de uso práctico común"""
        practical_words = {
            "hello", "goodbye", "please", "thank", "sorry", "excuse", 
            "help", "need", "want", "have", "do", "make", "take", "give",
            "go", "come", "see", "look", "hear", "say", "tell", "ask",
            "eat", "drink", "sleep", "work", "study", "learn", "teach",
            "buy", "sell", "pay", "cost", "price", "money", "time", "day"
        }
        
        return any(practical in word.lower() for practical in practical_words)
    
    def _is_interesting_word(self, word: str) -> bool:
        """Determina si una palabra es interesante o poco común"""
        common_words = {
            "the", "be", "to", "of", "and", "a", "in", "that", "have", "i",
            "it", "for", "not", "on", "with", "he", "as", "you", "do", "at"
        }
        
        word_lower = word.lower()
        
        # Palabras largas tienden a ser más interesantes
        if len(word) > 8:
            return True
        
        # Palabras con prefijos/sufijos interesantes
        interesting_patterns = ["anti", "auto", "bio", "geo", "hyper", "inter", "macro", 
                               "micro", "multi", "neo", "omni", "poly", "tele", "trans"]
        
        if any(pattern in word_lower for pattern in interesting_patterns):
            return True
        
        # No es una palabra común
        return word_lower not in common_words
    
    async def _generate_vocabulary(self, category: str, 
                                 user_level: Optional[EnglishLevel],
                                 limit: int) -> List[VocabularyItem]:
        """Genera vocabulario dinámicamente usando IA"""
        
        logger.info(f"Generando vocabulario para categoría: {category}")
        
        prompt = f"""
        Genera una lista de {limit} palabras de vocabulario en inglés sobre {category}.
        Nivel de dificultad: {user_level.value if user_level else 'mixed'}.
        
        Para cada palabra, proporciona:
        1. Palabra en inglés
        2. Traducción al español
        3. Ejemplo de uso en una oración
        4. Nivel de complejidad (basic/intermediate/advanced)
        5. Pronunciación fonética opcional
        
        Formato JSON:
        {{
            "vocabulary": [
                {{
                    "id": "unique_id_1",
                    "english_word": "word",
                    "spanish_translation": "traducción",
                    "example_sentence": "This is an example sentence.",
                    "complexity": "basic",
                    "pronunciation": "/prəˌnʌn.siˈeɪ.ʃən/",
                    "category": "{category}"
                }}
            ]
        }}
        """
        
        try:
            response = await groq_client.generate_response(prompt)
            import json
            data = json.loads(response)
            
            vocabulary_items = []
            for i, item_data in enumerate(data.get("vocabulary", [])):
                vocab_item = VocabularyItem(
                    id=f"gen_{category}_{i}_{datetime.now().timestamp()}",
                    category=category,
                    english_word=item_data.get("english_word", ""),
                    spanish_translation=item_data.get("spanish_translation", ""),
                    example_sentence=item_data.get("example_sentence", ""),
                    complexity=EnglishLevel(item_data.get("complexity", "basic")),
                    pronunciation=item_data.get("pronunciation")
                )
                vocabulary_items.append(vocab_item)
            
            return vocabulary_items
            
        except Exception as e:
            logger.error(f"Error generando vocabulario: {str(e)}")
            return self._get_fallback_vocabulary(category, user_level, limit)
    
    def _get_fallback_vocabulary(self, category: str, 
                               user_level: Optional[EnglishLevel],
                               limit: int) -> List[VocabularyItem]:
        """Vocabulario de respaldo cuando no hay conexión"""
        
        fallback_vocab = {
            "daily_life": [
                VocabularyItem(
                    id="fallback_1",
                    category=category,
                    english_word="hello",
                    spanish_translation="hola",
                    example_sentence="Hello, how are you?",
                    complexity=EnglishLevel.BASIC,
                    pronunciation="/həˈloʊ/"
                ),
                VocabularyItem(
                    id="fallback_2",
                    category=category,
                    english_word="thank you",
                    spanish_translation="gracias",
                    example_sentence="Thank you for your help.",
                    complexity=EnglishLevel.BASIC,
                    pronunciation="/ˈθæŋk juː/"
                )
            ],
            "work": [
                VocabularyItem(
                    id="fallback_3",
                    category=category,
                    english_word="meeting",
                    spanish_translation="reunión",
                    example_sentence="We have a meeting at 3 PM.",
                    complexity=EnglishLevel.INTERMEDIATE,
                    pronunciation="/ˈmiːtɪŋ/"
                )
            ],
            "education": [
                VocabularyItem(
                    id="fallback_4",
                    category=category,
                    english_word="student",
                    spanish_translation="estudiante",
                    example_sentence="The student is studying English.",
                    complexity=EnglishLevel.BASIC,
                    pronunciation="/ˈstuːdənt/"
                )
            ]
        }
        
        vocab_list = fallback_vocab.get(category, fallback_vocab["daily_life"])
        
        # Filtrar por nivel si se especifica
        if user_level:
            vocab_list = [v for v in vocab_list if v.complexity == user_level]
        
        return vocab_list[:limit]
    
    async def create_vocabulary_lesson(self, vocabulary: List[VocabularyItem], 
                                     user_level: EnglishLevel) -> Dict[str, Any]:
        """Crea una lección estructurada a partir del vocabulario"""
        
        if not vocabulary:
            return {"error": "No hay vocabulario disponible"}
        
        # Organizar vocabulario por grupos temáticos
        thematic_groups = {}
        for word in vocabulary:
            theme = self._extract_theme(word.english_word)
            if theme not in thematic_groups:
                thematic_groups[theme] = []
            thematic_groups[theme].append(word)
        
        # Crear ejercicios basados en el nivel
        exercises = []
        
        if user_level == EnglishLevel.BASIC:
            exercises = self._create_basic_exercises(vocabulary)
        elif user_level == EnglishLevel.INTERMEDIATE:
            exercises = self._create_intermediate_exercises(vocabulary)
        else:  # Advanced
            exercises = self._create_advanced_exercises(vocabulary)
        
        lesson = {
            "title": f"Vocabulario: {vocabulary[0].category if vocabulary else 'General'}",
            "description": f"Lección de {len(vocabulary)} palabras para nivel {user_level.value}",
            "vocabulary": [word.dict() for word in vocabulary],
            "thematic_groups": [
                {
                    "theme": theme,
                    "words": [w.english_word for w in words[:3]],
                    "count": len(words)
                }
                for theme, words in list(thematic_groups.items())[:3]
            ],
            "exercises": exercises,
            "estimated_time": f"{len(vocabulary) * 2} minutos",
            "learning_objectives": [
                "Memorizar palabras clave",
                "Usar palabras en contexto",
                "Practicar pronunciación",
                "Aplicar en conversaciones"
            ]
        }
        
        return lesson
    
    def _create_basic_exercises(self, vocabulary: List[VocabularyItem]) -> List[Dict[str, Any]]:
        """Crea ejercicios para nivel básico"""
        exercises = []
        
        # Ejercicio 1: Emparejamiento simple
        if len(vocabulary) >= 4:
            exercises.append({
                "type": "matching",
                "title": "Empareja las palabras",
                "instructions": "Empareja cada palabra en inglés con su traducción en español",
                "pairs": [
                    {
                        "english": word.english_word,
                        "spanish": word.spanish_translation
                    }
                    for word in vocabulary[:4]
                ],
                "shuffle": True
            })
        
        # Ejercicio 2: Completar oraciones
        if len(vocabulary) >= 3:
            exercises.append({
                "type": "fill_blank",
                "title": "Completa las oraciones",
                "instructions": "Completa cada oración con la palabra correcta",
                "sentences": [
                    {
                        "sentence": word.example_sentence.replace(word.english_word, "_____"),
                        "correct_word": word.english_word,
                        "options": [
                            word.english_word,
                            random.choice([w.english_word for w in vocabulary if w != word]),
                            "different word"
                        ]
                    }
                    for word in vocabulary[:3]
                ]
            })
        
        return exercises
    
    def _create_intermediate_exercises(self, vocabulary: List[VocabularyItem]) -> List[Dict[str, Any]]:
        """Crea ejercicios para nivel intermedio"""
        exercises = self._create_basic_exercises(vocabulary)
        
        # Ejercicio adicional: Crear oraciones
        if len(vocabulary) >= 5:
            exercises.append({
                "type": "sentence_creation",
                "title": "Crea oraciones",
                "instructions": "Crea una oración original usando cada palabra",
                "words": [word.english_word for word in vocabulary[:5]]
            })
        
        # Ejercicio adicional: Sinónimos
        if len(vocabulary) >= 4:
            exercises.append({
                "type": "synonyms",
                "title": "Encuentra sinónimos",
                "instructions": "Para cada palabra, encuentra un sinónimo apropiado",
                "words": [word.english_word for word in vocabulary[:4]]
            })
        
        return exercises
    
    def _create_advanced_exercises(self, vocabulary: List[VocabularyItem]) -> List[Dict[str, Any]]:
        """Crea ejercicios para nivel avanzado"""
        exercises = self._create_intermediate_exercises(vocabulary)
        
        # Ejercicio adicional: Debate/Opinión
        if len(vocabulary) >= 3:
            topic = vocabulary[0].category
            exercises.append({
                "type": "debate",
                "title": "Expresa tu opinión",
                "instructions": f"Escribe un párrafo breve sobre '{topic}' usando al menos 3 palabras del vocabulario",
                "required_words": [word.english_word for word in vocabulary[:3]],
                "word_count": "50-100 palabras"
            })
        
        # Ejercicio adicional: Traducción inversa
        if len(vocabulary) >= 4:
            exercises.append({
                "type": "reverse_translation",
                "title": "Traducción al inglés",
                "instructions": "Traduce estas oraciones al inglés usando las palabras aprendidas",
                "sentences": [
                    {
                        "spanish": f"Ejemplo en español usando {word.spanish_translation}",
                        "hint": word.english_word
                    }
                    for word in vocabulary[:4]
                ]
            })
        
        return exercises
    
    async def get_spaced_repetition_words(self, chat_id: int, 
                                        count: int = 10) -> List[VocabularyItem]:
        """Obtiene palabras para repaso espaciado basado en algoritmo SM-2"""
        
        # TODO: Implementar algoritmo de repetición espaciada SM-2
        # Por ahora, devolver palabras aleatorias
        
        categories = await sheets_client.get_categories()
        if not categories:
            categories = ["daily_life", "work", "education"]
        
        selected_category = random.choice(categories)
        vocabulary = await self.get_category_vocabulary(selected_category, None, count)
        
        return vocabulary
    
    async def test_vocabulary_knowledge(self, chat_id: int, 
                                      words: List[VocabularyItem]) -> Dict[str, Any]:
        """Evalúa conocimiento del vocabulario"""
        
        test = {
            "total_questions": len(words),
            "questions": [],
            "start_time": datetime.now().isoformat()
        }
        
        for i, word in enumerate(words):
            question_types = ["translation", "usage", "synonym"]
            question_type = random.choice(question_types)
            
            if question_type == "translation":
                test["questions"].append({
                    "type": "translation",
                    "question": f"¿Cuál es la traducción de '{word.english_word}'?",
                    "correct_answer": word.spanish_translation,
                    "options": self._generate_translation_options(word, words)
                })
            elif question_type == "usage":
                test["questions"].append({
                    "type": "usage",
                    "question": f"Completa la oración: {word.example_sentence.replace(word.english_word, '_____')}",
                    "correct_answer": word.english_word,
                    "options": self._generate_usage_options(word, words)
                })
            else:  # synonym
                test["questions"].append({
                    "type": "synonym",
                    "question": f"¿Cuál es un sinónimo de '{word.english_word}'?",
                    "correct_answer": "unknown",  # Sería determinado por IA
                    "options": ["option1", "option2", "option3", "option4"]
                })
        
        return test
    
    def _generate_translation_options(self, correct_word: VocabularyItem, 
                                    all_words: List[VocabularyItem]) -> List[str]:
        """Genera opciones para preguntas de traducción"""
        options = [correct_word.spanish_translation]
        
        # Añadir traducciones de otras palabras
        other_words = [w for w in all_words if w != correct_word]
        if len(other_words) >= 3:
            options.extend([w.spanish_translation for w in random.sample(other_words, 3)])
        else:
            # Añadir opciones genéricas si no hay suficientes palabras
            generic_options = ["casa", "perro", "libro", "computador"]
            options.extend(random.sample(generic_options, 3))
        
        random.shuffle(options)
        return options
    
    def _generate_usage_options(self, correct_word: VocabularyItem, 
                              all_words: List[VocabularyItem]) -> List[str]:
        """Genera opciones para preguntas de uso"""
        options = [correct_word.english_word]
        
        other_words = [w for w in all_words if w != correct_word]
        if len(other_words) >= 3:
            options.extend([w.english_word for w in random.sample(other_words, 3)])
        else:
            generic_options = ["house", "dog", "book", "computer"]
            options.extend(random.sample(generic_options, 3))
        
        random.shuffle(options)
        return options

# Instancia global
vocab_service = VocabularyService()