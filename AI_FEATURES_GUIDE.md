# 🤖 AI Question Generator Guide

## Overview

The AI Question Generator uses OpenAI's GPT-4o model to automatically create quiz questions from text content or images. This powerful feature can significantly speed up quiz creation while maintaining high quality.

## ✨ Features

### 🔧 System Prompt Management
- **Editable Prompts**: Customize how the AI generates questions
- **Version Control**: Track changes and revert to previous versions
- **Active Prompt**: Always use the latest approved prompt version

### 📝 Question Generation
- **Text Input**: Paste educational content to generate questions
- **Image Analysis**: Upload screenshots, diagrams, or educational images
- **Multiple Question Types**:
  - Multiple Choice (2-8 options)
  - Fill in the Blank (with multiple acceptable answers)

### 🎯 Advanced Configuration
- **Question Count**: Generate 1-20 questions per request
- **Difficulty Control**: Easy, Medium, Hard, or Mixed
- **Custom Instructions**: Guide the AI with specific requirements
- **Class Integration**: Questions automatically tagged to selected class

## 🚀 Setup Instructions

### 1. Install Requirements
```bash
pip install -r requirements.txt
```

### 2. Get OpenAI API Key
1. Go to [OpenAI Platform](https://platform.openai.com/api-keys)
2. Create a new API key
3. Copy the key

### 3. Set Environment Variable

**Windows (Command Prompt):**
```cmd
set OPENAI_API_KEY=your_api_key_here
```

**Windows (PowerShell):**
```powershell
$env:OPENAI_API_KEY='your_api_key_here'
```

**Linux/Mac:**
```bash
export OPENAI_API_KEY=your_api_key_here
```

**Or create a .env file:**
```
OPENAI_API_KEY=your_api_key_here
```

### 4. Run Setup Script (Optional)
```bash
python setup_ai.py
```

## 📋 Usage Guide

### Creating Your First AI-Generated Questions

1. **Navigate to AI Generator** (`/ai_generator`)
2. **Set Up System Prompt** (first time only):
   - Click "Create Default" if no prompt exists
   - Or customize the prompt for your needs
3. **Choose Input Method**:
   - **Text Tab**: Paste educational content
   - **Image Tab**: Upload educational images
4. **Configure Generation**:
   - Select target class
   - Set number of questions (1-20)
   - Choose question types
   - Set difficulty preference
   - Add custom instructions (optional)
5. **Generate**: Click "Generate Questions with AI"
6. **Review & Add**: Review generated questions and add to question bank

### System Prompt Customization

The system prompt controls how the AI generates questions. You can:

- **Edit Current Prompt**: Modify the active prompt
- **View History**: See all previous versions
- **Revert**: Activate any previous version
- **Version Control**: Each edit creates a new version

#### Example Customizations:
```
Focus on creating questions that test practical application rather than memorization.

For multiple choice questions, ensure distractors represent common misconceptions.

For fill-in-the-blank questions, accept common synonyms and abbreviations.
```

## 🎨 Question Types

### Multiple Choice
- **Automatic Validation**: Ensures correct answer is in options
- **Smart Distractors**: AI creates plausible wrong answers
- **Flexible Options**: 2-8 answer choices (4 default)
- **True/False Detection**: Auto-creates True/False for binary questions

### Fill in the Blank
- **Multiple Blanks**: Supports questions with multiple `_____` blanks
- **Case Insensitive**: Answers match regardless of capitalization
- **Multiple Acceptable Answers**: E.g., "apple", "apples", "red apple"
- **Smart Parsing**: AI detects blanks and provides variations

## 📊 Structured Output

AI generates questions in a structured format:

```json
{
  "question": "What is the capital of France?",
  "question_type": "multiple_choice",
  "options": ["London", "Berlin", "Paris", "Madrid"],
  "correct_answer": "Paris",
  "acceptable_answers": ["Paris"],
  "difficulty": "easy",
  "tags": ["geography", "capitals"],
  "explanation": "Paris has been the capital of France since..."
}
```

## 🔄 Integration with Question Bank

Generated questions can be:
- **Added Individually**: Review and add each question separately
- **Bulk Added**: Add all generated questions at once
- **Filtered**: Only add questions that meet your standards
- **Edited**: Modify before adding to the bank

## ⚙️ Best Practices

### For Text Input:
- Use well-structured educational content
- Include definitions, examples, and explanations
- Paste 2-3 paragraphs for best results
- Avoid very short or very long text blocks

### For Image Input:
- Use clear, high-resolution images
- Educational diagrams work best
- Include text, charts, or labeled diagrams
- Avoid blurry or handwritten content

### System Prompts:
- Test changes with small batches first
- Document what changes you made in descriptions
- Keep successful prompts for future reference
- Revert if quality decreases

## 🚨 Important Notes

### Cost Management:
- OpenAI charges per API call
- Monitor usage at [OpenAI Platform](https://platform.openai.com/usage)
- Generate in batches to optimize costs
- Review questions before bulk adding

### Quality Control:
- Always review AI-generated questions
- Check for accuracy and clarity
- Verify that correct answers are actually correct
- Ensure questions match your difficulty standards

### Privacy:
- Don't input sensitive or proprietary content
- Content is sent to OpenAI's servers
- Review OpenAI's data usage policies

## 🛠️ Troubleshooting

### "OpenAI API key not configured"
- Ensure OPENAI_API_KEY environment variable is set
- Restart the server after setting the key
- Run `python setup_ai.py` for setup help

### "AI response was not valid JSON"
- System prompt may need adjustment
- Try simpler content or fewer questions
- Check OpenAI service status

### Poor Question Quality
- Refine your system prompt
- Provide clearer custom instructions
- Use higher quality input content
- Adjust difficulty preference

### Image Analysis Issues
- Ensure images contain readable text or clear diagrams
- Use PNG or JPEG formats
- Keep file sizes reasonable (< 5MB)
- Provide context in custom instructions

## 🎯 Advanced Tips

1. **Prompt Engineering**: Experiment with different instruction styles
2. **Content Preparation**: Clean up text before input for better results
3. **Batch Processing**: Generate questions for multiple topics in sequence
4. **Quality Templates**: Create standard prompts for different subjects
5. **Review Workflows**: Establish consistent review processes

Happy question generating! 🚀
