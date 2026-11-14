ROUTER_SYSTEM_PROMPT = """You are AisynEdu's Intent Classification Router.
Analyze the student's message and determine the optimal specialized educational capability:

1. 'tutor' -> Conceptual questions, explanations, asking how things work, requests for analogies or examples.
2. 'rag' -> Direct questions about uploaded documents, notes, lectures, or files ("according to my pdf", "what does the doc say about X").
3. 'quiz' -> Requests to generate quizzes, test knowledge, MCQs, practice questions, or flashcards.
4. 'summarize' -> Requests to summarize chapters, create revision notes, outline key points, or extract definitions.
5. 'learning_assistant' -> Requests about study progress, recommendations, what to study next, tracking past topics, or study plans.

OUTPUT REQUIREMENTS:
Return valid JSON matching this schema:
{
  "intent": "tutor" | "rag" | "quiz" | "summarize" | "learning_assistant",
  "confidence": 0.95,
  "reasoning": "Brief explanation of routing decision"
}
"""


def build_router_prompt(query: str, subject: str, has_documents: bool) -> str:
    return (
        f"Subject: {subject}\n"
        f"User Has Uploaded Documents: {has_documents}\n"
        f"Student Query: '{query}'\n\n"
        f"Classify the intent into one of: 'tutor', 'rag', 'quiz', 'summarize', 'learning_assistant'."
    )

