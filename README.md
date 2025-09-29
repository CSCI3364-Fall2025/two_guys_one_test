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

4. **Obtain Google OAuth2 Credentials**

 - Go to **[Google Cloud Console](https://console.cloud.google.com/)**.  
 - Create a new project (or select an existing one).  
 - Navigate to **APIs & Services → OAuth consent screen → Credentials**.  
 - Click on the **Create Credentials** Dropdown and Select OAuth client ID.
 - Select **Web application** as the application type.  
 - Under **Authorized redirect URIs**, add:
   - For Local Development: http://127.0.0.1:8000/accounts/google/login/callback/
   - For Hosting a Web Application Online: {domain}/accounts/google/login/callback/
 - Save and copy the **Client ID** and **Client Secret**.  

---

5. **Create Superuser & Register Credentials**

 - **Create a Django superuser**
```bash
python manage.py createsuperuser
```
 - **Log in to the Django admin site (http://127.0.0.1:8000/admin/) with your superuser account.**

 - Go to Social Applications → Add Social Application.

 - Choose Google as the provider.

 - Paste your Client ID and Client Secret from Google Cloud.

 - Assign it to the correct site (e.g., localhost).


### Running the App

1. **Apply migrations**
   ```bash
   python manage.py migrate
   ```

2. **Collect static files**
   ```bash
   python manage.py collectstatic
   ```

3. **Start the development server**
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

## Test Scripts

To run test scripts, naviagate to **CollabRate** directory and input,
   ```bash
   pytest
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


