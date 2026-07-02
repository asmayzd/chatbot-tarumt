from src.data_science.chatbot_engine import ChatbotEngine


class ChatbotEvaluator:
    def __init__(self, chatbot: ChatbotEngine):
        self.chatbot = chatbot

    def run_basic_tests(self):
        test_questions = [
            "What are the total sales?",
            "What is the total profit?",
            "Which country has the highest sales?",
            "What is the most profitable country?",
            "What is the most profitable category?",
            "What is the best selling category?",
            "What is the average shipping delay?",
        ]

        results = []

        for question in test_questions:
            answer = self.chatbot.answer(question)

            results.append({
                "question": question,
                "answer": answer,
                "status": "passed" if "cannot answer" not in answer.lower() else "failed"
            })

        return results