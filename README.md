# CollabRate

A Django-powered peer‑review and assessment platform that allows instructors to create, publish, and manage Likert‑scale and open‑ended feedback forms for courses and teams.

---

## Table of Contents

1. [Features](#features)
2. [Tech Stack](#tech-stack)
3. [Getting Started](#getting-started)
   - [Prerequisites](#prerequisites)
   - [Installation](#installation)
   - [Running the App](#running-the-app)
4. [Database Migrations](#database-migrations)
5. [Models](#models)
6. [Apps & Pages](#apps--pages)
7. [Contributing](#contributing)
8. [License](#license)

---

## Features

- Instructor-driven creation of feedback forms (Likert and open‑ended).
- Self‑evaluation or peer‑evaluation modes.
- Team‑scoped forms and responses.
- Google OAuth Single Sign‑On with automatic role assignment (Student vs. Professor).
- Deadline management (date + time) with timezone handling.
- CRUD for courses, forms, teams, and responses.

---

## Tech Stack

- **Backend:** Python 3.10, Django 5.1.7
- **Database:** PostgreSQL (via Django ORM)
- **Auth:** Google OAuth 2.0
- **Frontend:** Bootstrap, custom CSS, Choices.js, date/time pickers
- **Deployment:** TBD

---

## Getting Started

### Prerequisites

- Python 3.10+

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/<username>/collabrate.git
   cd collabrate
   ```

2. **Create & activate a virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate     # macOS/Linux
   .\.venv\\Scripts\\activate  # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   Copy `.env.example` to `.env` and fill in:
   - `SECRET_KEY`
   - `DATABASE_URL`
   - `GOOGLE_OAUTH_CLIENT_ID`
   - `GOOGLE_OAUTH_CLIENT_SECRET`

### Running the App

1. **Apply migrations**
   ```bash
   python manage.py migrate
   ```

2. **Create a superuser**
   ```bash
   python manage.py createsuperuser
   ```

3. **Collect static files**
   ```bash
   python manage.py collectstatic
   ```

4. **Start the development server**
   ```bash
   python manage.py runserver
   ```

Visit `http://127.0.0.1:8000/` and log in via Google.

---

## Database Migrations

Whenever you modify models:
```bash
python manage.py makemigrations
python manage.py migrate
```

---

## Models

- **Course**
  - `join_code`, `name`, `color_1`, `color_2`, etc.
- **CustomUser** (extends `AbstractUser`)
  - `user_type` (Student or Professor)
- **CourseForm**
  - `course`, `name`, `due_date`, `due_time`, `self_evaluate`, `teams`, etc.
- **LikertQuestion** & **OpenEndedQuestion**
  - Linked to `CourseForm` templates.
- **LikertResponse** & **OpenEndedResponse**
  - Composite PK: (`evaluator`, `evaluee`, `question`)
- **Team**
  - `name`, `course`, ManyToMany to `CustomUser` students

---

## Apps & Pages

- **Courses**
  - List all courses with join codes
  - Course detail: overview, teams, forms
- **Forms**
  - Create / Edit / Publish / Release forms
  - Configure Likert & open‑ended questions
- **Answer Form**
  - Students submit responses (self or peer)
  - Auto‑update existing responses if resubmitted
- **Responses Dashboard**
  - Professors view aggregated Likert scores and open‑ended feedback
- **Team Management**
  - Create / Delete teams, assign students
- **Admin**
  - Full CRUD via Django admin

---

## Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/foo`)
3. Commit your changes (`git commit -am 'Add foo'`)
4. Push to the branch (`git push origin feature/foo`)
5. Open a Pull Request

---

## License

MIT License © 2025

