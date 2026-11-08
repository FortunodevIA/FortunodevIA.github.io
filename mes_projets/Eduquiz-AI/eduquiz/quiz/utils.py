import io
import random
import re
import unicodedata
from collections import Counter
from PyPDF2 import PdfReader

from .ai_service import is_ai_enabled

FRENCH_STOPWORDS = {
    'et', 'la', 'le', 'les', 'des', 'un', 'une', 'de', 'du', 'dans', 'pour', 'sur',
    'avec', 'sans', 'est', 'sont', 'qui', 'que', 'par', 'au', 'aux', 'ce', 'cet',
    'cette', 'ces', 'ceci', 'cela', 'ça', 'se', 'sa', 'son', 'ses', 'en', 'comme',
    'ou', 'où', 'a', 'il', 'elle', 'nous', 'vous', 'ils', 'elles', 'on', 'leur',
    'lui', 'eux', 'celui', 'celle', 'ceux', 'ci', 'ça', 'mais', 'donc', 'or', 'ni',
    'car', 'si', 'non', 'plus', 'moins', 'très', 'tout', 'tous', 'être', 'avoir',
    'faire', 'peut', 'entre', 'avant', 'après', 'pendant', 'sous', 'parmi', 'fait',
    'été', 'aussi', 'nouveau', 'nouvelle',
}
GENERIC_TERM_HEADS = {
    'système', 'secteur', 'service', 'partie', 'processus', 'fonction', 'élément',
    'éléments', 'domaine', 'approche', 'aspect', 'méthode', 'groupe', 'ensemble',
    'état', 'mécanisme', 'structure', 'exercice', 'organisation', 'organisationnel',
}
WEAK_KEYWORDS = {
    'obligatoire', 'proche', 'couramment', 'souvent', 'responsable', 'garantir',
    'assurer', 'obtenir', 'organiser', 'appelée', 'appelé', 'appelées', 'appelés',
    'servir', 'utilisé', 'utilisée', 'utilisées', 'utilisés', 'sécurisation', 'sécurité',
    'titre', 'title', 'document', 'page', 'content', 'balise', 'balises', 'doctype',
    'language', 'langage', 'première', 'premiere', 'générale', 'generale', 'section',
    'permet', 'analyse', 'théorie', 'concept', 'principe', 'message', 'texte',
    'suivant', 'vidéo', 'video', 'simulation', 'cette', 'chaque', 'celui', 'celle',
}
ENGLISH_STOPWORDS = {
    'the', 'and', 'for', 'with', 'from', 'that', 'this', 'are', 'was', 'were', 'will',
    'can', 'not', 'have', 'has', 'had', 'but', 'you', 'your', 'their', 'them', 'they',
    'what', 'which', 'when', 'where', 'how', 'why', 'all', 'any', 'one', 'two', 'three',
}


def extract_pdf_text(uploaded_file):
    raw_text = ''
    try:
        uploaded_file.seek(0)
        try:
            reader = PdfReader(uploaded_file)
            pages = [page.extract_text() or '' for page in reader.pages]
            raw_text = '\n'.join(pages)
        except Exception:
            uploaded_file.seek(0)
            content = uploaded_file.read()
            try:
                reader = PdfReader(io.BytesIO(content))
                pages = [page.extract_text() or '' for page in reader.pages]
                raw_text = '\n'.join(pages)
            except Exception:
                raw_text = ''
    except Exception:
        return ''

    # quick heuristic: if extracted text contains many replacement characters or squares, try fallbacks
    def _seems_garbage(s: str) -> bool:
        if not s:
            return True
        # replacement char � or empty squares
        bad = s.count('\ufffd') + s.count('�') + s.count('□')
        if bad > max(3, len(s) // 200):
            return True
        # too many non-printable or non-letter chars
        printable = re.sub(r'\s', '', s)
        letters = len(re.findall(r'[A-Za-zÀ-ÿ]', printable))
        if letters < max(10, len(printable) // 10):
            return True
        return False

    if _seems_garbage(raw_text):
        # try PyMuPDF (fitz) for better extraction if available
        try:
            import fitz
            uploaded_file.seek(0)
            data = uploaded_file.read()
            doc = fitz.open(stream=data, filetype='pdf')
            pages = [p.get_text('text') or '' for p in doc]
            raw_text = '\n'.join(pages)
        except Exception:
            # try pdfplumber as another fallback
            try:
                import pdfplumber
                uploaded_file.seek(0)
                with pdfplumber.open(io.BytesIO(uploaded_file.read())) as pdf:
                    pages = [p.extract_text() or '' for p in pdf.pages]
                raw_text = '\n'.join(pages)
            except Exception:
                raw_text = ''

    if not raw_text:
        return ''

    # normalize unicode and remove isolated control/box characters
    try:
        raw_text = unicodedata.normalize('NFKC', raw_text)
    except Exception:
        pass
    raw_text = re.sub(r'[\ufffd□]', ' ', raw_text)
    raw_text = re.sub(r'[^\x09\x0A\x0D\x20-\uFFFF]', ' ', raw_text)
    return _clean_extracted_pdf_text(raw_text)


def _clean_text(text):
    if not isinstance(text, str):
        return ''
    text = _clean_math_ocr_noise(text)
    return re.sub(r'\s+', ' ', text).strip()


def has_meaningful_extracted_text(text):
    if not isinstance(text, str):
        return False
    cleaned = re.sub(r'\s+', ' ', text).strip()
    if not cleaned:
        return False
    if len(cleaned) < 40:
        return False
    words = re.findall(r'[A-Za-zÀ-ÿ]+', cleaned)
    if len(words) < 5:
        return False
    if sum(len(word) for word in words) < 30:
        return False
    lower = cleaned.lower()
    math_markers = ['logit', 'probit', 'modèle', 'modele', 'fonction', 'probabilité', 'probabilite', 'variable', 'math', 'formule']
    if any(marker in lower for marker in math_markers):
        return True
    return True


def _looks_like_formula(text):
    if not isinstance(text, str):
        return False
    value = text.strip()
    if not value:
        return False

    # A normal sentence containing a formula is not "formula-only garbage".
    alpha_chars = len(re.findall(r'[A-Za-zÀ-ÿ]', value))
    if alpha_chars >= 12:
        return False

    markers = ['pr(', 'phi(', 'β', 'φ', 'exp(', 'logit', 'probit', 'xik', 'xk', 'xi', 'xj', '|']
    matches = sum(1 for marker in markers if marker in value.lower())
    if matches < 2:
        return False
    return bool(re.search(r'[=<>+*/|%{}]', value)) or 'β' in value or 'φ' in value


def _is_noise_pdf_line(line):
    low = line.lower()
    if len(re.findall(r'[a-zà-ÿ]', low)) < 5:
        return True
    if re.search(r'table des matières|table des matieres|table of contents|sommaire|tableau des matières|tableau des matieres', low):
        return True
    if re.search(r'^(page|page\s*\d+)$', low):
        return True
    if re.search(r'\b(equipe pédagogique|equipe pedagogique|uvci|version\s*\d|201\d|202\d|copyright|©|@)\b', low):
        return True
    if re.search(r'\b(objectifs?|introduction|contenu|annexe|références|references|bibliographie|index|sommaire)\b.*\d+$', low):
        return True
    if re.match(r'^[0-9\.\-\sivxlcdm]+$', low):
        return True
    if re.search(r'\b(Leçon|Lecon|Chapitre|Section|Titre|Annexe|Partie)\b', line) and ':' in line and len(line.split()) < 15:
        return True
    if re.search(r'\bI{1,3}\b\s*[-–]\s*\w+', line) and re.search(r'\d{1,3}', line):
        return True
    if len(re.findall(r'\d+', line)) >= 3 and len(line.split()) < 20:
        return True
    return False


def _clean_math_ocr_noise(text):
    t = text
    t = t.replace('“', '"').replace('”', '"').replace('’', "'")
    t = re.sub(r'"\s*Pr\s*;\s*', ' ', t, flags=re.IGNORECASE)
    t = re.sub(r'(?i)\bpr\s*;\s*(?:xik|xk|xi|xj)\s*=\s*[^.?!]+', ' ', t)
    t = re.sub(r'(?i)\b(?:xik|xk|xi|xj)\s*=\s*(?:kxik|k?xik|k?xk|k?xi|k?xj)\s*[^.?!]+', ' ', t)
    t = re.sub(r'(?i)\b(?:phi|φ)\s*\(\s*(?:xi|xik|xk|xj)\s*\)', ' ', t)
    t = re.sub(r'\b(?:xik|xk|xi|xj)\b(?:(?:\s*[=+\-*/<>]+\s*)\b(?:xik|xk|xi|xj)\b)+', ' ', t)
    t = re.sub(r'\bpr\s*;\s*[^.?!]+', ' ', t, flags=re.IGNORECASE)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def _clean_extracted_pdf_text(text):
    text = _clean_math_ocr_noise(text)
    text = text.replace('\r', '\n')
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    cleaned = []
    for line in lines:
        stripped = line
        stripped = re.sub(r'(?i)\bpr\s*\([^)]*\)\s*=\s*[A-Za-z0-9βφ\s\(\)\|\[\]\{\}=<>+\-*/.,%]+', ' [formule] ', stripped)
        stripped = re.sub(r'(?i)\b(?:phi|φ)\s*\([^)]*\)', ' [formule] ', stripped)
        stripped = re.sub(r'(?i)\b(?:exp|logit|probit)\s*\([^)]*\)', ' [formule] ', stripped)
        stripped = re.sub(r'\b(?:β|φ|xik|xk|xi|xj)\b', ' ', stripped)
        stripped = re.sub(r'\s+', ' ', stripped).strip()
        stripped = stripped.replace('"', ' ')
        if not stripped.strip():
            continue
        if _looks_like_formula(stripped):
            continue
        if _is_noise_pdf_line(stripped):
            continue
        if re.search(r'\d+\s*$|\s+\d+\s*$', stripped) and len(stripped.split()) < 8:
            continue
        if re.match(r'^(?:[IVXLCDM]+\.)?\s*\d+[\.)]?\s*.+$', stripped):
            continue
        if re.search(r'[=<>+*/%^{}]', stripped) and len(re.findall(r'[A-Za-zÀ-ÿ]', stripped)) < 8:
            continue
        cleaned.append(stripped)
    return ' '.join(cleaned)


def _is_noise_text_segment(text):
    low = text.lower()
    if re.search(r'table des matières|table des matieres|table of contents|sommaire|tableau des matières|tableau des matieres|source\s*:\s*wiki(?:pedia|pé|pédia)|travaux pratique|objectif(?:s)?|index|annexe|bibliographie|lien hypertexte', low):
        return True
    if re.search(r'^(page|page\s*\d+|page:\s*\d+)\b', low):
        return True
    if len(re.findall(r'\d+', text)) >= 3 and len(text.split()) < 20:
        return True
    if re.search(r'\b(Leçon|Lecon|Chapitre|Section|Titre|Annexe|Partie)\b', text) and ':' in text and len(text.split()) < 15:
        return True
    if _is_noise_pdf_line(text):
        return True
    return False


def _normalize_term(term):
    term = term.strip()
    term = re.sub(r"^(?:le|la|les|l'|un|une|des|du|de)\s+", '', term, flags=re.IGNORECASE)
    term = re.sub(r"^['\"“”«»]+|['\"“”«»]+$", '', term).strip()
    return term.lower()


def _display_term(term):
    term = term.strip()
    term = re.sub(r"^(?:le|la|les|l'|un|une|des|du|de)\s+", '', term, flags=re.IGNORECASE)
    term = re.sub(r"^['\"“”«»]+|['\"“”«»]+$", '', term).strip()
    return term


def _is_generic_definition_term(term):
    normalized = _normalize_term(term)
    tokens = [w.lower() for w in re.findall(r"[\wÀ-ÿ']+", normalized) if w]
    if not tokens:
        return True
    if tokens[0] in {'ce', 'cet', 'cette', 'ces', 'ceci', 'cela'} and len(tokens) > 1:
        return tokens[1] in GENERIC_TERM_HEADS
    return any(token in GENERIC_TERM_HEADS and len(tokens) <= 4 for token in tokens)


def _is_valid_term(term):
    if _is_generic_definition_term(term):
        return False
    normalized = _normalize_term(term)
    if any(char.isdigit() for char in normalized):
        return False
    tokens = [w.lower() for w in re.findall(r"[\wÀ-ÿ']+", normalized) if w]
    tokens = [w for w in tokens if w not in FRENCH_STOPWORDS and w not in ENGLISH_STOPWORDS]
    if len(tokens) == 0 or len(tokens) > 8:
        return False
    if len(tokens) == 1 and len(tokens[0]) <= 4:
        return False
    if any(token in WEAK_KEYWORDS for token in tokens):
        return False
    if sum(1 for token in tokens if token in GENERIC_TERM_HEADS) > 0 and len(tokens) <= 5:
        return False
    return any(len(w) > 3 for w in tokens)


DEFINITION_INVALID_STARTS = {
    'très proche de', 'le plus souvent', 'plus souvent', 'souvent', 'couramment', 'fréquemment',
    'utilisé pour', 'utilisé par', 'peut être utilisé', 'permet de', 'lié à',
    'liée à', 'concerne', 'est basé sur', 'est nécessaire pour', 'sert à', 'est très',
}


def _is_valid_definition(definition):
    normalized = definition.strip().lower()
    if not normalized or len(normalized) < 15:
        return False
    if normalized.startswith('est '):
        return False
    if any(normalized.startswith(prefix) for prefix in DEFINITION_INVALID_STARTS):
        return False
    if 'proche de' in normalized and normalized.startswith('très'):  # tournure comparative faible
        return False
    if normalized.count(' ') < 2:
        return False
    return True


def _normalize_option_text(value):
    if not isinstance(value, str):
        return ''
    return re.sub(r'\s+', ' ', value.strip().lower())


def _is_similar_text(a, b):
    a = _normalize_option_text(a)
    b = _normalize_option_text(b)
    if not a or not b:
        return False
    return a == b or a in b or b in a


def _is_valid_distractor(correct, distractor):
    if not isinstance(distractor, str) or not distractor.strip():
        return False
    normalized = _normalize_option_text(distractor)
    if len(normalized) < 3:
        return False
    if normalized in FRENCH_STOPWORDS or normalized in ENGLISH_STOPWORDS or normalized in WEAK_KEYWORDS:
        return False
    if _is_similar_text(correct, normalized) or _is_similar_text(normalized, correct):
        return False
    if normalized in {'analyse', 'théorie', 'concept', 'notion'}:
        return False
    return True


def _keyword_occurrences(text, keyword):
    return len(re.findall(rf"\b{re.escape(keyword)}\b", text.lower()))


def _find_definition_candidates(text):
    text = text.replace('\n', ' ')
    patterns = [
        r'(?:^|[\.\?!]\s*)([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9_\-\'’ ]{2,79}?)\s+est\s+(?:un|une|le|la|l\'|des|du|de la|de l\'|aux?)\s+([^\.\?!]{15,120})',
        r'(?:^|[\.\?!]\s*)([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9_\-\'’ ]{2,79}?)\s+signifie\s+([^\.\?!]{15,120})',
    ]
    candidates = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            term = _clean_text(match.group(1))
            definition = _clean_text(match.group(2)).rstrip(' .;')
            if _looks_like_formula(term) or _looks_like_formula(definition):
                continue
            if len(term) > 2 and len(definition) > 10 and _is_valid_term(term) and _is_valid_definition(definition):
                candidates.append((term, definition))
    return candidates


def _clean_keyword(word):
    return re.sub(r"[^A-Za-zÀ-ÿ0-9\-']", '', word).strip().lower()


def extract_keywords(text, limit=20):
    words = re.findall(r"\b[\wÀ-ÿ']{4,}\b", text.lower())
    filtered = []
    for word in words:
        clean_word = _clean_keyword(word)
        if not clean_word:
            continue
        normalized_word = _normalize_term(clean_word)
        if not normalized_word:
            continue
        if normalized_word in FRENCH_STOPWORDS or normalized_word in ENGLISH_STOPWORDS or normalized_word.isdigit():
            continue
        if normalized_word in WEAK_KEYWORDS or normalized_word in GENERIC_TERM_HEADS:
            continue
        if any(char.isdigit() for char in normalized_word):
            continue
        filtered.append(normalized_word)

    counts = Counter(filtered)
    keywords = [word for word, _ in counts.most_common() if _is_valid_keyword(word)]
    return keywords[:limit]


def _is_valid_keyword(keyword):
    normalized = _normalize_term(keyword)
    if len(normalized) <= 3:
        return False
    if normalized in FRENCH_STOPWORDS or normalized in ENGLISH_STOPWORDS or normalized in WEAK_KEYWORDS:
        return False
    tokens = [w for w in re.findall(r"[\wÀ-ÿ']+", normalized) if w]
    if any(token in WEAK_KEYWORDS or token in GENERIC_TERM_HEADS for token in tokens):
        return False
    if any(token.endswith('ment') for token in tokens):
        return False
    if len(tokens) == 1:
        return len(tokens[0]) > 4
    return True


def _question_hash(text, options, correct):
    normalized_options = [opt.strip().lower() for opt in options]
    normalized_options.sort()
    return f"{text.strip().lower()}|{'|'.join(normalized_options)}|{correct}"


def _is_valid_question_item(item):
    if not item or not isinstance(item, dict):
        return False
    text = item.get('text', '')
    options = item.get('options', [])
    correct = item.get('correct', '')
    if not isinstance(text, str) or len(text.strip()) < 15:
        return False
    if not isinstance(options, list) or len(options) != 4:
        return False
    normalized_options = [_normalize_option_text(opt) for opt in options if isinstance(opt, str) and opt.strip()]
    if len(normalized_options) != 4 or len(set(normalized_options)) != 4:
        return False
    if correct not in ('a', 'b', 'c', 'd'):
        return False
    if options[ord(correct) - ord('a')].strip().lower() not in normalized_options:
        return False
    for i in range(len(normalized_options)):
        for j in range(i + 1, len(normalized_options)):
            if _is_similar_text(normalized_options[i], normalized_options[j]):
                return False
    if len(re.sub(r'[^A-Za-zÀ-ÿ]', '', text)) < 10:
        return False
    if any(_is_similar_text(text, opt) for opt in normalized_options):
        return False
    return True


def _append_unique_questions(questions, candidates, seen_keys, count):
    for item in candidates:
        if not _is_valid_question_item(item):
            continue
        key = _question_hash(item['text'], item['options'], item['correct'])
        if key in seen_keys:
            continue
        seen_keys.add(key)
        questions.append(item)
        if len(questions) >= count:
            break


def _is_html_course(text):
    low = text.lower()
    html_signals = ['<html', '<body', '<head', '<title', 'doctype', 'balise', 'balises', 'html', 'body>', 'href', '<a', '<img', 'css', 'html5']
    count = sum(1 for s in html_signals if s in low)
    return count >= 2


def _generate_html_quiz(text, count=10, level='easy'):
    # Jeu de questions HTML de base utile pour les cours introductifs
    pool = [
        {
            'text': 'Qui est le concepteur du langage HTML ?',
            'options': ['Microsoft', 'Tim Berners-Lee', 'Netscape', 'Le W3C'],
            'correct': 'b',
            'explanation': "Tim Berners-Lee a créé le HTML.",
        },
        {
            'text': "Que signifie l'acronyme HTML ?",
            'options': ['Hyper Technology Mixed Language', 'HyperText Markup Language', 'Hot Text Mapping Language', 'Hyper Tool Machine Language'],
            'correct': 'b',
            'explanation': 'HTML = HyperText Markup Language.',
        },
        {
            'text': 'Dans une page HTML, la balise <body> sert à :',
            'options': ["Définir l'en-tête du document", 'Définir le corps du document', 'Définir le titre du document', 'Ajouter des commentaires'],
            'correct': 'b',
            'explanation': 'La balise <body> contient le corps visible de la page.',
        },
        {
            'text': "Quelle est la règle absolue concernant l'imbrication des balises HTML ?",
            'options': ['La première balise ouverte est la dernière fermée', 'Les balises peuvent rester ouvertes indéfiniment', 'Les balises doivent être écrites en majuscules', 'Les balises doivent toujours être auto-fermantes'],
            'correct': 'a',
            'explanation': "Les balises doivent être correctement imbriquées (LIFO).",
        },
        {
            'text': "La balise <title> permet d'afficher le texte dans :",
            'options': ['Le corps de la page', "La barre de titre ou l'onglet du navigateur", 'La barre d\'état du navigateur', 'Le pied de page du document'],
            'correct': 'b',
            'explanation': "La balise <title> définit le titre affiché dans l'onglet du navigateur.",
        },
    ]

    questions = []
    for i, q in enumerate(pool):
        if len(questions) >= count:
            break
        questions.append(q)

    # Si besoin, générer des questions simples basées sur les mots-clés du texte, filtrées
    if len(questions) < count:
        keywords = extract_keywords(text, limit=30)
        added = set()
        for kw in keywords:
            if len(questions) >= count:
                break
            if not _is_valid_keyword(kw):
                continue
            if kw in added:
                continue
            distractors = _keyword_distractors(kw, keywords)
            prompt = _keyword_prompt(level, len(questions))
            questions.append(_build_keyword_question(kw, distractors, prompt, level))
            added.add(kw)

    return questions[:count]


def _keyword_distractors(correct, keywords):
    distractors = [k for k in keywords if k != correct]
    random.shuffle(distractors)
    result = []
    for keyword in distractors:
        if len(result) >= 3:
            break
        if not _is_valid_distractor(correct, keyword):
            continue
        result.append(keyword)

    if len(result) < 3:
        candidates = [k for k in keywords if k != correct and _is_valid_distractor(correct, k) and k not in result]
        for candidate in candidates:
            if len(result) >= 3:
                break
            result.append(candidate)

    fallback = ['analyse', 'théorie', 'concept', 'expression', 'notion']
    idx = 0
    while len(result) < 3:
        candidate = fallback[idx % len(fallback)]
        if candidate != correct and candidate not in result:
            result.append(candidate)
        idx += 1
    return result


def summarize_text(text, sentence_count=4):
    from .ai_service import summarize_with_ai
    ai_summary = summarize_with_ai(text, sentence_count=sentence_count)
    if ai_summary:
        return ai_summary
    text = _clean_text(text)
    sentences = re.split(r'(?<=[.!?])\s+', text)
    if len(sentences) <= sentence_count:
        return text

    keywords = extract_keywords(text, limit=15)
    scored = []
    for index, sentence in enumerate(sentences):
        score = sum(1 for keyword in keywords if keyword in sentence.lower())
        scored.append((score, index, sentence))

    scored.sort(key=lambda item: (-item[0], item[1]))
    selected = sorted(scored[:sentence_count], key=lambda item: item[1])
    return ' '.join([sentence for _, _, sentence in selected]).strip()


def _build_question(term, definition, distractors, level='easy'):
    wrong_options = list(distractors)
    random.shuffle(wrong_options)
    options = [definition] + wrong_options[:3]
    random.shuffle(options)
    correct_index = options.index(definition)
    labels = ['a', 'b', 'c', 'd']
    if level == 'easy':
        prompt = f'Que signifie « {term} » dans ce cours ?'
    elif level == 'medium':
        prompt = f'Parmi les choix suivants, quelle définition correspond le mieux à « {term} » ?'
    else:
        prompt = f'Dans le contexte du cours, « {term} » désigne :'
    q = {
        'text': prompt,
        'options': options,
        'correct': labels[correct_index],
        'explanation': f'« {term} » correspond à : {definition}.',
    }
    return _finalize_question(q, 'mcq')


def _keyword_prompt(level='easy', index=0):
    easy_templates = [
        'Quel mot-clé est lié au contenu du cours ?',
        'Quel terme parmi la liste est important pour ce cours ?',
        'Lequel de ces mots reflète le mieux le sujet étudié ?'
    ]
    medium_templates = [
        'Parmi ces termes, lequel est le plus pertinent pour le cours ?',
        'Quel mot illustre le mieux le thème du texte ?',
        'Lequel de ces mots est le plus lié au contenu ?'
    ]
    hard_templates = [
        'Quel terme incarne le concept principal du cours ?',
        'Lequel de ces mots est le plus central dans cette leçon ?',
        'Quel terme représente le mieux les notions abordées ?'
    ]
    if level == 'medium':
        return medium_templates[index % len(medium_templates)]
    if level == 'hard':
        return hard_templates[index % len(hard_templates)]
    return easy_templates[index % len(easy_templates)]


def _build_keyword_question(keyword, distractors, prompt, level='easy'):
    wrong_options = list(distractors)
    random.shuffle(wrong_options)
    options = [keyword] + wrong_options[:3]
    random.shuffle(options)
    labels = ['a', 'b', 'c', 'd']
    q = {
        'text': prompt,
        'options': options,
        'correct': labels[options.index(keyword)],
        'explanation': f'Le mot-clé correct est « {keyword} », qui apparaît dans le cours.',
    }
    return _finalize_question(q, 'mcq')


def _build_cloze_question(answer, sentence, distractors, level='medium'):
    blanked = re.sub(re.escape(answer), '_____', sentence, count=1, flags=re.IGNORECASE)
    prompt = f'Complétez la phrase suivante : {blanked}'
    wrong_options = list(distractors)
    random.shuffle(wrong_options)
    options = [answer] + wrong_options[:3]
    random.shuffle(options)
    labels = ['a', 'b', 'c', 'd']
    q = {
        'text': prompt,
        'options': options,
        'correct': labels[options.index(answer)],
        'explanation': f'Le mot correct est « {answer} ».',
    }
    return _finalize_question(q, 'mcq')


def _build_true_false_question(statement, is_true=True):
    options = ['Vrai', 'Faux', 'Pas sûr', 'Aucun des deux']
    correct = 'a' if is_true else 'b'
    return {
        'text': f'Vrai ou faux : {statement}',
        'options': options,
        'correct': correct,
        'explanation': 'La phrase est ' + ('vraie.' if is_true else 'fausse.'),
        'question_type': 'tf',
    }


def _finalize_question(question, question_type=None):
    q = dict(question)
    q_type = question_type or q.get('question_type') or 'mcq'
    q['question_type'] = q_type
    q['correct_options'] = q.get('correct_options', '')
    if q_type == 'tf':
        q['options'] = ['Vrai', 'Faux', 'Pas sûr', 'Aucun des deux']
        q['correct'] = 'a' if q.get('correct', 'a') in ('a', 'b') and q.get('correct', 'a') == 'a' else 'b'
        q['text'] = f"Vrai ou faux : {q['text']}"
    elif q_type == 'multi':
        options = q.get('options', [])
        if isinstance(options, list) and len(options) >= 4:
            q['correct'] = q.get('correct', 'a')
            # keep the original answer plus one second plausible correct option for multi-answer style
            corrected = []
            for idx, key in enumerate('abcd'):
                if idx == ord(q.get('correct', 'a')) - ord('a'):
                    corrected.append(key)
                elif idx == (ord(q.get('correct', 'a')) - ord('a') + 2) % 4:
                    corrected.append(key)
            q['correct_options'] = ','.join(corrected[:2])
    return q


def _build_multi_answer_question(statement, good_statements, distractors=None):
    clean_statement = _clean_text(statement or 'La proposition est correcte.')
    choices = list(good_statements or [])
    if distractors:
        choices.extend(distractors)
    choices = [str(c).strip() for c in choices if str(c).strip()][:4]
    while len(choices) < 4:
        choices.append('Une notion importante du cours')
    random.shuffle(choices)
    correct_indexes = [idx for idx, option in enumerate(choices) if option in good_statements]
    if not correct_indexes:
        correct_indexes = [0, 1]
        choices = choices[:2] + ['Une notion importante du cours', 'Un autre concept du cours']
        random.shuffle(choices)
        corrected = []
        for idx, option in enumerate(choices):
            if idx in (0, 1):
                corrected.append(option)
        if len(corrected) >= 2:
            correct_indexes = [choices.index(corrected[0]), choices.index(corrected[1])]
    q = {
        'text': f'Parmi les affirmations suivantes, lesquelles sont correctes ? {clean_statement}',
        'options': choices[:4],
        'correct': 'a',
        'correct_options': ','.join('abcd'[idx] for idx in sorted(correct_indexes)[:2]),
        'question_type': 'multi',
        'explanation': 'Plusieurs réponses sont correctes selon le cours.',
    }
    return q


def _ensure_question_type_variety(questions, count, text):
    questions = list(questions or [])
    if not questions:
        return questions
    seen_types = {q.get('question_type') for q in questions}
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', _clean_text(text)) if s.strip()]
    sentence_pool = [s for s in sentences if len(s.split()) >= 8 and not _is_noise_text_segment(s)][:8]

    extras = []
    if 'tf' not in seen_types and sentence_pool:
        tf_statement = sentence_pool[0]
        extras.append(_build_true_false_question(tf_statement[:180], True))
    if 'multi' not in seen_types and len(sentence_pool) >= 2:
        question_text = sentence_pool[0]
        good = [sentence_pool[0], sentence_pool[1]]
        distractors = [s for s in sentence_pool[2:5] if s not in good]
        extras.append(_build_multi_answer_question(question_text, good, distractors))

    if extras:
        questions = extras + questions

    while len(questions) < count:
        if sentence_pool:
            stmt = sentence_pool[len(questions) % len(sentence_pool)]
            questions.append(_build_true_false_question(stmt[:180], True))
        else:
            questions.append(_build_true_false_question('Le cours contient des notions importantes et pertinentes.', True))
        if len(questions) >= count:
            break
        questions.append({
            'text': 'Parmi les affirmations suivantes, lesquelles sont correctes ?',
            'options': ['Le cours présente des notions pertinentes', 'Le cours est sans structure', 'Le cours est illisible', 'Le cours n’a pas de sens'],
            'correct': 'a',
            'correct_options': 'a,b',
            'question_type': 'multi',
            'explanation': 'Plusieurs réponses sont correctes selon le cours.',
        })
    return questions[:count]


def generate_quiz_questions(text, count=10, level='easy', mode='default'):
    text = _clean_text(text)
    if not text:
        return []

    questions = []
    seen_keys = set()

    if _is_html_course(text):
        html_questions = _generate_html_quiz(text, count, level)
        html_questions = _ensure_question_type_variety(html_questions, count, text)
        if html_questions and len(html_questions) >= min(count, 3):
            return html_questions[:count]
        _append_unique_questions(questions, html_questions, seen_keys, count)

    if mode in ('smart', 'default'):
        smart_questions = _generate_smart_quiz(text, count, level)
        smart_questions = _ensure_question_type_variety(smart_questions, count, text)
        if smart_questions and len(smart_questions) >= min(count, 3):
            return smart_questions[:count]
        _append_unique_questions(questions, smart_questions or [], seen_keys, count)

    if is_ai_enabled():
        from .ai_service import generate_questions_with_ai
        ai_questions = generate_questions_with_ai(text, count=count, level=level)
        ai_questions = _ensure_question_type_variety(ai_questions or [], count, text)
        if ai_questions and len(ai_questions) >= min(count, 3):
            return ai_questions[:count]
        _append_unique_questions(questions, ai_questions or [], seen_keys, count)

    definitions = _find_definition_candidates(text)
    keywords = extract_keywords(text, limit=40)
    used_terms = set()

    for term, definition in definitions:
        if len(questions) >= count:
            break
        display_term = _display_term(term)
        if not _is_valid_term(display_term):
            continue
        normalized_term = _normalize_term(display_term)
        if normalized_term in used_terms:
            continue
        used_terms.add(normalized_term)

        distractors = [d for _, d in definitions if d != definition]
        unique_distractors = []
        for item in distractors:
            if item not in unique_distractors and item.lower() != definition.lower():
                unique_distractors.append(item)
        distractors = unique_distractors
        if len(distractors) < 3:
            distractors.extend([x for x in keywords if x.lower() != definition.lower()])
        distractors = [d for i, d in enumerate(distractors) if d not in distractors[:i]]
        if len(distractors) < 3:
            distractors.extend(['Une expression', 'Un concept', 'Une notion'])

        question_data = _build_question(display_term, definition, distractors, level)
        _append_unique_questions(questions, [question_data], seen_keys, count)

    if len(questions) < count:
        remaining_keywords = [k for k in keywords if _is_valid_keyword(k)]
        for keyword in remaining_keywords:
            if len(questions) >= count:
                break
            normalized_keyword = _normalize_term(keyword)
            if normalized_keyword in used_terms:
                continue
            used_terms.add(normalized_keyword)
            distractors = _keyword_distractors(keyword, keywords)
            prompt = _keyword_prompt(level, len(questions))
            question_data = _build_keyword_question(keyword, distractors, prompt, level)
            _append_unique_questions(questions, [question_data], seen_keys, count)

    if len(questions) < count:
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
        for sentence in sentences:
            if len(questions) >= count:
                break
            if _is_noise_text_segment(sentence) or len(sentence.split()) < 10:
                continue
            candidates = []
            for token in re.findall(r"[\wÀ-ÿ'’\-]{4,}", sentence):
                if token.lower() in FRENCH_STOPWORDS or token.lower() in ENGLISH_STOPWORDS:
                    continue
                if not _is_valid_keyword(token):
                    continue
                candidates.append((_normalize_term(token), token))
            if not candidates:
                continue
            candidates.sort(key=lambda item: (-len(item[1]), item[0] in keywords, item[1].lower()))
            answer = candidates[0][1]
            if re.search(re.escape(answer), sentence, flags=re.IGNORECASE):
                distractors = _keyword_distractors(answer, keywords)
                question_data = _build_cloze_question(answer, sentence, distractors, level)
                _append_unique_questions(questions, [question_data], seen_keys, count)

    if len(questions) < count:
        default_terms = ['structure', 'balise', 'formulaire', 'connexion', 'algorithme', 'machine']
        for default in default_terms:
            if len(questions) >= count:
                break
            if _normalize_term(default) in used_terms:
                continue
            distractors = _keyword_distractors(default, default_terms)
            question_data = _build_keyword_question(default, distractors, _keyword_prompt(level, len(questions)), level)
            _append_unique_questions(questions, [question_data], seen_keys, count)

    questions = _ensure_question_type_variety(questions, count, text)
    return questions[:count]


def _generate_smart_quiz(text, count=10, level='easy'):
    text = _clean_text(text)
    # Utiliser le TEXTE COMPLET, pas le résumé - essentiel pour la qualité
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
    sentences = [s for s in sentences if not _is_noise_text_segment(s) and len(s.split()) >= 8]
    keywords = extract_keywords(text, limit=50)
    questions = []
    used_answers = set()

    def sentence_score(sentence):
        score = 0
        score += min(5, len(sentence.split()) // 5)
        score += sum(1 for kw in keywords if kw in sentence.lower())
        if re.search(r'\b(est|sont|signifie|désigne|consiste|comprend|permet|fonctionne|utilise)\b', sentence, flags=re.IGNORECASE):
            score += 2
        if len(re.findall(r'[A-ZÀ-Ÿ]', sentence)) < 2:
            score -= 1
        return score

    sentences.sort(key=lambda s: (-sentence_score(s), -len(s)))

    # Extraire des définitions du texte complet avec plusieurs motifs
    for s in sentences:
        if len(questions) >= count:
            break
        m = re.search(r"([A-ZÀ-Ÿ][A-Za-zÀ-ÿ0-9_''\- ]{2,80}?)\s+(?:ne\s+)?(?:est|sont|désigne|designent|signifie|consiste|correspond à|permet de|permet|comprend|utilise|utilisent)\s+([^\.\?!]{15,200})", s, flags=re.IGNORECASE)
        if m:
            term = _display_term(m.group(1))
            definition = _clean_text(m.group(2)).rstrip(' .;')
            if _is_valid_term(term) and _is_valid_definition(definition):
                distractors = [k for k in keywords if k.lower() != definition.lower()][:10]
                distractors = [d for d in distractors if _is_valid_keyword(d)][:3]
                while len(distractors) < 3:
                    distractors.append('Une notion')
                questions.append(_build_question(term, definition, distractors, level))
                used_answers.add(_normalize_term(term))

    # Générer quelques affirmations vrai/faux à partir de bonnes phrases
    for s in sentences:
        if len(questions) >= count:
            break
        if len(questions) >= count or len(questions) >= 3:
            break
        m = re.search(r"([A-ZÀ-Ÿ][A-Za-zÀ-ÿ0-9_''\- ]{3,80}?)\s+(?:est|sont|signifie|désigne|consiste|comprend|permet|utilise)\s+([^\.\?!]{15,120})", s, flags=re.IGNORECASE)
        if m and len(s.split()) > 10:
            if not _is_noise_text_segment(s):
                questions.append(_build_true_false_question(s, True))

    # Puis créer des questions à trou / mots-clés à partir des meilleures phrases
    for s in sentences:
        if len(questions) >= count:
            break
        if _is_noise_text_segment(s):
            continue
        if len(s.split()) < 10:
            continue
        candidates = []
        for token in re.findall(r"[\wÀ-ÿ'’\-]{4,}", s):
            if token.lower() in FRENCH_STOPWORDS or token.lower() in ENGLISH_STOPWORDS:
                continue
            if not _is_valid_keyword(token):
                continue
            norm = _normalize_term(token)
            if norm in used_answers:
                continue
            candidates.append((token, norm))
        if not candidates:
            continue
        candidates.sort(key=lambda item: (-len(item[0]), item[1] in keywords, item[0].lower()))
        answer, norm = candidates[0]
        if not re.search(re.escape(answer), s, flags=re.IGNORECASE):
            continue
        used_answers.add(norm)
        prompt = f"Complétez la phrase : {re.sub(re.escape(answer), '_____', s, count=1, flags=re.IGNORECASE)}"
        distractors = _keyword_distractors(answer, keywords)
        questions.append(_build_keyword_question(answer, distractors, prompt, level))

    # Si le nombre reste insuffisant, revenir à des questions à base de mots-clés (filtrées)
    if len(questions) < count:
        remaining = [k for k in keywords if _is_valid_keyword(k) and _normalize_term(k) not in used_answers]
        for kw in remaining:
            if len(questions) >= count:
                break
            distractors = _keyword_distractors(kw, keywords)
            prompt = _keyword_prompt(level, len(questions))
            questions.append(_build_keyword_question(kw, distractors, prompt, level))

    return questions[:count]


def assess_text_quality(text):
    """Return (score, reasons list). Score 0..1. Reasons are short strings."""
    t = _clean_text(text)
    reasons = []
    length = len(t)
    sentences = [s for s in re.split(r'(?<=[.!?])\s+', t) if s.strip()]
    sentence_count = len(sentences)
    definitions = _find_definition_candidates(t)
    keywords = extract_keywords(t, limit=40)

    # score de longueur
    len_score = min(1.0, length / 3000.0)
    if length < 500:
        reasons.append('texte court')
    # variété des phrases
    sent_score = min(1.0, sentence_count / 8.0)
    if sentence_count < 4:
        reasons.append('peu de phrases')
    # présence de définitions
    def_score = min(1.0, len(definitions) / 3.0)
    if len(definitions) == 0:
        reasons.append('aucune définition détectée')
    # richesse en mots-clés
    kw_score = min(1.0, len(keywords) / 10.0)
    if len(keywords) < 6:
        reasons.append('peu de mots-clés significatifs')

    # moyenne pondérée
    score = (0.4 * len_score) + (0.2 * sent_score) + (0.2 * def_score) + (0.2 * kw_score)
    # normaliser les raisons (unique)
    reasons = list(dict.fromkeys(reasons))
    return score, reasons
