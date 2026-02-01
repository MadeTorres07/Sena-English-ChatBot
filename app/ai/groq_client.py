# Cliente Groq AI

import asyncio
import json
from typing import List, Dict, Any, Optional
from groq import Groq
from ..config import settings

class GroqAIClient:
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model = settings.GROQ_MODEL
        
    async def generate_response(
        self, 
        prompt: str, 
        system_message: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        """Genera respuesta usando Groq AI"""
        
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})
        
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False
            )
            return completion.choices[0].message.content
        except Exception as e:
            return f"Error al generar respuesta: {str(e)}"
    
    async def correct_english_text(self, text: str, user_level: str) -> Dict[str, Any]:
        """Corrige texto en inglés y da sugerencias"""
        
        prompt = f"""
        Analiza este texto en inglés de un estudiante de nivel {user_level}:
        
        Texto del estudiante: "{text}"
        
        Por favor, analiza:
        1. Correcciones gramaticales necesarias
        2. Sugerencias de vocabulario más apropiado (3 palabras)
        3. Puntuación y estilo
        4. Da una versión corregida completa
        
        Responde en formato JSON:
        {{
            "original": "texto original",
            "corrected": "texto corregido",
            "grammar_errors": ["error1", "error2"],
            "vocabulary_suggestions": ["palabra1", "palabra2", "palabra3"],
            "score": 0-100,
            "feedback": "retroalimentación constructiva"
        }}
        """
        
        response = await self.generate_response(prompt)
        try:
            return json.loads(response)
        except:
            return {"error": "No se pudo analizar la respuesta"}
    
    async def generate_vocabulary_lesson(
        self, 
        category: str, 
        level: str, 
        word_count: int = 10
    ) -> Dict[str, Any]:
        """Genera lección de vocabulario personalizada"""
        
        prompt = f"""
        Genera una lección de vocabulario en inglés para nivel {level}.
        Categoría: {category}
        Número de palabras: {word_count}
        
        Para cada palabra, incluye:
        1. Palabra en inglés
        2. Traducción al español
        3. Pronunciación fonética
        4. Ejemplo de uso en oración
        5. Sinónimos (2-3)
        
        Formato de respuesta JSON:
        {{
            "category": "{category}",
            "level": "{level}",
            "words": [
                {{
                    "english": "word",
                    "spanish": "traducción",
                    "pronunciation": "/prəˌnʌn.siˈeɪ.ʃən/",
                    "example": "example sentence",
                    "synonyms": ["syn1", "syn2"]
                }}
            ],
            "practice_exercises": [
                {{
                    "type": "multiple_choice",
                    "question": "question text",
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": "A"
                }}
            ]
        }}
        """
        
        response = await self.generate_response(prompt)
        try:
            return json.loads(response)
        except:
            return {"error": "No se pudo generar la lección"}

groq_client = GroqAIClient()