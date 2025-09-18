from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    STUDENT = 'student'
    PROFESSOR = 'professor'

    USER_TYPE_OPTIONS = [
        (STUDENT, 'Student'),
        (PROFESSOR, 'Professor'),
    ]

    # Define a User Type to Distinguish Between Professors and Students
    # Blank by Default
    user_type = models.CharField(
        max_length=10,
        choices=USER_TYPE_OPTIONS,
        blank=True,
    )

    def __str__(self):
        return f"{self.username} ({self.user_type or 'Not Set'})"