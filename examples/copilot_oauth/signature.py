import dspy


class QA(dspy.Signature):
    """Answer the question. Think step by step, then produce a concise answer."""

    question: str = dspy.InputField(desc="Question to answer")
    answer: str = dspy.OutputField(desc="Concise answer")
