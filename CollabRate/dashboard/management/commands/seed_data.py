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
        parser.add_argument(
            "--purge",
            action="store_true",
            help="Clear all existing data before seeding (users, courses, teams, allauth records)",
        )
        parser.add_argument(
            "--help-detailed",
            action="store_true",
            help="Show detailed help with examples and level configurations",
        )

    def handle(self, *args, **options):
        # Show detailed help if requested
        if options["help_detailed"]:
            self.show_detailed_help()
            return

        level = options["level"]
        semester = options["semester"]
        year = options["year"]
        seed = options["seed"]
        with_allauth = options["with_allauth"]
        fast_passwords = options["fast_passwords"]
        purge = options["purge"]

        if with_allauth and (EmailAddress is None or SocialAccount is None):
            raise CommandError(
                "django-allauth not available but --with-allauth was specified"
            )

        random.seed(seed)

        # Purge existing data if requested
        if purge:
            self.stdout.write(self.style.WARNING("Purging existing data..."))
            
            # Delete in reverse dependency order to avoid foreign key constraints
            if SocialAccount is not None:
                deleted_social = SocialAccount.objects.all().delete()
                self.stdout.write(f"Deleted {deleted_social[0]} SocialAccount records")
            
            if EmailAddress is not None:
                deleted_emails = EmailAddress.objects.all().delete()
                self.stdout.write(f"Deleted {deleted_emails[0]} EmailAddress records")
            
            # Delete teams first (they reference courses and users)
            deleted_teams = Team.objects.all().delete()
            self.stdout.write(f"Deleted {deleted_teams[0]} Team records")
            
            # Delete courses (they reference users)
            deleted_courses = Course.objects.all().delete()
            self.stdout.write(f"Deleted {deleted_courses[0]} Course records")
            
            # Delete all users
            User = get_user_model()
            deleted_users = User.objects.all().delete()
            self.stdout.write(f"Deleted {deleted_users[0]} User records")
            
            self.stdout.write(self.style.SUCCESS("Purge completed"))

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

    def show_detailed_help(self):
        """Display detailed help information with examples and configurations."""
        self.stdout.write(self.style.SUCCESS("CollabRate Data Seeding Command"))
        self.stdout.write("=" * 50)
        self.stdout.write("")
        
        self.stdout.write(self.style.WARNING("USAGE:"))
        self.stdout.write("  python manage.py seed_data [OPTIONS]")
        self.stdout.write("")
        
        self.stdout.write(self.style.WARNING("OPTIONS:"))
        self.stdout.write("  --level {1,2,3}           Data volume level (default: 1)")
        self.stdout.write("    Level 1: ~150 courses, 30-80 students, teams 4-8")
        self.stdout.write("    Level 2: ~700 courses, 30-80 students, teams 4-6") 
        self.stdout.write("    Level 3: ~2000 courses, 30-100 students, teams 4-6")
        self.stdout.write("")
        
        self.stdout.write("  --semester {Spring,Fall}  Target semester (default: Spring)")
        self.stdout.write("  --year YYYY              Target year (default: current year)")
        self.stdout.write("  --seed N                 Random seed for reproducibility (default: 42)")
        self.stdout.write("")
        
        self.stdout.write("  --with-allauth           Create EmailAddress and SocialAccount records")
        self.stdout.write("                          (simulates Google OAuth users)")
        self.stdout.write("  --fast-passwords         Use unusable passwords for speed")
        self.stdout.write("                          (users can only login via social auth)")
        self.stdout.write("  --purge                  Clear all existing data before seeding")
        self.stdout.write("")
        
        self.stdout.write(self.style.WARNING("EXAMPLES:"))
        self.stdout.write("  # Quick Level 1 test")
        self.stdout.write("  python manage.py seed_data --level 1 --fast-passwords")
        self.stdout.write("")
        
        self.stdout.write("  # Full Level 2 with allauth and purge")
        self.stdout.write("  python manage.py seed_data --level 2 --with-allauth --purge --fast-passwords")
        self.stdout.write("")
        
        self.stdout.write("  # Level 3 for stress testing")
        self.stdout.write("  python manage.py seed_data --level 3 --semester Fall --year 2025 --fast-passwords")
        self.stdout.write("")
        
        self.stdout.write(self.style.WARNING("PERFORMANCE NOTES:"))
        self.stdout.write("  - Use --fast-passwords for large datasets (Level 2/3)")
        self.stdout.write("  - --with-allauth adds extra time for social account creation")
        self.stdout.write("  - Level 1: ~1-3 minutes, Level 2: ~5-20 minutes, Level 3: ~20-60+ minutes")
        self.stdout.write("  - Progress updates shown every ~5% of courses")
        self.stdout.write("")
        
        self.stdout.write(self.style.WARNING("DATA GENERATED:"))
        self.stdout.write("  - CustomUser records (students and professors)")
        self.stdout.write("  - Course records with join codes and colors")
        self.stdout.write("  - Team records with student assignments")
        self.stdout.write("  - Optional: EmailAddress and SocialAccount records")
        self.stdout.write("")
        
        self.stdout.write(self.style.WARNING("DATABASE TABLES AFFECTED:"))
        self.stdout.write("  - accounts_customuser (users)")
        self.stdout.write("  - dashboard_course (courses)")
        self.stdout.write("  - course_team (teams)")
        self.stdout.write("  - course_team_students (team memberships)")
        self.stdout.write("  - dashboard_course_students (course enrollments)")
        if EmailAddress is not None:
            self.stdout.write("  - account_emailaddress (if --with-allauth)")
        if SocialAccount is not None:
            self.stdout.write("  - socialaccount_socialaccount (if --with-allauth)")
