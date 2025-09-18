import random
import string
from django.db import models
from accounts.models import CustomUser

def generate_join_code():
    # Generate a six (6) character alphanumeric code
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

class Course(models.Model):
    SEMESTER_CHOICES = [
        ('Spring', 'Spring'),
        ('Fall', 'Fall'),
    ]

    COLOR_CHOICES = [
        "#ff6b6b", "#4CAF50", "#3498db", "#f39c12", "#9b59b6",
        "#e74c3c", "#1abc9c", "#e67e22", "#2ecc71", "#8e44ad",
        "#c0392b", "#16a085", "#f1c40f", "#d35400", "#27ae60",
        "#2980b9", "#7f8c8d", "#bdc3c7", "#34495e"
    ]

    join_code = models.CharField(max_length=6, primary_key=True, unique=True, blank=True)
    code = models.CharField(max_length=20)
    title = models.CharField(max_length=100)
    student_count = models.IntegerField(default=0)
    semester = models.CharField(max_length=10, choices=SEMESTER_CHOICES)
    year = models.IntegerField()
    color = models.CharField(max_length=7, blank=True, null=True)  
    students = models.ManyToManyField(
        CustomUser,
        related_name="enrolled_courses",
        limit_choices_to={'user_type': CustomUser.STUDENT},
        blank=True
    )
    professor = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='courses',
        limit_choices_to={'user_type': CustomUser.PROFESSOR},
        null=True,
        blank=True
    )

    def save(self, *args, **kwargs):
        if not self.join_code:
            self.join_code = generate_join_code()
            while Course.objects.filter(join_code=self.join_code).exists():
                self.join_code = generate_join_code()
        if not self.color:
            self.color = random.choice(self.COLOR_CHOICES)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} - {self.title} ({self.semester} {self.year}) - {self.join_code}"
