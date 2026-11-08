def print_chat(question, answer, sources=None):
    """Pretty-print one question/answer exchange, with its sources if provided.

    Arguments:
    question -- the user's question, as a string
    answer -- the generated answer, as a string
    sources -- optional DataFrame of retrieved chunks, with columns title and score
    """
    print(f"Client   : {question}")
    if sources is not None:
        titles = ", ".join(f"{row.title} ({row.score:.2f})" for row in sources.itertuples())
        print(f"Sources  : {titles}")
    print(f"Assistant: {answer}")
    print("-" * 80)
