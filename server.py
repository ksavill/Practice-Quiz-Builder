from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List
import os
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Text, select
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from quiz_validator import validate_quiz, Quiz, Question

app = FastAPI()

DATABASE_URL = "sqlite:///./quizzes.db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")

# Database models
class QuizDB(Base):
    __tablename__ = "quizzes"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, unique=True, index=True)

    questions = relationship("QuestionDB", back_populates="quiz", cascade="all, delete-orphan")


class QuestionDB(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True, index=True)
    question = Column(Text, nullable=False)
    options = Column(Text, nullable=False)  # Storing options as comma-separated string
    correct_answer = Column(String, nullable=False)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"))

    quiz = relationship("QuizDB", back_populates="questions")


Base.metadata.create_all(bind=engine)

class QuestionModel(BaseModel):
    question: str
    options: List[str]
    correct_answer: str

class QuizModel(BaseModel):
    title: str
    questions: List[QuestionModel]

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
@app.get("/home")
@app.get("/index")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/version")
async def version():
    return {"version": "24.25.3"}

@app.get("/styles")
async def get_styles():
    return FileResponse(os.path.join("static", "styles.css"))

@app.get("/favicon.ico")
async def favicon():
    return FileResponse(os.path.join("static", "favicon.ico"))

@app.get("/quiz_builder")
async def quiz_builder(request: Request):
    return templates.TemplateResponse("quiz_builder.html", {"request": request})

@app.get("/quiz_builder/{quiz_id}")
async def edit_quiz(request: Request, quiz_id: int, db: Session = Depends(get_db)):
    quiz = db.query(QuizDB).filter(QuizDB.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    quiz_data = {
        "id": quiz.id,
        "title": quiz.title,
        "questions": [
            {
                "question": q.question,
                "options": q.options.split(","),
                "correct_answer": q.correct_answer
            } for q in quiz.questions
        ]
    }
    
    return templates.TemplateResponse("quiz_builder.html", {"request": request, "quiz": quiz_data})

@app.get("/quiz_practice/{quiz_id}")
async def quiz_practice(request: Request, quiz_id: int, db: Session = Depends(get_db)):
    quiz = db.query(QuizDB).filter(QuizDB.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return templates.TemplateResponse("quiz_practice.html", {"request": request, "quiz": quiz})

@app.get("/api/quizzes")
async def get_all_quizzes(db: Session = Depends(get_db)):
    quizzes = db.query(QuizDB).all()
    return [{"title": quiz.title, "id": quiz.id} for quiz in quizzes]

@app.post("/api/quizzes")
async def create_quiz(quiz: QuizModel, db: Session = Depends(get_db)):
    existing_quiz_titles = [q.title for q in db.query(QuizDB).all()]
    
    questions = [Question(q.question, q.options, q.correct_answer) for q in quiz.questions]
    new_quiz = Quiz(quiz.title, questions)
    
    validate_quiz(new_quiz, existing_quiz_titles)
    
    db_quiz = QuizDB(title=quiz.title)
    db.add(db_quiz)
    db.commit()
    db.refresh(db_quiz)

    for q in quiz.questions:
        db_question = QuestionDB(
            question=q.question,
            options=",".join(q.options),
            correct_answer=q.correct_answer,
            quiz_id=db_quiz.id
        )
        db.add(db_question)
    db.commit()

    return {"quiz_id": db_quiz.id}

@app.get("/api/quizzes/{quiz_id}")
async def quiz_questions(quiz_id: int, db: Session = Depends(get_db)):
    quiz = db.query(QuizDB).filter(QuizDB.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    return {
        "id": quiz.id,
        "title": quiz.title,
        "questions": [
            {
                "question": q.question,
                "options": q.options.split(","),
                "correct_answer": q.correct_answer
            } for q in quiz.questions
        ]
    }

@app.put("/api/quizzes/{quiz_id}")
async def update_quiz(quiz_id: int, quiz: QuizModel, db: Session = Depends(get_db)):
    db_quiz = db.query(QuizDB).filter(QuizDB.id == quiz_id).first()
    if not db_quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    existing_quiz_titles = [q.title for q in db.query(QuizDB).all() if q.id != quiz_id]
    questions = [Question(q.question, q.options, q.correct_answer) for q in quiz.questions]
    updated_quiz = Quiz(quiz.title, questions)
    
    validate_quiz(updated_quiz, existing_quiz_titles)

    db_quiz.title = quiz.title
    db.query(QuestionDB).filter(QuestionDB.quiz_id == quiz_id).delete()

    for q in quiz.questions:
        db_question = QuestionDB(
            question=q.question,
            options=",".join(q.options),
            correct_answer=q.correct_answer,
            quiz_id=db_quiz.id
        )
        db.add(db_question)

    db.commit()
    return {"quiz_id": db_quiz.id}

@app.delete("/api/quizzes/{quiz_id}")
async def delete_quiz(quiz_id: int, db: Session = Depends(get_db)):
    quiz = db.query(QuizDB).filter(QuizDB.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    db.delete(quiz)
    db.commit()
    return {"detail": "Quiz deleted successfully"}



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
