from django.test import TestCase

# Create your tests here.
class MathTests(TestCase):
    def test_addition(self):
        self.assertEqual(1 + 1, 2)
