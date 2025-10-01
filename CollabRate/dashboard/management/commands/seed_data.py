import math
import random
import uuid
from datetime import datetime
import time

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction

from dashboard.models import Course
from course.models import Team

try:
    from allauth.account.models import EmailAddress
    from allauth.socialaccount.models import SocialAccount
except Exception:  # pragma: no cover - allauth optional at seed time
    EmailAddress = None
    SocialAccount = None


LEVEL_CONFIG = {
    1: {
        "courses_per_semester": 150,
        "students_min": 30,
        "students_max": 80,
        "team_min": 4,
        "team_max": 8,
    },
    2: {
        "courses_per_semester": 700,
        "students_min": 30,
        "students_max": 80,
        "team_min": 4,
        "team_max": 6,
    },
    3: {
        "courses_per_semester": 2000,
        "students_min": 30,
        "students_max": 100,
        "team_min": 4,
        "team_max": 6,
    },
}


def chunk_list(items, chunk_size):
    for i in range(0, len(items), chunk_size):
        yield items[i : i + chunk_size]


class Command(BaseCommand):
    help = (
        "Seed database with sample data: users (students/professors), courses, teams.\n"
        "Usage: python manage.py seed_data --level 1 --semester Spring --year 2025"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--level",
            type=int,
            choices=[1, 2, 3],
            default=1,
            help="Load level 1/2/3 data volume",
        )
        parser.add_argument(
            "--semester",
            type=str,
            choices=["Spring", "Fall"],
            default="Spring",
            help="Target semester",
        )
        parser.add_argument(
            "--year",
            type=int,
            default=datetime.utcnow().year,
            help="Target year",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=42,
            help="Random seed for reproducibility",
        )
        parser.add_argument(
            "--with-allauth",
            action="store_true",
            help="Create EmailAddress and SocialAccount rows for users",
        )
        parser.add_argument(
            "--fast-passwords",
            action="store_true",
            help="Assign unusable passwords (no hashing) to speed up large runs",
        )

    def handle(self, *args, **options):
        level = options["level"]
        semester = options["semester"]
        year = options["year"]
        seed = options["seed"]
        with_allauth = options["with_allauth"]
        fast_passwords = options["fast_passwords"]

        if with_allauth and (EmailAddress is None or SocialAccount is None):
            raise CommandError(
                "django-allauth not available but --with-allauth was specified"
            )

        random.seed(seed)

        config = LEVEL_CONFIG[level]
        courses_target = config["courses_per_semester"]
        students_min = config["students_min"]
        students_max = config["students_max"]
        team_min = config["team_min"]
        team_max = config["team_max"]

        self.stdout.write(
            self.style.NOTICE(
                f"Seeding level {level}: ~{courses_target} courses in {semester} {year}"
            )
        )

        User = get_user_model()

        created_courses = []
        created_professors = []
        created_students = []
        created_teams = []
        created_email_addresses = []
        created_social_accounts = []

        username_counter = int(random.random() * 1000)
        email_domain = "student.example.edu"
        prof_domain = "faculty.example.edu"

        def next_username(prefix: str) -> str:
            nonlocal username_counter
            username_counter += 1
            return f"{prefix}{username_counter}"

        def make_email(local: str, domain: str) -> str:
            return f"{local}@{domain}"

        # We create objects inside a transaction for speed and atomicity
        with transaction.atomic():
            start_time = time.time()
            progress_every = max(1, courses_target // 20)  # ~5% increments
            for course_index in range(courses_target):
                course_code = f"CS{100 + (course_index % 400)}"
                course_title = f"Course {course_code} Section {course_index % 5}"

                # Professor
                prof_username = next_username("prof_")
                prof_email = make_email(prof_username, prof_domain)
                professor = User(
                    username=prof_username,
                    email=prof_email,
                    user_type=getattr(User, "PROFESSOR", "professor"),
                )
                if fast_passwords:
                    professor.set_unusable_password()
                else:
                    professor.set_password("Passw0rd!")
                professor.save()
                created_professors.append(professor)

                # Course
                course = Course(
                    code=course_code,
                    title=course_title,
                    semester=semester,
                    year=year,
                    professor=professor,
                )
                course.save()
                created_courses.append(course)

                # Students for this course
                num_students = random.randint(students_min, students_max)
                students_for_course = []
                for _ in range(num_students):
                    stu_username = next_username("student_")
                    stu_email = make_email(stu_username, email_domain)
                    student = User(
                        username=stu_username,
                        email=stu_email,
                        user_type=getattr(User, "STUDENT", "student"),
                    )
                    if fast_passwords:
                        student.set_unusable_password()
                    else:
                        student.set_password("Passw0rd!")
                    student.save()
                    students_for_course.append(student)
                    created_students.append(student)

                # Enroll students
                course.students.add(*students_for_course)
                course.student_count = len(students_for_course)
                course.save(update_fields=["student_count"])

                # Teams: choose a team size in range and partition students
                preferred_team_size = random.randint(team_min, team_max)
                random.shuffle(students_for_course)
                teams_needed = max(1, math.ceil(len(students_for_course) / preferred_team_size))

                # Distribute students as evenly as possible
                for team_num in range(teams_needed):
                    team = Team(name=f"Team {team_num + 1}", course=course)
                    team.save()
                    created_teams.append(team)

                # Assign students to teams round-robin
                for idx, student in enumerate(students_for_course):
                    team = created_teams[-teams_needed + (idx % teams_needed)]
                    team.students.add(student)

                # Optionally create allauth records
                if with_allauth:
                    for u in [professor] + students_for_course:
                        if EmailAddress is not None:
                            created_email_addresses.append(
                                EmailAddress(user=u, email=u.email, verified=True, primary=True)
                            )
                        if SocialAccount is not None:
                            created_social_accounts.append(
                                SocialAccount(
                                    user=u,
                                    provider="google",
                                    uid=f"google-oauth2|{uuid.uuid4()}",
                                    extra_data={
                                        "email": u.email,
                                        "name": u.username.replace("_", " "),
                                    },
                                )
                            )

                # Periodic progress update
                if (course_index + 1) % progress_every == 0 or (course_index + 1) == courses_target:
                    elapsed = time.time() - start_time
                    pct = ((course_index + 1) / courses_target) * 100.0
                    self.stdout.write(
                        self.style.NOTICE(
                            f"Created courses: {course_index + 1}/{courses_target} ({pct:0.1f}%) in {elapsed:0.1f}s"
                        )
                    )

            # Bulk create allauth rows in chunks to avoid large INSERTs
            if with_allauth:
                if EmailAddress is not None and created_email_addresses:
                    total = len(created_email_addresses)
                    done = 0
                    for batch in chunk_list(created_email_addresses, 1000):
                        EmailAddress.objects.bulk_create(batch, ignore_conflicts=True)
                        done += len(batch)
                        self.stdout.write(self.style.NOTICE(f"EmailAddress bulk: {done}/{total}"))
                if SocialAccount is not None and created_social_accounts:
                    total = len(created_social_accounts)
                    done = 0
                    for batch in chunk_list(created_social_accounts, 1000):
                        SocialAccount.objects.bulk_create(batch, ignore_conflicts=True)
                        done += len(batch)
                        self.stdout.write(self.style.NOTICE(f"SocialAccount bulk: {done}/{total}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {len(created_courses)} courses, "
                f"{len(created_professors)} professors, {len(created_students)} students, "
                f"{len(created_teams)} teams"
            )
        )


