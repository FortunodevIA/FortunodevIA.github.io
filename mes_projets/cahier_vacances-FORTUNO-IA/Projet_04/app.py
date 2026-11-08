"""Interface Streamlit pour interroger l'assistant RAG de l'Hôtel Le Belvédère.

Depuis la racine du dépôt, lancer avec :
    uv run streamlit run Projet_04/app.py
"""

from html import escape
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
from transformers import pipeline

# Construit les chemins à partir de ce fichier pour fonctionner depuis tout dossier.
PROJECT_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJECT_DIR / "data"
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
GENERATION_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"

# Donne au modèle son rôle et lui interdit de compléter avec des faits inventés.
ROLE = (
    "Tu es l'assistant virtuel de l'Hôtel Le Belvédère, au bord du lac d'Annecy.\n"
    "Voici la documentation officielle de l'hôtel :"
)
INSTRUCTION = (
    "Réponds en une ou deux phrases, uniquement à partir des informations "
    "de la documentation ci-dessus. Si plusieurs horaires sont mentionnés, "
    "utilise celui qui correspond précisément au service demandé. "
    "Si l'information ne s'y trouve pas, réponds exactement : "
    '"Je ne sais pas, je vous invite à contacter la réception."'
)

# Configure le titre et l'icône de l'onglet du navigateur.
st.set_page_config(page_title="Hôtel Le Belvédère · Assistant", page_icon="🏨", layout="wide")

# Applique une identité visuelle discrète, inspirée de l'hôtel et du lac.
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Fraunces:opsz,wght@9..144,500;9..144,600&display=swap');
    .stApp {
        background:
            repeating-linear-gradient(0deg, rgba(29, 89, 75, .025) 0 1px, transparent 1px 34px),
            linear-gradient(135deg, #f4f7f3 0%, #e8f0eb 100%);
        color: #1d302a;
        font-family: 'DM Sans', sans-serif;
    }
    .block-container { max-width: 940px; padding-top: 2.6rem; padding-bottom: 3rem; }
    h1, h2, h3 { font-family: 'Fraunces', Georgia, serif !important; color: #173f36; }
    .eyebrow { color: #b85e40; font-size: .76rem; font-weight: 700; letter-spacing: .08em; }
    .intro { max-width: 620px; color: #52645d; font-size: 1.05rem; }
    [data-testid="stSidebar"] { background: #173f36; }
    [data-testid="stSidebar"] * { color: #f1f5f0; }
    [data-testid="stChatMessage"] {
        border: 1px solid rgba(29, 89, 75, .12);
        border-radius: 8px;
    }
    [data-testid="stChatMessage"] *,
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] * {
        color: #1d302a !important;
        -webkit-text-fill-color: #1d302a !important;
    }
    div[data-testid="stForm"] {
        background: rgba(255,255,255,.7);
        border: 1px solid rgba(29, 89, 75, .14);
        border-radius: 12px;
        padding: 0.75rem;
    }
    textarea,
    .stTextArea textarea,
    .stTextInput input {
        background: #ffffff !important;
        color: #1d302a !important;
        -webkit-text-fill-color: #1d302a !important;
        caret-color: #1d302a;
        border: 1px solid #79968a !important;
    }
    textarea::placeholder,
    .stTextArea textarea::placeholder,
    .stTextInput input::placeholder {
        color: #52645d !important;
        -webkit-text-fill-color: #52645d !important;
        opacity: 1;
    }
    div.stButton > button { border-radius: 6px; }
    </style>
    """,
    unsafe_allow_html=True,
)


def render_chat_message(role, content):
    """Affiche une bulle de chat avec des couleurs fixes, indépendantes du thème Streamlit."""
    is_user = role == "user"
    label = "Vous" if is_user else "Assistant"
    background = "#173f36" if is_user else "#ffffff"
    foreground = "#ffffff" if is_user else "#1d302a"
    st.markdown(
        f"""
        <div style="background-color:{background}; color:{foreground}; opacity:1;
                    border:1px solid #79968a; border-radius:10px; padding:12px 16px;
                    margin:8px 0; overflow-wrap:anywhere;">
            <div style="font-size:.75rem; font-weight:700; margin-bottom:4px;
                        color:{foreground}; opacity:1;">{label}</div>
            <div style="white-space:pre-wrap; color:{foreground}; opacity:1;">
                {escape(content)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


@st.cache_resource(show_spinner="Lecture des documents et chargement des modèles...")
def load_rag():
    """Charge les rubriques de l'hôtel, leur index vectoriel et le modèle de réponse."""
    # Repère les fichiers PDF et arrête proprement si la documentation manque.
    pdf_paths = sorted(DATA_DIR.glob("*.pdf"))
    if not pdf_paths:
        raise FileNotFoundError(f"Aucun document PDF trouvé dans {DATA_DIR}")

    # Extrait chaque page et la convertit en une rubrique titrée.
    rows = []
    for pdf_path in pdf_paths:
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            # Garde la séparation des lignes telle que dans le notebook de référence.
            extracted = page.extract_text() or ""
            lines = extracted.split("\n")
            if not lines or not lines[0].strip():
                continue
            title = lines[0]
            body = "\n".join(lines[1:-1])
            rows.append({"source": pdf_path.name, "title": title, "text": body})

    # Assemble le titre et le texte de chaque page comme dans le notebook.
    pages = pd.DataFrame(rows)
    if pages.empty:
        raise ValueError("Aucun texte lisible n'a été extrait des documents PDF.")
    pages["section"] = "## " + pages["title"] + "\n\n" + pages["text"]

    # Charge le modèle multilingue et encode une fois toutes les rubriques.
    embedder = SentenceTransformer(EMBEDDING_MODEL)
    embeddings = embedder.encode(
        pages["section"].tolist(), normalize_embeddings=True, show_progress_bar=False
    )

    # Charge le petit modèle de génération déjà utilisé dans le notebook.
    generator = pipeline("text-generation", model=GENERATION_MODEL)
    return pages, embedder, embeddings, generator


# Affiche l'en-tête de la conversation.
st.markdown('<p class="eyebrow">RÉCEPTION · ANNECY</p>', unsafe_allow_html=True)
st.title("Hôtel Le Belvédère")
st.markdown(
    '<p class="intro">Bonjour. Posez votre question sur les chambres, les horaires ou les services de l’hôtel. '
    "Je m’appuie sur les documents de la réception et vous indique mes sources.</p>",
    unsafe_allow_html=True,
)

# Présente la fonction principale de l'application dans la barre latérale.
with st.sidebar:
    st.markdown("## Le Belvédère")
    st.caption("Assistant de la réception · Annecy")
    st.divider()
    st.markdown("**Documentation**")
    st.caption("Les réponses sont fondées sur les PDF fournis par l'hôtel.")
    if st.button("Effacer la conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# Charge les modèles une seule fois par session du serveur et affiche toute erreur utile.
try:
    pages, embedder, chunk_embeddings, generator = load_rag()
except Exception as error:
    st.error(f"Impossible de préparer l’assistant : {error}")
    st.stop()

# Affiche le nombre de rubriques documentaires déjà prêtes pour la recherche.
st.caption(f"{len(pages)} rubriques documentaires indexées")

# Initialise la mémoire de conversation lors de la première visite.
if "messages" not in st.session_state:
    st.session_state.messages = []

# Redessine les anciens messages après chaque interaction Streamlit.
for message in st.session_state.messages:
    render_chat_message(message["role"], message["content"])
    if message.get("sources"):
        with st.expander("Documents consultés"):
            for source in message["sources"]:
                st.caption(
                    f"{source['title']} · {source['source']} · similarité {source['score']:.2f}"
                )

# Propose quelques questions courantes pour rendre l'assistant testable dès l'ouverture.
st.markdown("**Questions fréquentes**")
example_columns = st.columns(3)
examples = [
    "À quelle heure commence le check-in ?",
    "Le wifi est-il gratuit ?",
    "Acceptez-vous les chiens ?",
]
for column, example in zip(example_columns, examples):
    if column.button(example, use_container_width=True):
        st.session_state.pending_question = example

# Lit la question écrite ou choisie parmi les suggestions.
typed_question = st.chat_input("Écrivez votre question à la réception…")
question = st.session_state.pop("pending_question", None) or typed_question

# Lance le RAG lorsqu'une question a été fournie.
if question:
    # Ajoute la question à la mémoire et l'affiche immédiatement.
    st.session_state.messages.append({"role": "user", "content": question})
    render_chat_message("user", question)

    # Récupère les deux rubriques les plus proches du sens de la question.
    question_embedding = embedder.encode([question], normalize_embeddings=True)[0]
    similarities = chunk_embeddings @ question_embedding
    top_indices = np.argsort(-similarities)[:2]
    retrieved = pages.iloc[top_indices].copy()
    retrieved["score"] = similarities[top_indices]
    context = "\n\n".join(retrieved["section"])

    # Repère les formulations qui dépendent explicitement d'un échange précédent.
    question_lower = question.casefold().strip()
    follow_up_starters = (
        "et ", "alors ", "dans ce cas", "ce tarif", "cette chambre", "cet hôtel",
        "ça ", "cela ", "il est", "elle est", "ils sont", "elles sont",
    )
    is_follow_up = question_lower.startswith(follow_up_starters)

    # Ne transmet que le dernier échange, et seulement pour une question de suivi.
    previous_messages = st.session_state.messages[:-1][-2:]
    history = "\n".join(
        f"{'Client' if message['role'] == 'user' else 'Assistant'} : {message['content']}"
        for message in previous_messages
    )
    history_text = (
        f"Historique précédent (uniquement pour comprendre un suivi) :\n{history}\n\n"
        if history and is_follow_up
        else ""
    )

    # Place le dernier échange avant les documents pour garder la réponse ancrée dans les sources.
    prompt = f"{ROLE}\n\n{history_text}{context}\n\nQuestion d'un client : {question}\n{INSTRUCTION}"

    # Génère la réponse à partir des sources fournies.
    with st.spinner("Je consulte les documents de l'hôtel…"):
        result = generator(
            [{"role": "user", "content": prompt}],
            max_new_tokens=40,
            do_sample=False,
            use_cache=True,
        )
        answer = result[0]["generated_text"][-1]["content"]
    render_chat_message("assistant", answer)
    with st.expander("Documents consultés"):
        for row in retrieved.itertuples():
            st.caption(f"{row.title} · {row.source} · similarité {row.score:.2f}")

    # Conserve la réponse et ses sources pour afficher l'historique ensuite.
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer,
            "sources": retrieved[["title", "source", "score"]].to_dict("records"),
        }
    )
