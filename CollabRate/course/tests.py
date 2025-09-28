from django.test import TestCase
import pytest
from django.urls import reverse
from django.contrib.messages import get_messages
from django.utils import timezone
from accounts.models import CustomUser
from dashboard.models import Course
from course.models import CourseForm

# Create your tests here.
class MathTests(TestCase):
    def test_addition(self):
        self.assertEqual(1 + 1, 2)
