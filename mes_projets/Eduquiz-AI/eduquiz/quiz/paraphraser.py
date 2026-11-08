"""Paraphraser optionnel utilisant gpt4all si disponible.

Fonctions exposées:
- paraphrase_question(text) -> text
- paraphrase_questions(list_of_dicts) -> list_of_dicts

Le module est tolérant à l'absence de gpt4all: renvoie l'input non modifié.
"""
import logging
logger = logging.getLogger(__name__)


def _get_gpt4all():
    try:
        from gpt4all import GPT4All
        return GPT4All
    except Exception as exc:
        logger.info('gpt4all non disponible: %s', exc)
        return None


def paraphrase_question(text: str) -> str:
    if not text:
        return text
    GPT = _get_gpt4all()
    if not GPT:
        return text
    try:
        # utiliser le modèle téléchargé localement si présent
        model_name = 'Phi-3 Mini Instruct'
        model_file = 'Phi-3-mini-4k-instruct.Q4_0.gguf'
        model_path = 'models/gpt4all'
        try:
            gpt = GPT(model_file, model_path=model_path)
        except Exception:
            # fallback au nom logique
            gpt = GPT(model_name, model_path=model_path)
        prompt = f"Paraphrase la question suivante en français en conservant le sens et le mot manquant '_____':\n\n{text}\n\nRéponse:"
        resp = gpt.generate(prompt)
        if isinstance(resp, dict):
            out = resp.get('response') or resp.get('choices')
            if isinstance(out, list):
                return out[0]
        if isinstance(resp, str):
            return resp
        return text
    except Exception as exc:
        logger.exception('Erreur paraphrase gpt4all: %s', exc)
        return text


def paraphrase_questions(questions):
    """Paraphrase la clé `text` de chaque question si possible."""
    if not questions:
        return questions
    out = []
    for q in questions:
        try:
            t = q.get('text', '')
            pt = paraphrase_question(t)
            nq = dict(q)
            nq['text'] = pt
            out.append(nq)
        except Exception:
            out.append(q)
    return out
