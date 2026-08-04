def build_mcq_prompt(context: str, count: int, difficulty: str | None) -> str:
    diff = f"Difficulty level: {difficulty}." if difficulty else "Mix of easy, medium, and hard."
    return (
        f"You are a quiz generator for students. Generate exactly {count} multiple-choice questions "
        f"based ONLY on the provided context. Do not use any information outside the context.\n\n"
        f"Context:\n{context}\n\n"
        f"Requirements:\n"
        f"- Each question must have exactly 4 options labeled A, B, C, D\n"
        f"- Exactly one option must be correct\n"
        f"- Include a brief explanation for the correct answer\n"
        f"- {diff}\n\n"
        f"Return a JSON array with this exact structure:\n"
        f'[{{"question":"...","options":{{"A":"...","B":"...","C":"...","D":"..."}},'
        f'"correct":"A","explanation":"...","difficulty":"easy"}}]\n\n'
        f"Return ONLY the JSON array, no other text."
    )


def build_tf_prompt(context: str, count: int, difficulty: str | None) -> str:
    diff = f"Difficulty level: {difficulty}." if difficulty else "Mix of easy, medium, and hard."
    return (
        f"Generate exactly {count} true/false statements based ONLY on the provided context.\n\n"
        f"Context:\n{context}\n\n"
        f"- {diff}\n\n"
        f"Return a JSON array:\n"
        f'[{{"question":"Statement text","correct":true,"explanation":"...","difficulty":"easy"}}]\n\n'
        f"Return ONLY the JSON array, no other text."
    )


def build_short_prompt(context: str, count: int, difficulty: str | None) -> str:
    diff = f"Difficulty level: {difficulty}." if difficulty else "Mix of easy, medium, and hard."
    return (
        f"Generate exactly {count} short-answer questions based ONLY on the provided context.\n\n"
        f"Context:\n{context}\n\n"
        f"- {diff}\n\n"
        f"Return a JSON array:\n"
        f'[{{"question":"...","model_answer":"Expected answer in 1-3 sentences",'
        f'"key_terms":["term1","term2"],"difficulty":"easy"}}]\n\n'
        f"Return ONLY the JSON array, no other text."
    )
