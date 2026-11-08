"""Pipeline RAG léger + générateur heuristique de QCM.

But: fournir une génération de quiz hors-ligne sans dépendre d'API payante.

Fonctionnalités:
- extraction de texte depuis un PDF
- découpage en chunks
- indexation FAISS avec embeddings `sentence-transformers`
- récupération des chunks pertinents
- génération heuristique de questions QCM (cloze + distractors)

Le code gère proprement l'absence de dépendances (retourne None).
"""
from typing import List, Optional, Tuple
import os
import re
import logging

logger = logging.getLogger(__name__)
try:
    from . import paraphraser
except Exception:
    paraphraser = None


def extract_text_from_pdf(path: str) -> Optional[str]:
    try:
        from pypdf import PdfReader
    except Exception:
        logger.warning('pypdf non installé; extraction PDF impossible')
        return None
    if not os.path.exists(path):
        logger.warning('Fichier PDF introuvable: %s', path)
        return None
    try:
        reader = PdfReader(path)
        parts = []
        for page in reader.pages:
            parts.append(page.extract_text() or '')
        return '\n\n'.join(parts)
    except Exception as exc:
        logger.exception('Erreur lecture PDF: %s', exc)
        return None


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    if not text:
        return []
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    chunks = []
    current = ''
    for p in paragraphs:
        if len(current) + len(p) + 2 <= chunk_size:
            current = (current + '\n\n' + p).strip()
        else:
            if current:
                chunks.append(current)
            # start new chunk with overlap
            current = p
    if current:
        chunks.append(current)
    # apply simple overlap merging to ensure context
    merged = []
    for i, c in enumerate(chunks):
        if i > 0:
            prev = merged[-1]
            if len(prev) < chunk_size and len(c) < chunk_size:
                merged[-1] = (prev + '\n\n' + c)[: chunk_size + overlap]
                continue
        merged.append(c[:chunk_size + overlap])
    return merged


def _load_embeddings_model(name: str = 'all-MiniLM-L6-v2'):
    try:
        from sentence_transformers import SentenceTransformer
    except Exception:
        logger.warning('sentence-transformers non installé')
        return None
    try:
        model = SentenceTransformer(name)
        return model
    except Exception as exc:
        logger.exception('Impossible de charger le modèle embeddings: %s', exc)
        return None


def build_faiss_index(chunks: List[str], model_name: str = 'all-MiniLM-L6-v2') -> Optional[Tuple[object, object, List[str]]]:
    model = _load_embeddings_model(model_name)
    if model is None or not chunks:
        return None
    try:
        import numpy as np
        import faiss
    except Exception:
        logger.warning('faiss ou numpy non installé; build index impossible')
        return None
    try:
        embeddings = model.encode(chunks, convert_to_numpy=True, show_progress_bar=False)
        # normalize for cosine similarity
        faiss.normalize_L2(embeddings)
        dim = embeddings.shape[1]
        index = faiss.IndexFlatIP(dim)
        index.add(embeddings)
        return model, index, chunks
    except Exception as exc:
        logger.exception('Échec création index FAISS: %s', exc)
        return None


def retrieve_relevant(query: str, model, index, chunks: List[str], k: int = 3) -> List[str]:
    try:
        import numpy as np
    except Exception:
        return []
    if not query or model is None or index is None:
        return []
    try:
        q_emb = model.encode([query], convert_to_numpy=True)
        from numpy.linalg import norm
        # normalize
        q_emb = q_emb / (norm(q_emb, axis=1, keepdims=True) + 1e-12)
        D, I = index.search(q_emb, k)
        idxs = I[0].tolist()
        results = [chunks[i] for i in idxs if i < len(chunks)]
        return results
    except Exception as exc:
        logger.exception('Erreur retrieval FAISS: %s', exc)
        return []


def _candidate_answers_from_chunks(chunks: List[str]) -> List[str]:
    answers = []
    # prefer sequences starting with capital (noms propres), mais accepter
    # aussi mots longs / groupes de mots en minuscules (ex: photosynthèse)
    pattern_cap = re.compile(r"\b([A-ZÀ-ÖØ-Þ][a-zà-öø-ÿ]{3,}(?:\s+[A-ZÀ-ÖØ-Þ][a-zà-öø-ÿ]{2,})*)\b")
    pattern_any = re.compile(r"\b([a-zà-öø-ÿA-ZÀ-ÖØ-Þ]{6,}(?:\s+[a-zà-öø-ÿA-ZÀ-ÖØ-Þ]{3,})?)\b")
    for c in chunks:
        # collect capitalized matches first
        for m in pattern_cap.findall(c):
            if 3 <= len(m) <= 60:
                answers.append(m)
        # then collect long words / phrases as fallback
        for m in pattern_any.findall(c):
            if 3 <= len(m) <= 60:
                answers.append(m)
    # dedupe while preserving order
    seen = set()
    out = []
    for a in answers:
        la = a.lower()
        if la in seen:
            continue
        seen.add(la)
        out.append(a)
    return out


def generate_questions_from_text(text: str, count: int = 10) -> Optional[List[dict]]:
    if not text or not text.strip():
        return None
    chunks = chunk_text(text)
    built = build_faiss_index(chunks)
    if built is None:
        # try heuristic generation without retrieval
        candidates = _candidate_answers_from_chunks(chunks or [text])
        return _build_mcq_from_candidates(candidates, count)
    model, index, chunks = built
    # use whole text as query to get relevant chunks
    query = ' '.join(chunks[:3]) if chunks else text
    relevant = retrieve_relevant(query, model, index, chunks, k=6)
    candidates = _candidate_answers_from_chunks(relevant)
    if len(candidates) < 4:
        # broaden candidate pool
        candidates = _candidate_answers_from_chunks(chunks)
    questions = _build_mcq_from_candidates(candidates, count, emb_model=model, full_text=text)
    # paraphrase questions if paraphraser available
    if paraphraser:
        try:
            questions = paraphraser.paraphrase_questions(questions)
        except Exception:
            pass
    return questions


def _find_sentence_with_answer(answer: str, chunks: List[str], full_text: Optional[str] = None) -> Optional[str]:
    a = re.escape(answer)
    pattern = re.compile(r'([^\.\?!\n]*' + a + r'[^\.\?!\n]*[\.\?!]?)', re.IGNORECASE)
    # search in full_text first for a richer sentence
    if full_text:
        for m in pattern.findall(full_text):
            s = m.strip()
            if len(s) > 20:
                return s
    # fallback: search in chunks
    for c in chunks:
        for m in pattern.findall(c):
            s = m.strip()
            if len(s) > 20:
                return s
    return None


def _build_mcq_from_candidates(candidates: List[str], count: int, emb_model=None, full_text: Optional[str] = None) -> List[dict]:
    questions = []
    if not candidates:
        return questions
    pool = list(dict.fromkeys(candidates))  # dedupe preserving order
    import random
    random.shuffle(pool)

    # prepare embeddings for distractor selection if available
    cand_emb = None
    if emb_model is not None and len(pool) >= 4:
        try:
            import numpy as np
            cand_emb = emb_model.encode(pool, convert_to_numpy=True, show_progress_bar=False)
            # normalize
            from numpy.linalg import norm
            cand_emb = cand_emb / (norm(cand_emb, axis=1, keepdims=True) + 1e-12)
        except Exception:
            cand_emb = None

    # try to load spaCy French model for better linguistic filtering (optional)
    nlp = None
    try:
        import spacy
        try:
            nlp = spacy.load('fr_core_news_sm')
        except Exception:
            # try to load any small fr model by name if installed
            try:
                from spacy.util import get_installed_models
                for name in get_installed_models():
                    if name.startswith('fr'):
                        nlp = spacy.load(name)
                        break
            except Exception:
                nlp = None
    except Exception:
        nlp = None

    def _normalize_for_compare(s: str) -> str:
        s = s.strip().lower()
        if nlp:
            doc = nlp(s)
            lemmas = [tok.lemma_.lower() for tok in doc if not tok.is_punct and not tok.is_space]
            return ' '.join(lemmas)
        return re.sub(r"[^a-z0-9à-ÿ ]+", '', s)

    def _postprocess_question_text(q: str) -> str:
        # Nettoie les préfixes longs et fragments injoints (ex: 'Cours : ... Objectif ...')
        if not q or not isinstance(q, str):
            return q
        s = q.strip()
        s = re.sub(r'(?is)\bParaphrase\s*:\s*', '', s)
        s = re.sub(r'(?is)\bSelon\s+l\'auteur\s+du\s+document\s*[,\-:]\s*', '', s)
        s = re.sub(r'(?is)^\s*(?:Selon\s+le\s+texte|Selon\s+le\s+document|Selon\s+le\s+document\s+fourni|En\s+tenant\s+compte\s+du\s+contexte)\s*[,\-:]\s*', '', s)
        s = re.sub(r'(?is)\bSolution\s*\d*\s*[:\-]?\s*', '', s)
        s = re.sub(r'(?is)\bQuestion\s*[:\-]?\s*', '', s)
        s = re.sub(r'(?is)\bRéponse\s*[:\-]?\s*', '', s)
        s = re.sub(r'(?is)\bresponse\s*[:\-]?\s*', '', s)
        s = re.sub(r'(?is)\b###\s*.*?\n?', '', s)
        s = re.sub(r'Cours\s*:\s*.*?(?=(Objectif|Niveau|$))', '', s, flags=re.IGNORECASE)
        s = re.sub(r'Niveau\s*:\s*[^\n\?\.]*(?=[\n\?\.]|$)', '', s, flags=re.IGNORECASE)
        s = re.sub(r'Objectif\s*[:\-]?[^\n\?\.]*(?=[\n\?\.]|$)', '', s, flags=re.IGNORECASE)
        s = re.sub(r'\s+', ' ', s).strip()
        parts = re.split(r'(?<=[\.!?])\s+', s)
        if parts:
            s = parts[0]
        s = re.sub(r'_{2,}', '_____', s)
        s = re.sub(r'\s*_____\s*', ' _____ ', s)
        s = s.strip()
        if not s.endswith('?'):
            s = s.rstrip('. ') + ' ?'
        s = re.sub(r',\s*,+', ',', s)
        s = re.sub(r'\s+,', ',', s)
        s = re.sub(r'\.{2,}', '.', s)
        s = s.strip()
        s = re.sub(r'\s+\?', ' ?', s)
        return s

    i = 0
    while len(questions) < count and i < len(pool):
        answer = pool[i]
        i += 1
        # find a sentence context containing the answer to make a natural question
        sent = _find_sentence_with_answer(answer, pool, full_text) or _find_sentence_with_answer(answer, candidates, full_text) or ''
        if sent:
            # remplacer uniquement le token exact (frontières de mot)
            try:
                q_text = re.sub(r"\b" + re.escape(answer) + r"\b", '_____', sent, count=1, flags=re.IGNORECASE)
            except Exception:
                q_text = sent.replace(answer, '_____')
            if not q_text.strip().endswith('?'):
                q_text = f"Selon le texte, {q_text.strip()} ?"
        else:
            q_text = f"Quel terme du texte correspond à: {answer}?"

        # post-traiter pour enlever préfixes inutiles et rendre la phrase lisible
        q_text = _postprocess_question_text(q_text)
        # si le post-traitement vide la phrase ou la rend non significative, retomber sur une question sûre
        if not q_text or len(re.sub(r"[^A-Za-z0-9]", '', q_text)) < 6 or q_text.strip().startswith('Selon le texte') or q_text.strip().startswith('Selon le document'):
            q_text = f"Quel terme du texte correspond à : {answer} ?"

        # select distractors
        distractors = []
        if cand_emb is not None:
            try:
                import numpy as np
                # compute similarities
                idx = pool.index(answer)
                sims = cand_emb.dot(cand_emb[idx])
                # sort indices by similarity descending, exclude self
                order = list(np.argsort(-sims))
                for j in order:
                    if pool[j].lower() == answer.lower():
                        continue
                    if pool[j] not in distractors:
                        distractors.append(pool[j])
                    if len(distractors) >= 3:
                        break
            except Exception:
                distractors = []

        # fallback simple distractors
        if len(distractors) < 3:
            for d in pool[i:i + 20]:
                if d.lower() == answer.lower():
                    continue
                # filter too-similar distractors using simple normalization
                if d not in distractors and _normalize_for_compare(d) != _normalize_for_compare(answer):
                    distractors.append(d)
                if len(distractors) >= 3:
                    break

        #最後の手段: mutate strings, ensure they are not too similar
        attempts = 0
        while len(distractors) < 3 and attempts < 10:
            fake = _mutate_string(answer)
            if fake.lower() != answer.lower() and fake not in distractors and _normalize_for_compare(fake) != _normalize_for_compare(answer):
                distractors.append(fake)
            attempts += 1

        options = [answer] + distractors[:3]
        # ensure we have 4 options
        while len(options) < 4:
            options.append('Choix')
        random.shuffle(options)

        # more variety and more interesting quizzes
        # about 40% TF, 35% multi, 25% classic MCQ
        r = random.random()
        if r < 0.40:
            q_type = 'tf'
        elif r < 0.75:
            q_type = 'multi'
        else:
            q_type = 'mcq'

        correct = 'abcd'[options.index(answer)]
        correct_options = None
        if q_type == 'tf':
            # build a true statement based on the sentence if possible
            # keep options Vrai/Faux
            options = ['Vrai', 'Faux', '—', '—']
            # sentence contained the answer so statement is true
            correct = 'a'
        elif q_type == 'multi':
            # select an extra correct option distinct from answer
            # pick first distractor in options that's not the answer
            keys = []
            for o in options:
                if _normalize_for_compare(o) == _normalize_for_compare(answer):
                    keys.append(o)
                    break
            # try to pick one other plausible correct from pool
            extra = None
            for d in distractors:
                if _normalize_for_compare(d) != _normalize_for_compare(answer) and d in options:
                    extra = d
                    break
            if extra is None:
                # fallback to next option in pool
                for o in options:
                    if _normalize_for_compare(o) != _normalize_for_compare(answer):
                        extra = o
                        break
            # build correct options letters
            correct_indices = []
            for idx, o in enumerate(options):
                if _normalize_for_compare(o) == _normalize_for_compare(answer) or (extra and _normalize_for_compare(o) == _normalize_for_compare(extra)):
                    correct_indices.append(idx)
            if not correct_indices:
                correct_indices = [options.index(answer)]
            correct_options = ','.join('abcd'[idx] for idx in correct_indices)
        qdict = {
            'text': q_text,
            'options': options,
            'correct': correct,
            'explanation': f'Réponse: {answer} — basée sur le contenu fourni.',
            'question_type': q_type,
        }
        if correct_options:
            qdict['correct_options'] = correct_options
        questions.append(qdict)

    return questions


def rewrite_questions_rules(questions: List[dict]) -> List[dict]:
    """Applique des réécritures basiques pour améliorer la fluidité des questions.

    Couvre les cas fréquents quand aucun LLM local n'est disponible.
    """
    out = []
    for q in questions:
        t = q.get('text', '') or ''
        s = t.strip()
        s = re.sub(r'(?is)\bParaphrase\s*:\s*', '', s)
        s = re.sub(r'(?is)^\s*(?:Selon\s+le\s+texte|Selon\s+le\s+document|Selon\s+le\s+document\s+fourni)\s*[,\-:]\s*', '', s)
        s = re.sub(r'(?is)\bSolution\s*\d*\s*[:\-]?\s*', '', s)
        s = re.sub(r'(?is)\b###\s*.*?\n?', '', s)
        # transformer 'Quel terme du texte correspond à: X ?' -> 'X correspond à _____ ?' (simple)
        m = re.match(r'(?i)^Quel terme du texte correspond à\s*:\s*(.+)\s*\?$', s)
        if m:
            answer = m.group(1).strip()
            s = f"{answer} correspond à _____ ?"
        s = re.sub(r'\s+,', ',', s)
        s = re.sub(r'\s+\?', ' ?', s)
        s = re.sub(r'\s+', ' ', s).strip()
        if not s.endswith('?'):
            s = s.rstrip('. ') + ' ?'
        nq = dict(q)
        nq['text'] = s
        out.append(nq)
    return out


def _mutate_string(s: str) -> str:
    # transforme légèrement une chaîne pour créer un distractor simple
    import random
    s = s.strip()
    if not s:
        return 'Choix'
    parts = s.split()
    if len(parts) > 1:
        # swap two words
        i = random.randrange(len(parts))
        j = random.randrange(len(parts))
        parts[i], parts[j] = parts[j], parts[i]
        return ' '.join(parts)
    # single word: replace a vowel
    return re.sub(r'[aeiouyAEIOUYàâäéèêëîïôöùûü]', lambda m: random.choice('aeiouy'), s)
