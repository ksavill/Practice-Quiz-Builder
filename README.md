# Quiz Builder App

This is a simple web application for building and practicing quizzes. The app is built using FastAPI for the backend and Jinja2 for templating.

## Features

- Create new quizzes with a unique title and multiple questions.
- Edit existing quizzes.
- Delete quizzes.
- Practice quizzes and get feedback on answers.
- Import quizzes from a JSON file.
- Responsive and modern UI.

## Getting Started

### Prerequisites

- Python 3.7 or later

### Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/ksavill/Practice-Quiz-Builder.git
    cd quiz-builder-app
    ```

2. Create a virtual environment and activate it:
    ```sh
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3. Install the dependencies:
    ```sh
    pip install -r requirements.txt
    ```

### Running the App

1. Start the server:
    ```sh
    python server.py
    ```

2. Open your browser and go to [http://127.0.0.1:8000](http://127.0.0.1:8000) to access the app.

### API Endpoints

- **GET /**
  - **Description:** Home page.
  - **Response:** Renders the home page template.

- **GET /home**
  - **Description:** Alias for the home page.
  - **Response:** Renders the home page template.

- **GET /index**
  - **Description:** Alias for the home page.
  - **Response:** Renders the home page template.

- **GET /version**
  - **Description:** Get the current version of the app.
  - **Response:** JSON with the version number.

- **GET /styles**
  - **Description:** Retrieve the CSS stylesheet.
  - **Response:** Returns the `styles.css` file.

- **GET /favicon.ico**
  - **Description:** Retrieve the favicon.
  - **Response:** Returns the `favicon.ico` file.

- **GET /quiz_builder**
  - **Description:** Create a new quiz.
  - **Response:** Renders the quiz builder template for creating a new quiz.

- **GET /quiz_builder/{quiz_id}**
  - **Description:** Edit an existing quiz.
  - **Response:** Renders the quiz builder template for editing the specified quiz.

- **GET /quiz_practice/{quiz_id}**
  - **Description:** Practice a quiz.
  - **Response:** Renders the quiz practice template for the specified quiz.

- **GET /api/quizzes**
  - **Description:** Retrieve all quizzes.
  - **Response:** JSON array with all quizzes.

- **GET /api/quizzes/{quiz_id}**
  - **Description:** Retrieve a specific quiz by ID.
  - **Response:** JSON with the quiz details.

- **POST /api/quizzes**
  - **Description:** Create a new quiz.
  - **Request Body:** JSON with the quiz details.
  - **Response:** JSON with the ID of the created quiz.

- **PUT /api/quizzes/{quiz_id}**
  - **Description:** Update an existing quiz.
  - **Request Body:** JSON with the updated quiz details.
  - **Response:** JSON with the ID of the updated quiz.

- **DELETE /api/quizzes/{quiz_id}**
  - **Description:** Delete a quiz by ID.
  - **Response:** JSON with a success message.

### Project Structure

```
quiz-builder-app/
├── templates/
│ ├── index.html
│ ├── quiz_builder.html
| └── quiz_practice.html
├── static/
│ └── styles.css
├── server.py
├── quiz_validator.py
├── requirements.txt
└── README.md
```
