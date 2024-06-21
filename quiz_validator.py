from typing import List
from fastapi import HTTPException

class Question:
    def __init__(self, question: str, options: List[str], correct_answer: str):
        self.question = question
        self.options = options
        self.correct_answer = correct_answer

class Quiz:
    def __init__(self, title: str, questions: List[Question]):
        self.title = title
        self.questions = questions

def validate_quiz(quiz: Quiz, existing_quiz_titles: List[str]):
    errors = []

    # Check for non-empty title
    if not quiz.title.strip():
        errors.append("Quiz title cannot be empty.")

    # Check for unique title
    if quiz.title in existing_quiz_titles:
        errors.append("Quiz title must be unique.")
    
    # Check for nonzero number of questions
    if len(quiz.questions) == 0:
        errors.append("Quiz must contain at least one question.")
    
    for index, question in enumerate(quiz.questions):
        # Check for non-empty question text
        if not question.question.strip():
            errors.append(f"Question {index + 1} text cannot be empty.")
        
        # Check for at least one option
        if len(question.options) == 0:
            errors.append(f"Question {index + 1} must have at least one answer option.")
        
        # Check if there's a correct answer
        if not question.correct_answer or question.correct_answer not in question.options:
            errors.append(f"Question {index + 1} must have a correct answer marked.")

    if errors:
        raise HTTPException(status_code=400, detail=" ".join(errors))
