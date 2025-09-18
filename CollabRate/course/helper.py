# === HELPER FUNCTIONS for views.py ===
from .models import Likert, OpenEnded

def rebuild_likert_questions(request, course_form):
    """
    Deletes all existing Likert questions for the course_form and re-creates them
    from the POST data.
    """
    course_form.likert_questions.all().delete()
    num_likert = course_form.num_likert
    for i in range(num_likert):
        question = request.POST.get(f"likert_question_{i}", "").strip()
        option_1 = request.POST.get(f"likert_{i}_label_1", "Strongly Disagree").strip()
        option_2 = request.POST.get(f"likert_{i}_label_2", "Disagree").strip()
        option_3 = request.POST.get(f"likert_{i}_label_3", "Neutral").strip()
        option_4 = request.POST.get(f"likert_{i}_label_4", "Agree").strip()
        option_5 = request.POST.get(f"likert_{i}_label_5", "Strongly Agree").strip()

        Likert.objects.create(
            course_form=course_form,
            question=question,
            order=i,
            option_1=option_1,
            option_2=option_2,
            option_3=option_3,
            option_4=option_4,
            option_5=option_5,
        )

def rebuild_open_ended_questions(request, course_form):
    """
    Deletes all existing Open-Ended questions for the course_form and re-creates
    them from the POST data.
    """
    course_form.open_ended_questions.all().delete()
    num_open_ended = course_form.num_open_ended
    for i in range(num_open_ended):
        question = request.POST.get(f"open_ended_question_{i}", "").strip()
        OpenEnded.objects.create(
            course_form=course_form,
            question=question,
            order=i,
        )

def rebuild_all_questions(request, course_form):
    """
    Rebuilds both Likert and Open-ended questions.
    """
    rebuild_likert_questions(request, course_form)
    rebuild_open_ended_questions(request, course_form)