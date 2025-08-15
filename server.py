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
class ClassDB(Base):
    __tablename__ = "classes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)

    quizzes = relationship("QuizDB", back_populates="class_ref", cascade="all, delete-orphan")


class QuizDB(Base):
    __tablename__ = "quizzes"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)

    class_ref = relationship("ClassDB", back_populates="quizzes")
    questions = relationship("QuestionDB", back_populates="quiz", cascade="all, delete-orphan")


class QuestionDB(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True, index=True)
    question = Column(Text, nullable=False)
    question_type = Column(String, nullable=False, default="multiple_choice")
    options = Column(Text, nullable=False)  # Storing options as comma-separated string
    correct_answer = Column(String, nullable=False)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"))

    quiz = relationship("QuizDB", back_populates="questions")


class QuestionBankDB(Base):
    __tablename__ = "question_bank"
    id = Column(Integer, primary_key=True, index=True)
    question = Column(Text, nullable=False)
    question_type = Column(String, nullable=False, default="multiple_choice")
    options = Column(Text, nullable=False)  # Storing options as comma-separated string
    correct_answer = Column(String, nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    difficulty = Column(String, nullable=True)  # easy, medium, hard
    tags = Column(Text, nullable=True)  # comma-separated tags
    created_at = Column(String, nullable=True)  # timestamp

    class_ref = relationship("ClassDB")


class SystemPromptDB(Base):
    __tablename__ = "system_prompts"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # e.g., "question_generation", "image_analysis"
    prompt_text = Column(Text, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    is_active = Column(String, nullable=False, default="false")  # "true" or "false"
    created_at = Column(String, nullable=False)
    created_by = Column(String, nullable=True, default="system")
    description = Column(Text, nullable=True)


class AIConfigDB(Base):
    __tablename__ = "ai_config"
    id = Column(Integer, primary_key=True, index=True)
    config_key = Column(String, nullable=False, unique=True)  # e.g., "default_model", "api_provider"
    config_value = Column(Text, nullable=False)
    config_type = Column(String, nullable=False, default="string")  # "string", "integer", "boolean", "json"
    description = Column(Text, nullable=True)
    updated_at = Column(String, nullable=False)
    updated_by = Column(String, nullable=True, default="system")


Base.metadata.create_all(bind=engine)

# Global AI status tracking
AI_AVAILABLE = False
OPENAI_API_KEY_STATUS = {"available": False, "error": None}

# Initialize default system prompt if none exists
def initialize_default_prompts():
    db = SessionLocal()
    try:
        # Check if any system prompts exist
        existing_prompts = db.query(SystemPromptDB).count()
        
        if existing_prompts == 0:
            from datetime import datetime
            
            starter_prompt = """You are an expert question generator that converts existing questions and answers into structured quiz format.

**Primary Task**: Transform provided content (text or images) into well-formatted multiple choice or fill-in-the-blank questions.

**Input Expectations**:
- Users will paste existing questions with answers (often from textbooks, worksheets, or study materials)
- Images may contain questions from screenshots, photos of textbooks, or handwritten notes
- Content may be in various formats: informal notes, formal test questions, bullet points, etc.

**Output Requirements**:
1. **Preserve Original Intent**: Keep the core meaning and difficulty of source questions
2. **Improve Clarity**: Clean up wording while maintaining accuracy
3. **Add Context**: Provide explanations when helpful for understanding
4. **Smart Question Types**:
   - Use "multiple_choice" for questions that can have 4+ distinct options
   - Use "fill_blank" for questions better suited to direct answers or when only 1-2 clear options exist
   - Convert True/False to multiple_choice with "True" and "False" options
   - For fill_blank questions, use {blank} tokens to mark where answers should go

**Answer Generation Guidelines**:
- **Multiple Choice**: Create 4 plausible options unless the question is naturally True/False
- **Fill-in-Blank**: Use {blank} tokens in questions, provide multiple acceptable variations (case-insensitive, plural forms, synonyms)
- **Case Handling**: For fill-in-blank answers, use lowercase unless proper nouns or scientific notation require specific case
- **Multiple Blanks**: For questions with multiple blanks, use {blank} for each: "The {blank} orbits the {blank}"
- **Difficulty**: Match the original question's complexity level
- **Explanations**: Add brief, helpful explanations that clarify why the answer is correct

**Quality Standards**:
- All distractors (wrong answers) should be plausible but clearly incorrect
- Avoid "all of the above" or "none of the above" unless essential
- Ensure questions test understanding, not just memorization when possible
- Keep language clear and accessible

**Output exactly this JSON structure**:
```json
{
  "questions": [
    {
      "question": "Clear, well-formatted question text",
      "question_type": "multiple_choice" or "fill_blank",
      "options": ["option1", "option2", "option3", "option4"],
      "correct_answer": "exact_match_from_options",
      "acceptable_answers": ["answer1", "answer2"], // Only for fill_blank
      "difficulty": "easy", "medium", or "hard",
      "tags": ["topic1", "topic2"],
      "explanation": "Brief explanation of why this answer is correct"
    }
  ]
}
```

**Remember**: You are converting existing content, not creating entirely new questions. Focus on faithful transformation with quality improvements."""
            
            default_prompt = SystemPromptDB(
                name="question_generation",
                prompt_text=starter_prompt,
                version=1,
                is_active="true",
                created_at=datetime.now().isoformat(),
                created_by="system",
                description="Default starter prompt for converting existing questions and answers into structured format"
            )
            
            db.add(default_prompt)
            db.commit()
            print("✅ Default system prompt initialized")
        else:
            print(f"ℹ️ Found {existing_prompts} existing system prompts")
            
    except Exception as e:
        print(f"❌ Error initializing default prompts: {e}")
    finally:
        db.close()

# Initialize AI configuration and detection
def initialize_ai_config():
    """Initialize AI configuration and detect OpenAI API key availability"""
    global AI_AVAILABLE, OPENAI_API_KEY_STATUS
    
    db = SessionLocal()
    try:
        from datetime import datetime
        
        # Check for OpenAI API key
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key and api_key.strip():
            OPENAI_API_KEY_STATUS = {"available": True, "error": None}
            AI_AVAILABLE = True
            print("✅ OpenAI API key detected - AI features enabled")
        else:
            OPENAI_API_KEY_STATUS = {"available": False, "error": "OPENAI_API_KEY environment variable not set"}
            AI_AVAILABLE = False
            print("❌ OpenAI API key not found - AI features disabled")
            print("💡 Set OPENAI_API_KEY environment variable to enable AI features")
        
        # Initialize default AI configuration if not exists
        default_configs = [
            {
                "config_key": "default_model",
                "config_value": "gpt-5",
                "config_type": "string",
                "description": "Default AI model for question generation"
            },
            {
                "config_key": "max_questions_per_request",
                "config_value": "20",
                "config_type": "integer",
                "description": "Maximum number of questions that can be generated in a single request"
            },

            {
                "config_key": "enable_image_analysis",
                "config_value": "true",
                "config_type": "boolean",
                "description": "Enable image analysis for question generation"
            }
        ]
        
        for config in default_configs:
            existing = db.query(AIConfigDB).filter(AIConfigDB.config_key == config["config_key"]).first()
            if not existing:
                new_config = AIConfigDB(
                    config_key=config["config_key"],
                    config_value=config["config_value"],
                    config_type=config["config_type"],
                    description=config["description"],
                    updated_at=datetime.now().isoformat(),
                    updated_by="system"
                )
                db.add(new_config)
        
        db.commit()
        print("✅ AI configuration initialized")
        
    except Exception as e:
        print(f"❌ Error initializing AI configuration: {e}")
        OPENAI_API_KEY_STATUS = {"available": False, "error": f"Initialization error: {str(e)}"}
        AI_AVAILABLE = False
    finally:
        db.close()

# Initialize on startup
initialize_default_prompts()
initialize_ai_config()

class QuestionModel(BaseModel):
    question: str
    question_type: str = "multiple_choice"
    options: List[str]
    correct_answer: str

class QuizModel(BaseModel):
    title: str
    class_id: int
    questions: List[QuestionModel]

class ClassModel(BaseModel):
    name: str
    description: str = ""

class QuestionBankModel(BaseModel):
    question: str
    question_type: str = "multiple_choice"
    options: List[str]
    correct_answer: str
    class_id: int
    difficulty: str = "medium"
    tags: str = ""

class SystemPromptModel(BaseModel):
    name: str
    prompt_text: str
    description: str = ""

class AIConfigModel(BaseModel):
    config_key: str
    config_value: str
    config_type: str = "string"
    description: str = ""

class AIGenerationRequest(BaseModel):
    text_content: str = ""
    image_data: str = ""  # base64 encoded image
    class_id: int
    num_questions: int = 5
    min_options: int = 4
    question_types: List[str] = ["multiple_choice", "fill_blank"]
    difficulty_preference: str = "medium"
    custom_instructions: str = ""

class AIGeneratedQuestion(BaseModel):
    question: str
    question_type: str
    options: List[str]
    correct_answer: str
    acceptable_answers: List[str] = []  # For fill_blank - multiple valid answers
    difficulty: str
    tags: List[str]
    explanation: str = ""
    blank_positions: List[int] = []  # For fill_blank - positions of blanks in question

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
    return {"version": "25.33.1"}

@app.get("/styles")
async def get_styles():
    return FileResponse(os.path.join("static", "styles.css"))

@app.get("/favicon.ico")
async def favicon():
    return FileResponse(
        os.path.join("static", "favicon.ico"),
        media_type="image/x-icon",
        headers={"Cache-Control": "public, max-age=31536000"}
    )

@app.get("/class_management")
async def class_management(request: Request):
    return templates.TemplateResponse("class_management.html", {"request": request})

@app.get("/question_bank")
async def question_bank_management(request: Request):
    return templates.TemplateResponse("question_bank.html", {"request": request})

@app.get("/ai_generator")
async def ai_question_generator(request: Request):
    return templates.TemplateResponse("ai_generator.html", {"request": request})

@app.get("/ai_config")
async def ai_configuration(request: Request):
    return templates.TemplateResponse("ai_config.html", {"request": request})

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
        "class_id": quiz.class_id,
        "questions": [
            {
                "question": q.question,
                "question_type": q.question_type,
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

# Class CRUD endpoints
@app.get("/api/classes")
async def get_all_classes(db: Session = Depends(get_db)):
    classes = db.query(ClassDB).all()
    return [{"id": cls.id, "name": cls.name, "description": cls.description, "quiz_count": len(cls.quizzes)} for cls in classes]

@app.post("/api/classes")
async def create_class(class_data: ClassModel, db: Session = Depends(get_db)):
    # Check if class name already exists
    existing_class = db.query(ClassDB).filter(ClassDB.name == class_data.name).first()
    if existing_class:
        raise HTTPException(status_code=400, detail="Class name must be unique")
    
    db_class = ClassDB(name=class_data.name, description=class_data.description)
    db.add(db_class)
    db.commit()
    db.refresh(db_class)
    return {"class_id": db_class.id}

@app.get("/api/classes/{class_id}")
async def get_class(class_id: int, db: Session = Depends(get_db)):
    class_obj = db.query(ClassDB).filter(ClassDB.id == class_id).first()
    if not class_obj:
        raise HTTPException(status_code=404, detail="Class not found")
    return {
        "id": class_obj.id,
        "name": class_obj.name,
        "description": class_obj.description,
        "quizzes": [{"id": quiz.id, "title": quiz.title} for quiz in class_obj.quizzes]
    }

@app.put("/api/classes/{class_id}")
async def update_class(class_id: int, class_data: ClassModel, db: Session = Depends(get_db)):
    db_class = db.query(ClassDB).filter(ClassDB.id == class_id).first()
    if not db_class:
        raise HTTPException(status_code=404, detail="Class not found")
    
    # Check if new name conflicts with existing class (excluding current class)
    existing_class = db.query(ClassDB).filter(ClassDB.name == class_data.name, ClassDB.id != class_id).first()
    if existing_class:
        raise HTTPException(status_code=400, detail="Class name must be unique")
    
    db_class.name = class_data.name
    db_class.description = class_data.description
    db.commit()
    return {"class_id": db_class.id}

@app.delete("/api/classes/{class_id}")
async def delete_class(class_id: int, db: Session = Depends(get_db)):
    db_class = db.query(ClassDB).filter(ClassDB.id == class_id).first()
    if not db_class:
        raise HTTPException(status_code=404, detail="Class not found")
    
    # Check if class has quizzes
    if len(db_class.quizzes) > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete class '{db_class.name}' because it contains {len(db_class.quizzes)} quiz(es). Please delete or reassign the quizzes first."
        )
    
    db.delete(db_class)
    db.commit()
    return {"detail": "Class deleted successfully"}

# Question Bank CRUD endpoints
@app.get("/api/question-bank")
async def get_question_bank(class_id: int = None, db: Session = Depends(get_db)):
    if class_id:
        questions = db.query(QuestionBankDB).filter(QuestionBankDB.class_id == class_id).all()
    else:
        questions = db.query(QuestionBankDB).all()
    
    return [{
        "id": q.id,
        "question": q.question,
        "question_type": q.question_type,
        "options": q.options.split(","),
        "correct_answer": q.correct_answer,
        "class_id": q.class_id,
        "class_name": q.class_ref.name,
        "difficulty": q.difficulty,
        "tags": q.tags.split(",") if q.tags else [],
        "created_at": q.created_at
    } for q in questions]

@app.post("/api/question-bank")
async def add_to_question_bank(question: QuestionBankModel, db: Session = Depends(get_db)):
    # Check if class exists
    class_obj = db.query(ClassDB).filter(ClassDB.id == question.class_id).first()
    if not class_obj:
        raise HTTPException(status_code=400, detail="Invalid class_id")
    
    from datetime import datetime
    
    db_question = QuestionBankDB(
        question=question.question,
        question_type=question.question_type,
        options=",".join(question.options),
        correct_answer=question.correct_answer,
        class_id=question.class_id,
        difficulty=question.difficulty,
        tags=question.tags,
        created_at=datetime.now().isoformat()
    )
    db.add(db_question)
    db.commit()
    db.refresh(db_question)
    return {"question_id": db_question.id}

@app.get("/api/question-bank/{question_id}")
async def get_question_bank_item(question_id: int, db: Session = Depends(get_db)):
    question = db.query(QuestionBankDB).filter(QuestionBankDB.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    return {
        "id": question.id,
        "question": question.question,
        "question_type": question.question_type,
        "options": question.options.split(","),
        "correct_answer": question.correct_answer,
        "class_id": question.class_id,
        "difficulty": question.difficulty,
        "tags": question.tags.split(",") if question.tags else []
    }

@app.put("/api/question-bank/{question_id}")
async def update_question_bank_item(question_id: int, question: QuestionBankModel, db: Session = Depends(get_db)):
    db_question = db.query(QuestionBankDB).filter(QuestionBankDB.id == question_id).first()
    if not db_question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    # Check if class exists
    class_obj = db.query(ClassDB).filter(ClassDB.id == question.class_id).first()
    if not class_obj:
        raise HTTPException(status_code=400, detail="Invalid class_id")
    
    db_question.question = question.question
    db_question.question_type = question.question_type
    db_question.options = ",".join(question.options)
    db_question.correct_answer = question.correct_answer
    db_question.class_id = question.class_id
    db_question.difficulty = question.difficulty
    db_question.tags = question.tags
    
    db.commit()
    return {"question_id": db_question.id}

@app.delete("/api/question-bank/{question_id}")
async def delete_question_bank_item(question_id: int, db: Session = Depends(get_db)):
    question = db.query(QuestionBankDB).filter(QuestionBankDB.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    db.delete(question)
    db.commit()
    return {"detail": "Question deleted successfully"}

@app.post("/api/question-bank/generate-quiz")
async def generate_quiz_from_bank(
    class_id: int, 
    num_questions: int = 10, 
    difficulty: str = None, 
    question_types: List[str] = None, 
    db: Session = Depends(get_db)
):
    # Build query filters
    query = db.query(QuestionBankDB).filter(QuestionBankDB.class_id == class_id)
    
    if difficulty:
        query = query.filter(QuestionBankDB.difficulty == difficulty)
    
    if question_types:
        query = query.filter(QuestionBankDB.question_type.in_(question_types))
    
    available_questions = query.all()
    
    if len(available_questions) < num_questions:
        raise HTTPException(
            status_code=400, 
            detail=f"Not enough questions available. Found {len(available_questions)}, requested {num_questions}"
        )
    
    import random
    selected_questions = random.sample(available_questions, num_questions)
    
    return [{
        "question": q.question,
        "question_type": q.question_type,
        "options": q.options.split(","),
        "correct_answer": q.correct_answer
    } for q in selected_questions]

# System Prompt Management endpoints
@app.get("/api/system-prompts")
async def get_system_prompts(name: str = None, db: Session = Depends(get_db)):
    if name:
        prompts = db.query(SystemPromptDB).filter(SystemPromptDB.name == name).order_by(SystemPromptDB.version.desc()).all()
    else:
        prompts = db.query(SystemPromptDB).order_by(SystemPromptDB.name, SystemPromptDB.version.desc()).all()
    
    return [{
        "id": p.id,
        "name": p.name,
        "prompt_text": p.prompt_text,
        "version": p.version,
        "is_active": p.is_active == "true",
        "created_at": p.created_at,
        "created_by": p.created_by,
        "description": p.description
    } for p in prompts]

@app.get("/api/system-prompts/active/{prompt_name}")
async def get_active_prompt(prompt_name: str, db: Session = Depends(get_db)):
    prompt = db.query(SystemPromptDB).filter(
        SystemPromptDB.name == prompt_name,
        SystemPromptDB.is_active == "true"
    ).first()
    
    if not prompt:
        raise HTTPException(status_code=404, detail="No active prompt found")
    
    return {
        "id": prompt.id,
        "name": prompt.name,
        "prompt_text": prompt.prompt_text,
        "version": prompt.version,
        "description": prompt.description
    }

@app.post("/api/system-prompts")
async def create_or_update_prompt(prompt: SystemPromptModel, db: Session = Depends(get_db)):
    from datetime import datetime
    
    # Get the highest version for this prompt name
    latest = db.query(SystemPromptDB).filter(SystemPromptDB.name == prompt.name).order_by(SystemPromptDB.version.desc()).first()
    next_version = (latest.version + 1) if latest else 1
    
    # Deactivate all previous versions
    db.query(SystemPromptDB).filter(SystemPromptDB.name == prompt.name).update({"is_active": "false"})
    
    # Create new version
    new_prompt = SystemPromptDB(
        name=prompt.name,
        prompt_text=prompt.prompt_text,
        version=next_version,
        is_active="true",
        created_at=datetime.now().isoformat(),
        created_by="user",
        description=prompt.description
    )
    
    db.add(new_prompt)
    db.commit()
    db.refresh(new_prompt)
    
    return {"prompt_id": new_prompt.id, "version": new_prompt.version}

@app.post("/api/system-prompts/{prompt_id}/activate")
async def activate_prompt_version(prompt_id: int, db: Session = Depends(get_db)):
    prompt = db.query(SystemPromptDB).filter(SystemPromptDB.id == prompt_id).first()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    # Deactivate all versions of this prompt name
    db.query(SystemPromptDB).filter(SystemPromptDB.name == prompt.name).update({"is_active": "false"})
    
    # Activate the selected version
    prompt.is_active = "true"
    db.commit()
    
    return {"detail": f"Activated version {prompt.version} of {prompt.name}"}

@app.delete("/api/system-prompts/{prompt_id}")
async def delete_prompt_version(prompt_id: int, db: Session = Depends(get_db)):
    prompt = db.query(SystemPromptDB).filter(SystemPromptDB.id == prompt_id).first()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    if prompt.is_active == "true":
        raise HTTPException(status_code=400, detail="Cannot delete active prompt version")
    
    db.delete(prompt)
    db.commit()
    return {"detail": "Prompt version deleted successfully"}

# AI Configuration Management endpoints
@app.get("/api/ai/status")
async def get_ai_status():
    """Get the current AI availability status and configuration"""
    return {
        "ai_available": AI_AVAILABLE,
        "openai_status": OPENAI_API_KEY_STATUS,
        "features": {
            "question_generation": AI_AVAILABLE,
            "image_analysis": AI_AVAILABLE
        }
    }

@app.get("/api/ai/config")
async def get_ai_config(db: Session = Depends(get_db)):
    """Get all AI configuration settings"""
    configs = db.query(AIConfigDB).all()
    return [{
        "id": config.id,
        "config_key": config.config_key,
        "config_value": config.config_value,
        "config_type": config.config_type,
        "description": config.description,
        "updated_at": config.updated_at,
        "updated_by": config.updated_by
    } for config in configs]

@app.get("/api/ai/config/{config_key}")
async def get_ai_config_value(config_key: str, db: Session = Depends(get_db)):
    """Get a specific AI configuration value"""
    config = db.query(AIConfigDB).filter(AIConfigDB.config_key == config_key).first()
    if not config:
        raise HTTPException(status_code=404, detail="Configuration key not found")
    
    # Parse the value based on type
    parsed_value = config.config_value
    if config.config_type == "integer":
        parsed_value = int(config.config_value)
    elif config.config_type == "float":
        parsed_value = float(config.config_value)
    elif config.config_type == "boolean":
        parsed_value = config.config_value.lower() == "true"
    elif config.config_type == "json":
        import json
        parsed_value = json.loads(config.config_value)
    
    return {
        "config_key": config.config_key,
        "value": parsed_value,
        "raw_value": config.config_value,
        "config_type": config.config_type,
        "description": config.description
    }

@app.put("/api/ai/config/{config_key}")
async def update_ai_config(config_key: str, config_data: AIConfigModel, db: Session = Depends(get_db)):
    """Update an AI configuration setting"""
    from datetime import datetime
    
    config = db.query(AIConfigDB).filter(AIConfigDB.config_key == config_key).first()
    if not config:
        raise HTTPException(status_code=404, detail="Configuration key not found")
    
    # Validate the value based on type
    try:
        if config_data.config_type == "integer":
            int(config_data.config_value)
        elif config_data.config_type == "float":
            float(config_data.config_value)
        elif config_data.config_type == "boolean":
            if config_data.config_value.lower() not in ["true", "false"]:
                raise ValueError("Boolean values must be 'true' or 'false'")
        elif config_data.config_type == "json":
            import json
            json.loads(config_data.config_value)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid value for type {config_data.config_type}: {str(e)}")
    
    config.config_value = config_data.config_value
    config.config_type = config_data.config_type
    config.description = config_data.description
    config.updated_at = datetime.now().isoformat()
    config.updated_by = "user"
    
    db.commit()
    
    return {"detail": f"Configuration '{config_key}' updated successfully"}

@app.post("/api/ai/config")
async def create_ai_config(config_data: AIConfigModel, db: Session = Depends(get_db)):
    """Create a new AI configuration setting"""
    from datetime import datetime
    
    # Check if config key already exists
    existing = db.query(AIConfigDB).filter(AIConfigDB.config_key == config_data.config_key).first()
    if existing:
        raise HTTPException(status_code=400, detail="Configuration key already exists")
    
    # Validate the value based on type
    try:
        if config_data.config_type == "integer":
            int(config_data.config_value)
        elif config_data.config_type == "float":
            float(config_data.config_value)
        elif config_data.config_type == "boolean":
            if config_data.config_value.lower() not in ["true", "false"]:
                raise ValueError("Boolean values must be 'true' or 'false'")
        elif config_data.config_type == "json":
            import json
            json.loads(config_data.config_value)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid value for type {config_data.config_type}: {str(e)}")
    
    new_config = AIConfigDB(
        config_key=config_data.config_key,
        config_value=config_data.config_value,
        config_type=config_data.config_type,
        description=config_data.description,
        updated_at=datetime.now().isoformat(),
        updated_by="user"
    )
    
    db.add(new_config)
    db.commit()
    db.refresh(new_config)
    
    return {"config_id": new_config.id, "detail": f"Configuration '{config_data.config_key}' created successfully"}

@app.delete("/api/ai/config/{config_key}")
async def delete_ai_config(config_key: str, db: Session = Depends(get_db)):
    """Delete an AI configuration setting"""
    config = db.query(AIConfigDB).filter(AIConfigDB.config_key == config_key).first()
    if not config:
        raise HTTPException(status_code=404, detail="Configuration key not found")
    
    db.delete(config)
    db.commit()
    
    return {"detail": f"Configuration '{config_key}' deleted successfully"}

# AI Question Generation endpoint
@app.post("/api/ai/generate-questions")
async def generate_questions_with_ai(request: AIGenerationRequest, db: Session = Depends(get_db)):
    import openai
    import json
    import os
    import base64
    from typing import Dict, Any
    
    # Check if AI is available
    if not AI_AVAILABLE:
        raise HTTPException(
            status_code=503, 
            detail=f"AI features are not available: {OPENAI_API_KEY_STATUS.get('error', 'Unknown error')}"
        )
    
    # Get OpenAI API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")
    
    # Initialize OpenAI client
    client = openai.OpenAI(api_key=api_key)
    
    # Get active system prompt
    system_prompt = db.query(SystemPromptDB).filter(
        SystemPromptDB.name == "question_generation",
        SystemPromptDB.is_active == "true"
    ).first()
    
    if not system_prompt:
        raise HTTPException(status_code=404, detail="No active system prompt found for question generation")
    
    # Validate class exists
    class_obj = db.query(ClassDB).filter(ClassDB.id == request.class_id).first()
    if not class_obj:
        raise HTTPException(status_code=400, detail="Invalid class_id")
    
    # Build the user prompt
    user_content = []
    
    if request.text_content:
        user_content.append({
            "type": "text",
            "text": f"""Please generate {request.num_questions} questions from this content:

Content: {request.text_content}

Parameters:
- Question types: {', '.join(request.question_types)}
- Minimum options for multiple choice: {request.min_options}
- Difficulty preference: {request.difficulty_preference}
- Custom instructions: {request.custom_instructions if request.custom_instructions else 'None'}

Return a valid JSON array with the exact structure specified in the system prompt."""
        })
    
    if request.image_data:
        user_content.append({
            "type": "text", 
            "text": f"""Please analyze this image and generate {request.num_questions} educational questions based on its content.

Parameters:
- Question types: {', '.join(request.question_types)}
- Minimum options for multiple choice: {request.min_options}
- Difficulty preference: {request.difficulty_preference}
- Custom instructions: {request.custom_instructions if request.custom_instructions else 'None'}

Return a valid JSON array with the exact structure specified in the system prompt."""
        })
        user_content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{request.image_data}"
            }
        })
    
    try:
        # Get configured model
        model_config = db.query(AIConfigDB).filter(AIConfigDB.config_key == "default_model").first()
        ai_model = model_config.config_value if model_config else "gpt-4o"
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model=ai_model,  # Use configured model
            messages=[
                {"role": "system", "content": system_prompt.prompt_text},
                {"role": "user", "content": user_content}
            ]
        )
        
        # Parse the response
        ai_response = response.choices[0].message.content
        
        # Try to extract JSON from the response
        try:
            # Look for JSON array in the response
            import re
            json_match = re.search(r'\[.*\]', ai_response, re.DOTALL)
            if json_match:
                questions_data = json.loads(json_match.group())
            else:
                questions_data = json.loads(ai_response)
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail="AI response was not valid JSON")
        
        # Process and validate the generated questions
        processed_questions = []
        for q_data in questions_data:
            # Handle fill_blank questions specially
            if q_data.get("question_type") == "fill_blank":
                # Process fill-in-the-blank questions
                question_text = q_data.get("question", "")
                
                # Find blank positions (assuming _____ or [blank] format)
                blank_positions = []
                blank_markers = ["_____", "[blank]", "____", "___"]
                for i, marker in enumerate(blank_markers):
                    if marker in question_text:
                        blank_positions = [pos for pos, char in enumerate(question_text) if question_text[pos:pos+len(marker)] == marker]
                        break
                
                # Get acceptable answers (could be multiple variations)
                correct_answer = q_data.get("correct_answer", "")
                acceptable_answers = q_data.get("acceptable_answers", [correct_answer])
                
                if not acceptable_answers or not any(acceptable_answers):
                    acceptable_answers = [correct_answer]
                
                processed_question = {
                    "question": question_text,
                    "question_type": "fill_blank",
                    "options": acceptable_answers,  # Store all acceptable answers as options
                    "correct_answer": correct_answer,
                    "acceptable_answers": acceptable_answers,
                    "difficulty": q_data.get("difficulty", request.difficulty_preference),
                    "tags": ",".join(q_data.get("tags", [])),
                    "explanation": q_data.get("explanation", ""),
                    "blank_positions": blank_positions
                }
            else:
                # Handle multiple choice questions
                options = q_data.get("options", [])
                correct_answer = q_data.get("correct_answer", "")
                
                # Validate that correct answer is in options
                if correct_answer not in options:
                    if options:
                        correct_answer = options[0]  # Fallback to first option
                    else:
                        continue  # Skip invalid questions
                
                processed_question = {
                    "question": q_data.get("question", ""),
                    "question_type": q_data.get("question_type", "multiple_choice"),
                    "options": options,
                    "correct_answer": correct_answer,
                    "difficulty": q_data.get("difficulty", request.difficulty_preference),
                    "tags": ",".join(q_data.get("tags", [])),
                    "explanation": q_data.get("explanation", "")
                }
            
            processed_questions.append(processed_question)
        
        return {
            "generated_questions": processed_questions,
            "total_generated": len(processed_questions),
            "ai_model_used": ai_model,
            "prompt_version": system_prompt.version
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI generation failed: {str(e)}")

# Bulk add AI generated questions to question bank
@app.post("/api/ai/add-to-bank")
async def add_ai_questions_to_bank(request_data: dict, db: Session = Depends(get_db)):
    from datetime import datetime
    
    questions = request_data.get("questions", [])
    class_id = request_data.get("class_id")
    
    if not class_id:
        raise HTTPException(status_code=400, detail="class_id is required")
    
    # Validate class exists
    class_obj = db.query(ClassDB).filter(ClassDB.id == class_id).first()
    if not class_obj:
        raise HTTPException(status_code=400, detail="Invalid class_id")
    
    added_questions = []
    
    for q_data in questions:
        try:
            # Handle different question types
            if q_data.get("question_type") == "fill_blank":
                options_str = "|".join(q_data.get("acceptable_answers", [q_data.get("correct_answer", "")]))
            else:
                options_str = ",".join(q_data.get("options", []))
            
            db_question = QuestionBankDB(
                question=q_data.get("question", ""),
                question_type=q_data.get("question_type", "multiple_choice"),
                options=options_str,
                correct_answer=q_data.get("correct_answer", ""),
                class_id=class_id,
                difficulty=q_data.get("difficulty", "medium"),
                tags=q_data.get("tags", ""),
                created_at=datetime.now().isoformat()
            )
            
            db.add(db_question)
            added_questions.append(q_data.get("question", "Untitled Question"))
            
        except Exception as e:
            print(f"Error adding question: {e}")
            continue
    
    db.commit()
    
    return {
        "questions_added": len(added_questions),
        "added_questions": added_questions
    }

# AI Answer Explanation endpoint
@app.post("/api/ai/explain-answer")
async def explain_answer(request_data: dict, db: Session = Depends(get_db)):
    """Generate AI explanation for a quiz question answer"""
    
    # Check if AI is available
    if not AI_AVAILABLE:
        raise HTTPException(
            status_code=503, 
            detail=f"AI features are not available: {OPENAI_API_KEY_STATUS.get('error', 'Unknown error')}"
        )
    
    # Get OpenAI API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="OpenAI API key not configured")
    
    # Extract request data
    question_text = request_data.get("question", "")
    question_type = request_data.get("question_type", "multiple_choice")
    correct_answer = request_data.get("correct_answer", "")
    all_options = request_data.get("options", [])
    user_answer = request_data.get("user_answer", "")
    
    if not question_text or not correct_answer:
        raise HTTPException(status_code=400, detail="Question and correct answer are required")
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        # Create explanation prompt
        if question_type == "fill_blank":
            explanation_prompt = f"""You are an educational assistant. Provide a clear, concise explanation for this fill-in-the-blank question. Keep your response to 2-3 sentences maximum.

Question: {question_text}
Correct Answer: {correct_answer}
All Acceptable Answers: {', '.join(all_options)}
Student's Answer: {user_answer if user_answer else 'Not provided'}

Please explain:
1. Why the correct answer is right
2. The key concept or knowledge being tested
3. If the student's answer was wrong, briefly explain why
4. Keep the explanation educational and encouraging

Be concise - respond with 2-3 sentences only."""

        else:  # multiple_choice
            explanation_prompt = f"""You are an educational assistant. Provide a clear, concise explanation for this multiple choice question. Keep your response to 2-4 sentences maximum.

Question: {question_text}
Options: {', '.join(all_options)}
Correct Answer: {correct_answer}
Student's Answer: {user_answer if user_answer else 'Not provided'}

Please explain:
1. Why the correct answer is right
2. Why the other options are incorrect (briefly)
3. The key concept or knowledge being tested
4. If the student's answer was wrong, briefly explain the misconception
5. Keep the explanation educational and encouraging

Be concise - respond with 2-4 sentences only."""

        # Get configured model
        model_config = db.query(AIConfigDB).filter(AIConfigDB.config_key == "default_model").first()
        ai_model = model_config.config_value if model_config else "gpt-4o"
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model=ai_model,
            messages=[
                {"role": "user", "content": explanation_prompt}
            ]
        )
        
        explanation = response.choices[0].message.content.strip()
        
        return {
            "explanation": explanation,
            "question": question_text,
            "correct_answer": correct_answer,
            "user_answer": user_answer,
            "ai_model_used": ai_model
        }
        
    except Exception as e:
        print(f"Error generating explanation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate explanation: {str(e)}")

# JSON Template endpoint
@app.get("/api/question-template")
async def get_question_template():
    """Returns a JSON template with examples of different question types"""
    template = {
        "template_info": {
            "version": "1.0",
            "description": "Question template for AI generation or manual creation",
            "supported_types": ["multiple_choice", "fill_blank"],
            "instructions": "Replace the example questions with your own content. Ensure all required fields are present."
        },
        "questions": [
            {
                "question": "What is the capital of France?",
                "question_type": "multiple_choice",
                "options": ["London", "Berlin", "Paris", "Madrid"],
                "correct_answer": "Paris",
                "difficulty": "easy",
                "tags": ["geography", "capitals", "europe"],
                "explanation": "Paris has been the capital of France since the 6th century and is the country's largest city."
            },
            {
                "question": "The process by which plants convert sunlight into energy is called {blank}.",
                "question_type": "fill_blank",
                "options": ["photosynthesis"],
                "correct_answer": "photosynthesis",
                "acceptable_answers": ["photosynthesis", "photosynthetic process"],
                "difficulty": "medium",
                "tags": ["biology", "plants", "energy"],
                "explanation": "Photosynthesis is the process plants use to convert light energy into chemical energy."
            },
            {
                "question": "Which of the following is NOT a primary color?",
                "question_type": "multiple_choice",
                "options": ["Red", "Green", "Blue", "Yellow"],
                "correct_answer": "Yellow",
                "difficulty": "easy",
                "tags": ["art", "color theory"],
                "explanation": "The primary colors in light are red, green, and blue (RGB). Yellow is a secondary color."
            },
            {
                "question": "The formula for calculating the area of a circle is {blank} where r is the radius.",
                "question_type": "fill_blank",
                "options": ["πr²", "π × r²", "pi × r²", "pi × r^2"],
                "correct_answer": "πr²",
                "acceptable_answers": ["πr²", "π × r²", "pi × r²", "pi × r^2", "π*r²", "pi*r²"],
                "difficulty": "medium",
                "tags": ["mathematics", "geometry", "formulas"],
                "explanation": "The area of a circle is calculated using A = πr², where π (pi) is approximately 3.14159."
            }
        ]
    }
    
    return template

# Quiz Export endpoint
@app.get("/api/quizzes/{quiz_id}/export")
async def export_quiz_as_json(quiz_id: int, db: Session = Depends(get_db)):
    """Export a quiz as JSON that matches the import schema"""
    from datetime import datetime
    
    # Get the quiz with all its questions
    quiz = db.query(QuizDB).filter(QuizDB.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    # Convert quiz questions to the JSON schema format
    exported_questions = []
    
    for question in quiz.questions:
        # Parse options (stored as comma-separated string)
        options = [opt.strip() for opt in question.options.split(',') if opt.strip()]
        
        # Build the question object
        question_obj = {
            "question": question.question,
            "question_type": question.question_type,
            "options": options,
            "correct_answer": question.correct_answer,
            "difficulty": "medium",  # Default difficulty
            "tags": [],  # Default empty tags
            "explanation": ""  # Default empty explanation
        }
        
        # For fill_blank questions, add acceptable_answers and normalize case
        if question.question_type == "fill_blank":
            # Normalize options to lowercase for consistency
            normalized_options = [opt.lower().strip() for opt in options if opt and opt.strip()]
            normalized_correct = question.correct_answer.lower().strip() if question.correct_answer else ""
            
            # Update the question object with normalized values
            question_obj["options"] = normalized_options
            question_obj["correct_answer"] = normalized_correct
            question_obj["acceptable_answers"] = normalized_options
            
            # Calculate blank positions
            blank_positions = []
            question_text = question.question
            start = 0
            while True:
                pos = question_text.find("{blank}", start)
                if pos == -1:
                    break
                blank_positions.append(pos)
                start = pos + 1
            
            if blank_positions:
                question_obj["blank_positions"] = blank_positions
        
        exported_questions.append(question_obj)
    
    # Build the complete export structure
    export_data = {
        "export_info": {
            "quiz_id": quiz.id,
            "quiz_title": quiz.title,
            "class_name": quiz.class_ref.name,
            "class_id": quiz.class_id,
            "exported_at": datetime.now().isoformat(),
            "total_questions": len(exported_questions),
            "question_types": list(set(q["question_type"] for q in exported_questions))
        },
        "questions": exported_questions
    }
    
    return export_data

# JSON Import validation endpoint
@app.post("/api/validate-json-questions")
async def validate_json_questions(request_data: dict):
    """Validates JSON question format and returns parsed questions with validation results"""
    
    try:
        questions_data = request_data.get("questions", [])
        if not questions_data:
            raise HTTPException(status_code=400, detail="No questions provided")
        
        validated_questions = []
        errors = []
        
        for i, q_data in enumerate(questions_data):
            question_errors = []
            
            # Required fields validation
            required_fields = ["question", "question_type", "options", "correct_answer"]
            for field in required_fields:
                if field not in q_data or not q_data[field]:
                    question_errors.append(f"Missing required field: {field}")
            
            # Question type validation
            if q_data.get("question_type") not in ["multiple_choice", "fill_blank"]:
                question_errors.append("Invalid question_type. Must be 'multiple_choice' or 'fill_blank'")
            
            # Options validation
            options = q_data.get("options", [])
            if not isinstance(options, list) or len(options) == 0:
                question_errors.append("Options must be a non-empty array")
            
            # Correct answer validation
            correct_answer = q_data.get("correct_answer", "")
            if q_data.get("question_type") == "multiple_choice":
                if correct_answer not in options:
                    question_errors.append("Correct answer must be one of the provided options")
            
            # Fill-in-blank specific validation
            if q_data.get("question_type") == "fill_blank":
                question_text = q_data.get("question", "")
                
                # Check for {blank} tokens
                blank_count = question_text.count("{blank}")
                if blank_count == 0:
                    question_errors.append("Fill-in-blank questions must contain at least one {blank} token")
                
                # Normalize case for fill-in-blank answers
                acceptable_answers = q_data.get("acceptable_answers", [correct_answer])
                if acceptable_answers:
                    # Convert all to lowercase for comparison
                    acceptable_answers_lower = [ans.lower().strip() for ans in acceptable_answers if ans and ans.strip()]
                    correct_answer_lower = correct_answer.lower().strip() if correct_answer else ""
                    
                    if not acceptable_answers_lower or correct_answer_lower not in acceptable_answers_lower:
                        question_errors.append("Correct answer must be in acceptable_answers for fill_blank questions")
                else:
                    question_errors.append("Fill-in-blank questions must have acceptable_answers")
                
                # Validate blank positions for multiple blanks
                if blank_count > 1:
                    blank_positions = q_data.get("blank_positions", [])
                    if len(blank_positions) != blank_count:
                        question_errors.append(f"Question has {blank_count} blanks but blank_positions array has {len(blank_positions)} items")
            
            # Process blank positions for fill_blank questions
            blank_positions = []
            if q_data.get("question_type") == "fill_blank":
                question_text = q_data.get("question", "")
                # Find all positions of {blank} tokens
                start = 0
                while True:
                    pos = question_text.find("{blank}", start)
                    if pos == -1:
                        break
                    blank_positions.append(pos)
                    start = pos + 1
            
            # Normalize acceptable answers for fill-in-blank
            acceptable_answers = q_data.get("acceptable_answers", [correct_answer] if q_data.get("question_type") == "fill_blank" else [])
            if q_data.get("question_type") == "fill_blank" and acceptable_answers:
                # Normalize to lowercase and remove empty strings
                acceptable_answers = [ans.lower().strip() for ans in acceptable_answers if ans and ans.strip()]
                # Also normalize the correct answer
                correct_answer = correct_answer.lower().strip() if correct_answer else ""
                # Update options to match acceptable answers for fill_blank
                options = acceptable_answers
            
            # Build validated question
            validated_question = {
                "question": q_data.get("question", ""),
                "question_type": q_data.get("question_type", "multiple_choice"),
                "options": options,
                "correct_answer": correct_answer,
                "acceptable_answers": acceptable_answers,
                "difficulty": q_data.get("difficulty", "medium"),
                "tags": q_data.get("tags", []),
                "explanation": q_data.get("explanation", ""),
                "blank_positions": blank_positions,
                "validation_errors": question_errors,
                "is_valid": len(question_errors) == 0
            }
            
            validated_questions.append(validated_question)
            
            if question_errors:
                errors.append(f"Question {i+1}: {'; '.join(question_errors)}")
        
        return {
            "is_valid": len(errors) == 0,
            "total_questions": len(questions_data),
            "valid_questions": len([q for q in validated_questions if q["is_valid"]]),
            "validation_errors": errors,
            "questions": validated_questions
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"JSON validation failed: {str(e)}")

@app.get("/api/quizzes")
async def get_all_quizzes(db: Session = Depends(get_db)):
    quizzes = db.query(QuizDB).all()
    return [{"title": quiz.title, "id": quiz.id, "class_id": quiz.class_id, "class_name": quiz.class_ref.name} for quiz in quizzes]

@app.get("/api/classes/{class_id}/quizzes")
async def get_quizzes_by_class(class_id: int, db: Session = Depends(get_db)):
    class_obj = db.query(ClassDB).filter(ClassDB.id == class_id).first()
    if not class_obj:
        raise HTTPException(status_code=404, detail="Class not found")
    
    return [{"title": quiz.title, "id": quiz.id} for quiz in class_obj.quizzes]

@app.post("/api/quizzes")
async def create_quiz(quiz: QuizModel, db: Session = Depends(get_db)):
    # Check if class exists
    class_obj = db.query(ClassDB).filter(ClassDB.id == quiz.class_id).first()
    if not class_obj:
        raise HTTPException(status_code=400, detail="Invalid class_id")
    
    # Check for unique quiz titles within the same class
    existing_quiz_titles = [q.title for q in db.query(QuizDB).filter(QuizDB.class_id == quiz.class_id).all()]
    
    questions = [Question(q.question, q.options, q.correct_answer) for q in quiz.questions]
    new_quiz = Quiz(quiz.title, questions)
    
    validate_quiz(new_quiz, existing_quiz_titles)
    
    db_quiz = QuizDB(title=quiz.title, class_id=quiz.class_id)
    db.add(db_quiz)
    db.commit()
    db.refresh(db_quiz)

    for q in quiz.questions:
        db_question = QuestionDB(
            question=q.question,
            question_type=q.question_type,
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
                "question_type": q.question_type,
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
    
    # Check if class exists
    class_obj = db.query(ClassDB).filter(ClassDB.id == quiz.class_id).first()
    if not class_obj:
        raise HTTPException(status_code=400, detail="Invalid class_id")
    
    # Check for unique quiz titles within the same class (excluding current quiz)
    existing_quiz_titles = [q.title for q in db.query(QuizDB).filter(QuizDB.class_id == quiz.class_id, QuizDB.id != quiz_id).all()]
    questions = [Question(q.question, q.options, q.correct_answer) for q in quiz.questions]
    updated_quiz = Quiz(quiz.title, questions)
    
    validate_quiz(updated_quiz, existing_quiz_titles)

    db_quiz.title = quiz.title
    db_quiz.class_id = quiz.class_id
    db.query(QuestionDB).filter(QuestionDB.quiz_id == quiz_id).delete()

    for q in quiz.questions:
        db_question = QuestionDB(
            question=q.question,
            question_type=q.question_type,
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
    uvicorn.run(app, host="0.0.0.0", port=8086)
