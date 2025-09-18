import random
import string
from django.db import models
from django.core.validators import RegexValidator
from dashboard.models import Course
from accounts.models import CustomUser
from datetime import date
from django.utils import timezone

hex_validator = RegexValidator(
    regex=r'^#(?:[0-9a-fA-F]{3}){1,2}$',
    message='Enter a valid hex color code, e.g., #FFF or #FFFFFF.'
)

class CourseForm(models.Model):

    DRAFT = 'draft'
    PUBLISHED = 'published'
    RELEASED = 'released'
    
    FORM_STATE_CHOICES = [
        (DRAFT, 'Draft'),
        (PUBLISHED, 'Published'),
        (RELEASED, 'Released'),
    ]

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="course_forms")
    name = models.CharField(max_length=255, default="Untitled Form")
    due_datetime = models.DateTimeField(
        null=True,
        blank=True,
        default=timezone.now,
    )
    num_likert = models.PositiveIntegerField(default=3)
    num_open_ended = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    self_evaluate = models.BooleanField(default=False)
    teams = models.ManyToManyField('Team', related_name="course_forms", blank=True)
    color_1 = models.CharField(max_length=7, validators=[hex_validator], default="#872729")
    color_2 = models.CharField(max_length=7, validators=[hex_validator], default="#C44B4B")
    color_3 = models.CharField(max_length=7, validators=[hex_validator], default="#F2F0EF")
    color_4 = models.CharField(max_length=7, validators=[hex_validator], default="#3D5A80")
    color_5 = models.CharField(max_length=7, validators=[hex_validator], default="#293241")
    state = models.CharField(
        max_length=9,
        choices=FORM_STATE_CHOICES,
        default=DRAFT, 
    )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Form ID: {self.id}, Course: {self.course.title}, Name: {self.name}"
    
class Likert(models.Model):
    course_form = models.ForeignKey(CourseForm, on_delete=models.CASCADE, related_name="likert_questions")
    question = models.TextField()
    order = models.IntegerField()
    option_1 = models.CharField(max_length=255)
    option_2 = models.CharField(max_length=255)
    option_3 = models.CharField(max_length=255)
    option_4 = models.CharField(max_length=255)
    option_5 = models.CharField(max_length=255)

    def __str__(self):
        return f"Likert Q{self.order} for Form {self.course_form.id}: {self.question}"
    
class OpenEnded(models.Model):
    course_form = models.ForeignKey(CourseForm, on_delete=models.CASCADE, related_name="open_ended_questions")
    question = models.TextField()
    order = models.IntegerField()

    def __str__(self):
        return f"Open-Ended Q{self.order} for Form {self.course_form.id}: {self.question}"
    
class LikertResponse(models.Model):
    evaluator = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        limit_choices_to={'user_type': CustomUser.STUDENT},
        related_name="likert_responses_as_evaluator"
    )
    evaluee = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        limit_choices_to={'user_type': CustomUser.STUDENT},
        related_name="likert_responses_as_evaluee"
    )
    likert = models.ForeignKey(Likert, on_delete=models.CASCADE, related_name="responses")
    answer = models.IntegerField()


    def __str__(self):
        return f"Response by {self.student.username} to Likert Q{self.likert.order} (Form {self.likert.course_form.id}): {self.answer}"
    
class OpenEndedResponse(models.Model):
    evaluator = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        limit_choices_to={'user_type': CustomUser.STUDENT},
        related_name="open_ended_responses_as_evaluator"
    )
    evaluee = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        limit_choices_to={'user_type': CustomUser.STUDENT},
        related_name="open_ended_responses_as_evaluee"
    )
    open_ended = models.ForeignKey(OpenEnded, on_delete=models.CASCADE, related_name="responses")
    answer = models.TextField()

    def __str__(self):
        return f"Response by {self.student.username} to Open Ended Q{self.open_ended.order} (Form {self.open_ended.course_form.id})"
                
class Team(models.Model):
    name = models.CharField(max_length=100)
    course = models.ForeignKey(
        Course, 
        on_delete = models.CASCADE, 
        related_name = 'teams'
    )
    students = models.ManyToManyField(
        CustomUser, 
        limit_choices_to={'user_type': CustomUser.STUDENT},
        related_name='teams',
        blank=True
    )

    def __str__(self): 
        return f"{self.name} (Course: {self.course.code})"
    

