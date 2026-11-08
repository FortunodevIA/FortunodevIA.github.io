import json
import logging
import os
import re

logger = logging.getLogger(__name__)

LEVEL_INSTRUCTIONS = {
    'easy': (
        'Niveau facile : définitions directes, vocabulaire clé, '
        'questions courtes et accessibles pour un débutant.'
    ),
    'medium': (
        'Niveau moyen : compréhension, mise en relation de concepts, '
        'application simple dans un contexte du cours.'
    ),
    'hard': (
        'Niveau difficile : analyse, comparaison, cas concrets, '
        'pièges raisonnables mais une seule réponse clairement correcte.'
    ),
}


def is_ai_enabled():
    return bool(os.environ.get('ANTHROPIC_API_KEY', '').strip())


def _get_client():
    api_key = os.environ.get('ANTHROPIC_API_KEY', '').strip()
    if not api_key:
        return None
    try:
        from anthropic import Anthropic
        return Anthropic(api_key=api_key)
    except Exception as exc:
        logger.warning('Client Anthropic indisponible: %s', exc)
        return None


def _get_model():
    return os.environ.get('ANTHROPIC_MODEL', 'claude-sonnet-4-20250514')


def _truncate_text(text, max_chars=100000):
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) <= max_chars:
        return text
    half = max_chars // 2
    return (
        f'{text[:half]}\n\n[... contenu central omis pour respecter la limite ...]\n\n{text[-half:]}'
    )


def _extract_json_array(raw_text):
    raw_text = raw_text.strip()
    if raw_text.startswith('```'):
        raw_text = re.sub(r'^```(?:json)?\s*', '', raw_text)
        raw_text = re.sub(r'\s*```$', '', raw_text)
    start = raw_text.find('[')
    end = raw_text.rfind(']')
    if start == -1 or end == -1 or end <= start:
        raise ValueError('JSON array introuvable dans la réponse IA')
    return json.loads(raw_text[start:end + 1])


def _validate_question(item):
    if not isinstance(item, dict):
        return None
    text = str(item.get('text', '')).strip()
    options = item.get('options', [])
    correct = str(item.get('correct', '')).strip().lower()
    explanation = str(item.get('explanation', '')).strip()
    if not text or not isinstance(options, list) or len(options) != 4:
        return None
    if correct not in {'a', 'b', 'c', 'd'}:
        return None
    cleaned_options = [str(option).strip()[:255] for option in options]
    if any(not option for option in cleaned_options):
        return None
    return {
        'text': text,
        'options': cleaned_options,
        'correct': correct,
        'explanation': explanation or 'Réponse basée sur le contenu du cours.',
    }


def _normalize_questions(raw_questions, count):
    validated = []
    seen = set()
    for item in raw_questions:
        question = _validate_question(item)
        if not question:
            continue
        key = question['text'].lower()
        if key in seen:
            continue
        seen.add(key)
        validated.append(question)
        if len(validated) >= count:
            break
    return validated


def generate_questions_with_ai(text, count=10, level='easy'):
    client = _get_client()
    if not client or not text.strip():
        return None

    course_text = _truncate_text(text)
    level_hint = LEVEL_INSTRUCTIONS.get(level, LEVEL_INSTRUCTIONS['medium'])

    prompt = f"""Tu es un professeur expert qui crée des QCM pédagogiques en français.

À partir du cours ci-dessous, génère exactement {count} questions à choix multiples.

{level_hint}

Règles strictes:
- Base-toi UNIQUEMENT sur le contenu fourni
- 4 options par question, une seule bonne réponse (a, b, c ou d)
- Varie les types: définition, compréhension, application, analyse
- Options courtes (max 120 caractères)
- Pas de questions hors sujet ni de "toutes les réponses ci-dessus"
- Chaque question doit avoir une explication pédagogique claire

Réponds UNIQUEMENT avec un tableau JSON valide:
[
  {{
    "text": "Question ici ?",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct": "b",
    "explanation": "Pourquoi cette réponse est correcte."
  }}
]

COURS:
{course_text}
"""

    try:
        response = client.messages.create(
            model=_get_model(),
            max_tokens=8192,
            temperature=0.4,
            messages=[{'role': 'user', 'content': prompt}],
        )
        raw_questions = _extract_json_array(response.content[0].text)
        questions = _normalize_questions(raw_questions, count)
        if len(questions) < max(3, count // 3):
            logger.warning('Réponse IA insuffisante: %s questions sur %s', len(questions), count)
            return None
        return questions
    except Exception as exc:
        logger.exception('Échec génération quiz IA: %s', exc)
        return None


def summarize_with_ai(text, sentence_count=4):
    client = _get_client()
    if not client or not text.strip():
        return None

    course_text = _truncate_text(text, max_chars=60000)
    prompt = f"""Résume ce cours en français en {sentence_count} phrases claires et pédagogiques.
Concentre-toi sur les idées principales, définitions importantes et concepts clés.
Ne numérote pas les phrases. Pas de markdown.

COURS:
{course_text}
"""

    try:
        response = client.messages.create(
            model=_get_model(),
            max_tokens=1024,
            temperature=0.2,
            messages=[{'role': 'user', 'content': prompt}],
        )
        summary = response.content[0].text.strip()
        return summary if len(summary) > 20 else None
    except Exception as exc:
        logger.exception('Échec résumé IA: %s', exc)
        return None


def generate_questions_offline_from_text(text, count=10):
    """Génération de questions hors-ligne via pipeline RAG léger + heuristique.

    Retourne une liste de questions au même format que `generate_questions_with_ai`.
    """
    try:
        from . import rag_generator
    except Exception:
        logger.warning('Module rag_generator indisponible')
        return None
    try:
        questions = rag_generator.generate_questions_from_text(text, count=count)
        # normalize format
        if not questions:
            return None
        validated = []
        for q in questions:
            if not isinstance(q, dict):
                continue
            text_q = str(q.get('text', '')).strip()
            options = q.get('options', [])
            if len(options) != 4:
                continue
            correct = str(q.get('correct', 'a')).lower()
            if correct not in {'a', 'b', 'c', 'd'}:
                # if correct is an index
                try:
                    idx = int(correct)
                    correct = 'abcd'[idx]
                except Exception:
                    correct = 'a'
            validated.append({
                'text': text_q,
                'options': [str(o) for o in options],
                'correct': correct,
                'explanation': q.get('explanation', '') or 'Réponse basée sur le contenu.',
                'question_type': q.get('question_type', 'mcq'),
                'correct_options': q.get('correct_options', '')
            })
        return validated[:count]
    except Exception as exc:
        logger.exception('Échec génération offline: %s', exc)
        return None
