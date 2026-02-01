# Lecciones

# app/services/lesson_service.py

import asyncio
import random
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from ..database.models import EnglishLevel
from ..database.sheets_client import sheets_client
from ..ai.groq_client import groq_client
import logging

logger = logging.getLogger(__name__)

class LessonService:
    """Servicio avanzado de gestión de lecciones"""
    
    def __init__(self):
        self._lesson_cache = {}
        self._cache_expiry = {}
        self.CACHE_DURATION = timedelta(hours=1)
    
    async def generate_lesson(self, topic: str, level: EnglishLevel, 
                            duration_minutes: int = 15) -> Dict[str, Any]:
        """Genera una lección personalizada sobre un tema específico"""
        
        cache_key = f"lesson_{topic}_{level.value}_{duration_minutes}"
        
        if cache_key in self._lesson_cache and self._is_cache_valid(cache_key):
            return self._lesson_cache[cache_key]
        
        prompt = f"""
        Genera una lección de inglés sobre '{topic}' para nivel {level.value}.
        Duración: {duration_minutes} minutos.
        
        La lección debe incluir:
        1. Objetivos de aprendizaje claros (3-4 objetivos)
        2. Introducción al tema
        3. Contenido principal dividido en secciones
        4. Ejemplos prácticos
        5. Ejercicios de práctica (2-3 ejercicios)
        6. Resumen y conclusiones
        7. Recursos adicionales para profundizar
        
        Formato la respuesta en JSON:
        {{
            "title": "Título atractivo de la lección",
            "topic": "{topic}",
            "level": "{level.value}",
            "duration_minutes": {duration_minutes},
            "learning_objectives": ["obj1", "obj2", "obj3"],
            "introduction": "Texto de introducción",
            "sections": [
                {{
                    "title": "Título sección",
                    "content": "Contenido detallado",
                    "examples": ["ejemplo1", "ejemplo2"]
                }}
            ],
            "exercises": [
                {{
                    "type": "multiple_choice|fill_blank|matching|conversation",
                    "title": "Título ejercicio",
                    "instructions": "Instrucciones claras",
                    "content": {{ ... }}  # Depende del tipo
                }}
            ],
            "summary": "Resumen de la lección",
            "additional_resources": ["recurso1", "recurso2"]
        }}
        """
        
        try:
            response = await groq_client.generate_response(
                prompt=prompt,
                temperature=0.7,
                max_tokens=2000
            )
            
            import json
            lesson = json.loads(response)
            
            # Validar y completar campos
            lesson = self._validate_lesson(lesson, topic, level, duration_minutes)
            
            # Actualizar cache
            self._lesson_cache[cache_key] = lesson
            self._cache_expiry[cache_key] = datetime.now() + self.CACHE_DURATION
            
            return lesson
            
        except Exception as e:
            logger.error(f"Error generating lesson: {str(e)}")
            return self._get_default_lesson(topic, level, duration_minutes)
    
    def _validate_lesson(self, lesson: Dict[str, Any], topic: str, 
                        level: EnglishLevel, duration: int) -> Dict[str, Any]:
        """Valida y completa los campos de una lección generada"""
        
        # Campos obligatorios
        if "title" not in lesson:
            lesson["title"] = f"Lección sobre {topic}"
        
        if "topic" not in lesson:
            lesson["topic"] = topic
        
        if "level" not in lesson:
            lesson["level"] = level.value
        
        if "duration_minutes" not in lesson:
            lesson["duration_minutes"] = duration
        
        # Asegurar arrays
        if "learning_objectives" not in lesson:
            lesson["learning_objectives"] = [
                f"Entender conceptos básicos sobre {topic}",
                "Aplicar vocabulario relacionado",
                "Practicar en contexto"
            ]
        
        if "sections" not in lesson:
            lesson["sections"] = [
                {
                    "title": "Introducción",
                    "content": f"En esta lección aprenderás sobre {topic}.",
                    "examples": []
                }
            ]
        
        if "exercises" not in lesson:
            lesson["exercises"] = self._generate_default_exercises(topic, level)
        
        if "summary" not in lesson:
            lesson["summary"] = f"En esta lección hemos cubierto conceptos básicos sobre {topic}."
        
        if "additional_resources" not in lesson:
            lesson["additional_resources"] = []
        
        return lesson
    
    def _generate_default_exercises(self, topic: str, level: EnglishLevel) -> List[Dict[str, Any]]:
        """Genera ejercicios por defecto"""
        
        exercises = []
        
        # Ejercicio 1: Multiple choice
        exercises.append({
            "type": "multiple_choice",
            "title": f"Comprensión sobre {topic}",
            "instructions": "Selecciona la opción correcta:",
            "content": {
                "question": f"What is the main topic of this lesson about {topic}?",
                "options": [
                    f"Advanced concepts of {topic}",
                    f"Basic understanding of {topic}",
                    f"History of {topic}",
                    f"Technical details of {topic}"
                ],
                "correct_answer": 1,
                "explanation": f"This lesson covers basic concepts about {topic}."
            }
        })
        
        # Ejercicio 2: Fill in the blank
        if level != EnglishLevel.BASIC:
            exercises.append({
                "type": "fill_blank",
                "title": "Completa las oraciones",
                "instructions": "Completa las oraciones con las palabras correctas:",
                "content": {
                    "sentences": [
                        {
                            "sentence": f"{topic.capitalize()} is important because _____.",
                            "correct_word": "it",
                            "hint": "Pronombre"
                        }
                    ]
                }
            })
        
        return exercises
    
    def _get_default_lesson(self, topic: str, level: EnglishLevel, 
                          duration: int) -> Dict[str, Any]:
        """Lección por defecto en caso de error"""
        
        return {
            "title": f"Introducción a {topic}",
            "topic": topic,
            "level": level.value,
            "duration_minutes": duration,
            "learning_objectives": [
                f"Comprender conceptos básicos de {topic}",
                "Aprender vocabulario relacionado",
                "Practicar en contextos reales"
            ],
            "introduction": f"Esta lección te introducirá al tema de {topic}.",
            "sections": [
                {
                    "title": "¿Qué es?",
                    "content": f"{topic.capitalize()} es un tema importante para el aprendizaje del inglés.",
                    "examples": [
                        f"Example 1 related to {topic}",
                        f"Example 2 about {topic}"
                    ]
                },
                {
                    "title": "Aplicación práctica",
                    "content": f"Puedes usar lo aprendido sobre {topic} en situaciones diarias.",
                    "examples": [
                        f"Practical use case 1 for {topic}",
                        f"Practical use case 2 for {topic}"
                    ]
                }
            ],
            "exercises": self._generate_default_exercises(topic, level),
            "summary": f"Hemos cubierto los conceptos básicos de {topic}. Continúa practicando.",
            "additional_resources": []
        }
    
    async def get_recommended_topics(self, level: EnglishLevel) -> List[str]:
        """Obtiene temas recomendados según el nivel"""
        
        topics_by_level = {
            "basic": [
                "Greetings and Introductions",
                "Daily Routine",
                "Family and Friends",
                "Food and Drinks",
                "Shopping Basics",
                "Travel Essentials",
                "Weather and Seasons",
                "Hobbies and Interests",
                "Home and Furniture",
                "Numbers and Time"
            ],
            "intermediate": [
                "Work and Professions",
                "Education and Studies",
                "Health and Medicine",
                "Technology and Internet",
                "Culture and Traditions",
                "Environment and Nature",
                "Business Communication",
                "Travel Experiences",
                "Entertainment and Media",
                "Social Issues"
            ],
            "advanced": [
                "Professional Development",
                "Academic Writing",
                "Business Negotiations",
                "Scientific Topics",
                "Political Discussions",
                "Economic Concepts",
                "Legal Terminology",
                "Medical English",
                "Technical Documentation",
                "Creative Writing"
            ]
        }
        
        return topics_by_level.get(level.value, topics_by_level["basic"])
    
    async def create_progress_lesson(self, user_level: EnglishLevel, 
                                   weak_areas: List[str]) -> Dict[str, Any]:
        """Crea una lección enfocada en áreas débiles del usuario"""
        
        if not weak_areas:
            weak_areas = ["grammar", "vocabulary", "pronunciation"]
        
        focus_area = random.choice(weak_areas)
        
        prompt = f"""
        Crea una lección de inglés de refuerzo para nivel {user_level.value}.
        Enfócate en mejorar: {focus_area}
        
        La lección debe incluir:
        1. Diagnóstico del problema común
        2. Explicación clara de conceptos
        3. Ejercicios específicos para superar el problema
        4. Consejos prácticos
        5. Seguimiento recomendado
        
        Formato JSON:
        {{
            "type": "remedial_lesson",
            "focus_area": "{focus_area}",
            "title": "Título apropiado",
            "diagnosis": "Descripción del problema común",
            "explanation": "Explicación detallada",
            "exercises": [
                {{
                    "title": "Ejercicio específico",
                    "instructions": "Instrucciones",
                    "content": {{...}}
                }}
            ],
            "tips": ["tip1", "tip2", "tip3"],
            "next_steps": "Qué hacer después"
        }}
        """
        
        try:
            response = await groq_client.generate_response(prompt)
            import json
            lesson = json.loads(response)
            
            # Añadir metadata
            lesson["generated_at"] = datetime.now().isoformat()
            lesson["target_level"] = user_level.value
            
            return lesson
            
        except Exception as e:
            logger.error(f"Error creating progress lesson: {str(e)}")
            return {
                "type": "remedial_lesson",
                "focus_area": focus_area,
                "title": f"Refuerzo en {focus_area}",
                "diagnosis": f"Necesitas practicar más {focus_area}.",
                "explanation": f"Te explicaremos conceptos clave de {focus_area}.",
                "exercises": [],
                "tips": ["Practice daily", "Review regularly", "Ask for feedback"],
                "next_steps": "Continue with regular lessons"
            }
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Verifica si el cache es válido"""
        if cache_key not in self._cache_expiry:
            return False
        return datetime.now() < self._cache_expiry[cache_key]
    
    async def clear_cache(self):
        """Limpia la cache de lecciones"""
        self._lesson_cache.clear()
        self._cache_expiry.clear()
        logger.info("Lesson cache cleared")

# Instancia global
lesson_service = LessonService()