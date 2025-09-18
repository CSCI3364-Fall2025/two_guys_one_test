from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired 
from django.urls import reverse
from django.conf import settings
from accounts.models import CustomUser
from .models import Course
from .models import Course
import json
from django.http import HttpRequest
from django.shortcuts import render, get_object_or_404
from course.models import Course, CourseForm, Team, LikertResponse, OpenEndedResponse
from django.shortcuts import render, get_object_or_404
from course.models import CourseForm, LikertResponse, OpenEndedResponse, Team
from dashboard.models import Course
from accounts.models import CustomUser


@login_required
def dashboard(request):
    if request.user.user_type == CustomUser.PROFESSOR:
        courses = request.user.courses.all()
    elif request.user.user_type == CustomUser.STUDENT:
        courses = request.user.enrolled_courses.all()
    else:
        courses = Course.objects.none()
    return render(request, 'dashboard/dashboard.html', {'courses': courses})

@login_required
def join_course(request):
    if request.method == "POST":
        join_code = request.POST.get('join_code', '').strip()

        if len(join_code) != 6 or not join_code.isalnum():
            messages.error(request, "Invalid Code. Must be a 6-digit alphanumeric code.")
            return redirect('dashboard')
        
        try:
            course = Course.objects.get(join_code=join_code)
        except Course.DoesNotExist:
            messages.error(request, "A Course With This Code Does Not Exist.")
            return redirect('dashboard')
        
        if request.user.user_type != CustomUser.STUDENT:
            messages.error(request, "Joining a course is restricted to students.")
            return redirect('dashboard')

        if course.students.filter(pk=request.user.pk).exists():
            messages.info(request, f"Already enrolled in {course.title}.")
            return redirect('dashboard')

        course.students.add(request.user)
        course.student_count = course.students.count()
        course.save()

        messages.success(request, f"Successfully joined {course.title}!")
    return redirect('dashboard')

@login_required
def create_course(request):
    if request.method == "POST":
        code = request.POST.get('code', '').strip()
        title = request.POST.get('title', '').strip()
        semester = request.POST.get('semester')
        year = request.POST.get('year')
        color = request.POST.get('color', '').strip()

        if not all([code, title, semester, year]):
            messages.error(request, "All fields are required.")
            return redirect('dashboard')
        
        # Prevent duplicate course identifiers
        if Course.objects.filter(code__iexact=code, semester__iexact=semester, year=year).exists():
            messages.error(request, f"{code} already exists.")
            return redirect('dashboard')
        
        course = Course(code=code, title=title, semester=semester, year=int(year), color=color, professor=request.user)
        course.save()

        # raw_emails = request.POST.get('invite_email', '[]')
        # try:
        #     emails = json.loads(raw_emails)
        # except ValueError:
        #     emails = []
        
        # signer = TimestampSigner()
        # for email in emails:
        #     email = email.get('value', '').strip()
        #     if not email.lower().endswith('@bc.edu'):
        #         continue
        #     token = signer.sign(email)
        #     invite_url = request.build_absolute_uri(
        #         reverse('course_invite', args=[course.join_code, token])
        #     )
        #     subject = f"Invitation to join {course.title}"
        #     message = (
        #         f"Hello,\n\n"
        #         f"You have been invited to join the course \"{course.title}\".\n\n"
        #         f"Click the following link to join the course:\n{invite_url}\n\n"
        #         "If you did not expect this invitation, please ignore this email.\n\n"
        #         "Thank you!"
        #     )
        #     from_email = settings.DEFAULT_FROM_EMAIL
        #     recipient_list = [email]
        #     send_mail(subject, message, from_email, recipient_list)
        messages.success(request, f"Course {course.title} created. Join Code: {course.join_code}")
    return redirect('dashboard')

@login_required
def leave_course(request, join_code):
    if request.user.user_type != CustomUser.STUDENT:
        messages.error(request, "Leaving a course is restricted to students.")
        return redirect('dashboard')
    course = get_object_or_404(Course, join_code=join_code)
    course.students.remove(request.user)
    messages.success(request, f"Unenrolled from {course.title}.")
    return redirect('dashboard')

@login_required
def delete_course(request, join_code):
    try:
        course = Course.objects.get(join_code=join_code, professor=request.user)
    except Course.DoesNotExist():
        messages.error(request, "Course not found. Do not have permission to delete a course.")
    else:
        title = course.title
        course.delete()
        messages.success(request, f"Course {title} has been deleted.")
    return redirect('dashboard')

@login_required
def course_invite(request, join_code, token):
    signer = TimestampSigner()
    try:
        invited_email = signer.unsign(token, max_age=3600)
    except SignatureExpired:
        messages.error(request, "The invitation link has expired.")
        return redirect('dashboard')
    except BadSignature:
        messages.error(request, "Invalid invitation link.")
        return redirect('dashboard')
    
    course = get_object_or_404(Course, join_code=join_code)
    if request.user.email.lower() != invited_email.lower():
        messages.error(request, "The invitation link is intended for a different account. Please sign in with the correct email.")
        return redirect('dashboard')
    if course.students.filter(pk=request.user.pk).exists():
        messages.info(request, f"Already enrolled in {course.title}")
    else:
        course.students.add(request.user)
        course.student_count = course.students.count()
        course.save()
        messages.success(request, f"Successfully enrolled in {course.title}.")

    return redirect('dashboard')

def calculate_average_score(likert_responses):
    if not likert_responses.exists():
        return 0.0
    
    total = sum(resp.answer for resp in likert_responses)
    return total / likert_responses.count()



def calculate_average_score(likert_responses):
    if not likert_responses.exists():
        return 0.0
    total = sum(resp.answer for resp in likert_responses)
    return total / likert_responses.count()

def peer_results(request, course_code, delivery_number):
    course = get_object_or_404(Course, code=course_code)
    form_name = f"Delivery {delivery_number}"
    form = get_object_or_404(CourseForm, course=course, name=form_name)
    student = request.user

    team = Team.objects.get(students=student, course=course)

    # Get all Likert and open-ended responses about this student for this form
    likert_scores = LikertResponse.objects.filter(student=student, likert__course_form=form)
    open_feedback = OpenEndedResponse.objects.filter(student=student, open_ended__course_form=form)

    # Sort feedback alphabetically
    sorted_feedback = sorted([resp.answer for resp in open_feedback])

    score = calculate_average_score(likert_scores)

    context = {
        "course": course,
        "form": form,
        "score": round(score, 1),
        "feedback_list": sorted_feedback,
    }
    return render(request, "dashboard/peer_results.html", context)
