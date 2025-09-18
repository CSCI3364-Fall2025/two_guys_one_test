from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from dashboard.models import Course
from accounts.models import CustomUser
from .models import CourseForm, Team, Likert, LikertResponse, OpenEnded, OpenEndedResponse
from .helper import *
from django.http import HttpResponseRedirect
from django.core.mail import send_mail 
from django.urls import reverse 
from django.conf import settings
from django.utils import timezone
from datetime import datetime, time
from django.http import JsonResponse
from django.db.models import BooleanField, Case, Value, When
from django.db.models import Avg
import json

@login_required
def course_detail(request, join_code):
    course = get_object_or_404(Course, join_code=join_code)
    teams = Team.objects.filter(
        course=course,
        students=request.user,
    )

    now = timezone.now()

    team_forms = []
    for team in teams:
        # only non‐released forms whose deadline is still in the future
        todo = team.course_forms \
                   .exclude(state='released') \
                   .filter(due_datetime__gte=now)

        released = team.course_forms.filter(state='released')

        team_forms.append({
            'team':          team,
            'todo_forms':    todo,
            'released_forms': released,
        })

    latest_form = course.course_forms.order_by('-created_at').first()

    hour = now.hour
    if hour < 12:
        greeting = "Good morning"
    elif hour < 18:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"

    return render(request, 'course/course_landing.html', {
        'course':     course,
        'team_forms': team_forms,
        'latest_form': latest_form,
        'greeting': greeting,
    })

@login_required
def groups(request, join_code):
    return redirect('course_detail', join_code=join_code)

@login_required
def delete_team(request, join_code, team_id):
    course = get_object_or_404(Course, join_code=join_code)
    team   = get_object_or_404(Team, pk=team_id, course=course)

    if request.user != course.professor:
        messages.error(request, "Access denied.")
        return redirect('create_team', join_code=join_code)

    if request.method == "POST":
        name = team.name
        team.delete()
        messages.success(request, f"Team '{name}' has been deleted.")
    return redirect('create_team', join_code=join_code)

@login_required
def create_team(request, join_code):
    course = get_object_or_404(Course, join_code=join_code)
    user = request.user

    if request.user.user_type != CustomUser.PROFESSOR:
        messages.error(request, "Access denied: Professors only.")
        return redirect('dashboard')
    if course.professor != request.user:
        messages.error(request, "You do not have permission to access this course.")
        return redirect('dashboard')
    
    # Safeguard
    is_professor = (user == course.professor)
    is_enrolled = (
        user.user_type == CustomUser.STUDENT and
        course.students.filter(id=user.id).exists()
    )
    if not (is_professor or is_enrolled):
        return HttpResponseForbidden("You do not have permission to create a team for this course.")
    
    assigned_ids = Team.objects.filter(course=course).values_list('students__id', flat=True)
    available_students = course.students.exclude(id__in=assigned_ids)
    
    if request.method == "POST":
        team_name = request.POST.get("team_name", "")
        selected_ids = request.POST.getlist("students")
        
        if not team_name:
            messages.error(request, "Team name is required.")
            return render(request, "course/create_team.html", {
                "course": course,
                "students": available_students
            })

        if not selected_ids:
            messages.error(request, "At least one team member is required.")
            return render(request, "course/create_team.html", {
                "course": course,
                "students": available_students
            })
        # Create new team
        team = Team.objects.create(name=team_name, course=course)
        team.students.set(
            course.students.filter(id__in=selected_ids)
        )
    
        messages.success(request, f"Team '{team.name}' created successfully.")
        return redirect('create_team', join_code=course.join_code)

    # GET request show the empty form
    return render(request, "course/create_team.html", {
        "course": course,
        "students": available_students
    })

@login_required
def create_form(request, join_code):
    course = get_object_or_404(Course, join_code=join_code)
    # forms = CourseForm.objects.filter(course=course)
    now=timezone.now()
    forms = (CourseForm.objects
             .filter(course=course)
             .annotate(
                is_expired=Case(
                  When(due_datetime__lt=now, then=Value(True)),
                  default=Value(False),
                  output_field=BooleanField(),
                )
              )
    )

    if request.user.user_type != CustomUser.PROFESSOR:
        messages.error(request, "Access denied: Professors only.")
        return redirect('dashboard')
    if course.professor != request.user:
        messages.error(request, "You do not have permission to access this course.")
        return redirect('dashboard')

    # Default color values
    default_colors = {
        'color_1': "#872729",  # default color 1
        'color_2': "#C44B4B",  # default color 2
        'color_3': "#F2F0EF",  # default color 3
        'color_4': "#3D5A80",  # default color 4
        'color_5': "#293241",  # default color 5
    }

    if request.method == "POST":
        name = request.POST.get("form_name", "Untitled Form")
        self_evaluate = "self_evaluate" in request.POST
        num_likert = int(request.POST.get("num_likert", 0))
        num_open_ended = int(request.POST.get("num_open_ended", 0))

        due_dt_str = request.POST.get("due_datetime")
        print(due_dt_str)
        due_datetime = None
        if due_dt_str:
            try:
                # expects 'YYYY-MM-DDTHH:MM'
                due_datetime = datetime.fromisoformat(due_dt_str)
                print(due_datetime)
                print(timezone.now())
            except ValueError:
                messages.error(request, "Invalid date/time format.")
                return redirect('create_form', join_code=join_code)
        
        # Get color values from POST request or use default
        color_1 = request.POST.get('color_1', default_colors['color_1'])
        color_2 = request.POST.get('color_2', default_colors['color_2'])
        color_3 = request.POST.get('color_3', default_colors['color_3'])
        color_4 = request.POST.get('color_4', default_colors['color_4'])
        color_5 = request.POST.get('color_5', default_colors['color_5'])

        course_form = CourseForm.objects.create(
            course=course,
            name=name,
            self_evaluate=self_evaluate,
            num_likert=num_likert,
            num_open_ended=num_open_ended,
            due_datetime=due_datetime,
            color_1=color_1,
            color_2=color_2,
            color_3=color_3,
            color_4=color_4,
            color_5=color_5,
        )
        course_form.save()

        return redirect('draft_questions', join_code=join_code, course_form_id=course_form.pk)

    # Pass the default color values to the template
    return render(request, 'course/manage_forms.html', {
        'course': course,
        'default_colors': default_colors,
        'forms': forms
    })

@login_required
def edit_info(request, join_code, course_form_id):
    course = get_object_or_404(Course, join_code=join_code)
    course_form = get_object_or_404(CourseForm, pk=course_form_id)
    now=timezone.now()
    forms = (CourseForm.objects
             .filter(course=course)
             .annotate(
                is_expired=Case(
                  When(due_datetime__lt=now, then=Value(True)),
                  default=Value(False),
                  output_field=BooleanField(),
                )
              )
    )

    if request.user.user_type != CustomUser.PROFESSOR:
        messages.error(request, "Access denied: Professors only.")
        return redirect('dashboard')
    if course.professor != request.user:
        messages.error(request, "You do not have permission to access this course.")
        return redirect('dashboard')

    default_colors = {
        'color_1': "#872729",  # default color 1
        'color_2': "#C44B4B",  # default color 2
        'color_3': "#F2F0EF",  # default color 3
        'color_4': "#3D5A80",  # default color 4
        'color_5': "#293241",  # default color 5
    }

    if request.method == "POST":
        modified_num_likert = int(request.POST.get("num_likert", course_form.num_likert))
        if modified_num_likert < course_form.num_likert:
            Likert.objects.filter(course_form=course_form, order__gte=modified_num_likert).delete()
        
        modified_num_open_ended = int(request.POST.get("num_open_ended", course_form.num_open_ended))
        if modified_num_open_ended < course_form.num_open_ended:
            OpenEnded.objects.filter(course_form=course_form, order__gte=modified_num_open_ended).delete()

        due_dt_str = request.POST.get("due_datetime")
        due_datetime = None
        if due_dt_str:
            try:
                # expects 'YYYY-MM-DDTHH:MM'
                due_datetime = datetime.fromisoformat(due_dt_str)
            except ValueError:
                messages.error(request, "Invalid date/time format.")
                return redirect('edit_info', join_code=join_code, course_form_id=course_form_id)
        
        course_form.name = request.POST.get("form_name", course_form.name)
        course_form.self_evaluate = "self_evaluate" in request.POST
        course_form.num_likert = modified_num_likert
        course_form.num_open_ended = modified_num_open_ended
        course_form.due_datetime = due_datetime
        course_form.color_1 = request.POST.get("color_1", course_form.color_1)
        course_form.color_2 = request.POST.get("color_2", course_form.color_2)
        course_form.color_3 = request.POST.get("color_3", course_form.color_3)
        course_form.color_4 = request.POST.get("color_4", course_form.color_4)
        course_form.color_5 = request.POST.get("color_5", course_form.color_5)
        course_form.save()

        action = request.POST.get('action')
    
        # if action == 'release':
        #     course_form.state = 'released'
        #     course_form.save()
        #     print("🔁 POST request received!")
        #     '''
        #     students = CustomUser.objects.filter(teams__course_forms=course_form).distinct()
        #     for student in students:
        #         subject = f"Feedback Released: '{course_form.name}' in {course.code}"
        #         message = (
        #             f"Hello,\n\n"
        #             f"Feedback for the form \"{course_form.name}\" in your course \"{course.title}\" has been released.\n\n"
        #             f"You can now view your feedback and scores on the course page.\n\n"
        #             f"Thank you!"
        #         )
        #         from_email = settings.DEFAULT_FROM_EMAIL
        #         recipient_list = [student.email]
        #         send_mail(subject, message, from_email, recipient_list)
        #     '''
        #     messages.success(request, f"Form '{course_form.name}' released and notifications sent.")
        #     return redirect('course_detail', join_code=join_code)

        return redirect('draft_questions', join_code=join_code, course_form_id=course_form.pk)
    
    # form_expired = False
    # if course_form and course_form.state == "published":
    #     due_datetime = timezone.make_aware(datetime.combine(course_form.due_date, course_form.due_time))
    #     print(due_datetime)
    #     print(now)
    #     form_expired = now > due_datetime

    return render(request, 'course/manage_forms.html', {
        'course': course,
        'default_colors': default_colors,
        'forms': forms,
        'course_form': course_form,
        # 'form_expired': form_expired,
        # 'likert_questions': course_form.likert_questions.all(),
        # 'open_ended_questions': course_form.open_ended_questions.all(),
    })

@login_required
def draft_questions(request, join_code, course_form_id):
    course = get_object_or_404(Course, join_code=join_code)
    course_form = get_object_or_404(CourseForm, pk=course_form_id)
    now=timezone.now()
    forms = (CourseForm.objects
             .filter(course=course)
             .annotate(
                is_expired=Case(
                  When(due_datetime__lt=now, then=Value(True)),
                  default=Value(False),
                  output_field=BooleanField(),
                )
              )
    )

    if request.user.user_type != CustomUser.PROFESSOR:
        messages.error(request, "Access denied: Professors only.")
        return redirect('dashboard')
    if course.professor != request.user:
        messages.error(request, "You do not have permission to access this course.")
        return redirect('dashboard')

    likert_qs = list(course_form.likert_questions.all().order_by('order'))
    open_ended_qs = list(course_form.open_ended_questions.all().order_by('order'))

    if request.method == "POST":
        rebuild_all_questions(request, course_form)
        course_form.save()
        action = request.POST.get('action')

        if action == 'add_likert':
            course_form.num_likert += 1
            course_form.save()

            scroll_target = "likert"
            return HttpResponseRedirect(f'{request.path}?scroll={scroll_target}')
        
        elif action.startswith('delete_likert_'):
            try:
                delete_index = int(action.split("_")[2])
            except (ValueError, TypeError):
                delete_index = -1
            
            if delete_index >= 0:
                Likert.objects.filter(course_form=course_form, order=delete_index).delete()

                course_form.num_likert -= 1
                course_form.save()

                for lk in Likert.objects.filter(course_form=course_form).order_by('order'):
                    if lk.order > delete_index:
                        lk.order -= 1
                        lk.save()
            
            scroll_target = f"likert-{max(delete_index - 1, 0)}"
            return HttpResponseRedirect(f'{request.path}?scroll={scroll_target}')
        
        elif action == 'add_open_ended':
            course_form.num_open_ended += 1
            course_form.save()
            
            scroll_target = "open-ended"
            return HttpResponseRedirect(f"{request.path}?scroll={scroll_target}")
        
        elif action.startswith('delete_open_ended_'):
            try:
                delete_index = int(action.split("_")[3])
            except (ValueError, TypeError):
                delete_index = -1

            if delete_index >= 0:
                OpenEnded.objects.filter(course_form=course_form, order=delete_index).delete()

                course_form.num_open_ended -= 1
                course_form.save()

                for oe in OpenEnded.objects.filter(course_form=course_form).order_by('order'):
                    if oe.order > delete_index:
                        oe.order -= 1
                        oe.save()
            
            scroll_target = f"open-ended-{max(delete_index - 1, 0)}"
            return HttpResponseRedirect(f'{request.path}?scroll={scroll_target}')

        elif action == 'save':
            scroll_target = "save"
            return HttpResponseRedirect(f"{request.path}?scroll={scroll_target}")
        
        elif action == 'publish':
            all_teams = Team.objects.filter(course=course)
            course_form.teams.set(all_teams)

            course_form.state = CourseForm.PUBLISHED
            course_form.save()

            # students = CustomUser.objects.filter(
            #     teams__in=all_teams
            # ).distinct()
            # for student in students:
            #     local_dt = timezone.localtime(course_form.due_datetime, timezone.get_current_timezone())

            #     # 2) Format as “Apr 30 at 03:20 PM”
            #     due_date_str = local_dt.strftime('%b %d')
            #     due_time_str = local_dt.strftime('%I:%M %p')

            #     subject = f"New Form Published: '{course_form.name}' in {course_form.course.code}"
            #     message = (
            #         f"Hello,\n\n"
            #         f"A new form \"{course_form.name}\" has been published in your course "
            #         f"\"{course_form.course.title}\".\n\n"
            #         f"Due: {due_date_str} at {due_time_str}\n\n"
            #         f"Please visit the course page to fill out the form.\n\n"
            #         f"Thank you!"
            #     )
            #     send_mail(
            #         subject,
            #         message,
            #         settings.DEFAULT_FROM_EMAIL,
            #         [student.email],
            #     )
            messages.success(request, f"Form '{course_form.name}' published and notifications sent.")
            # return redirect('create_form', join_code=join_code)
            return redirect('view_form_responses', join_code=join_code, course_form_id=course_form.pk)
        
        # elif action == 'release':
        #     course_form.state = 'released'
        #     course_form.save()
        #     students = CustomUser.objects.filter(teams__course_forms=course_form).distinct()
        #     for student in students:
        #         subject = f"Feedback Released: '{course_form.name}' in {course.code}"
        #         message = (
        #             f"Hello,\n\n"
        #             f"Feedback for the form \"{course_form.name}\" in your course \"{course.title}\" has been released.\n\n"
        #             f"You can now view your feedback and scores on the course page.\n\n"
        #             f"Thank you!"
        #         )
        #         from_email = settings.DEFAULT_FROM_EMAIL
        #         recipient_list = [student.email]
        #         send_mail(subject, message, from_email, recipient_list)

        #     messages.success(request, f"Form '{course_form.name}' released and notifications sent.")
        #     return redirect('course_detail', join_code=join_code)

    context = {
        'course': course,
        'course_form': course_form,
        'forms': forms,
        'likert_qs': likert_qs,
        'open_ended_qs': open_ended_qs,
    }
    return render(request, 'course/draft_questions.html', context)


@login_required
def view_form_responses(request, join_code, course_form_id):
    # 1) Get the course and enforce professor-only access
    course = get_object_or_404(Course, join_code=join_code)
    if request.user.user_type != CustomUser.PROFESSOR or course.professor != request.user:
        messages.error(request, "Access denied.")
        return redirect('dashboard')

    # 2) Get the specific form
    course_form = get_object_or_404(CourseForm, pk=course_form_id, course=course)

    # —— NEW: handle “release” button POST ——
    if request.method == "POST" and request.POST.get("action") == "release":
        course_form.state = CourseForm.RELEASED
        course_form.save(update_fields=["state"])
        messages.success(request, "Form results have been released.")
        # Redirect back to this view so the template sees state="released"
        return redirect('view_form_responses', join_code=join_code, course_form_id=course_form_id)

    # 3) Build the sidebar list of all forms for this course
    now=timezone.now()
    forms = (CourseForm.objects
             .filter(course=course)
             .annotate(
                is_expired=Case(
                  When(due_datetime__lt=now, then=Value(True)),
                  default=Value(False),
                  output_field=BooleanField(),
                )
              )
    )

    # 4) Has the due date/time passed?
    form_expired = False
    if course_form.due_datetime:
        form_expired = timezone.now() > course_form.due_datetime

    # 5) Grab the questions to loop over
    likert_questions      = course_form.likert_questions.all()
    open_ended_questions  = course_form.open_ended_questions.all()

    return render(request, 'course/form_responses.html', {
        'course': course,
        'forms': forms,
        'course_form': course_form,
        'form_expired': form_expired,
        'likert_questions': likert_questions,
        'open_ended_questions': open_ended_questions,
    })

@login_required
def view_forms(request, join_code):
    course = get_object_or_404(Course, join_code=join_code)
    now=timezone.now()
    forms = (CourseForm.objects
             .filter(course=course)
             .annotate(
                is_expired=Case(
                  When(due_datetime__lt=now, then=Value(True)),
                  default=Value(False),
                  output_field=BooleanField(),
                )
              )
    )

    if request.user.user_type != CustomUser.PROFESSOR:
        messages.error(request, "Access denied: Professors only.")
        return redirect('dashboard')
    if course.professor != request.user:
        messages.error(request, "You do not have permission to access this course.")
        return redirect('dashboard')

    return render(request, "course/view_forms.html", {
        "join_code": join_code,
        "course": course,
        'forms': forms,
    })

@login_required
def delete_form(request, join_code, course_form_id):
    course_form = get_object_or_404(CourseForm, pk=course_form_id)
    name = course_form.name

    # 1) Delete all responses and questions
    LikertResponse.objects.filter(likert__course_form=course_form).delete()
    OpenEndedResponse.objects.filter(open_ended__course_form=course_form).delete()
    course_form.likert_questions.all().delete()
    course_form.open_ended_questions.all().delete()

    # 2) Now delete the form itself
    course_form.delete()

    messages.success(request, f"{name} has been deleted.")
    return redirect('create_form', join_code=join_code)

# @login_required
# def edit_form(request, join_code, form_id):
#     course = get_object_or_404(Course, join_code=join_code)
#     form = get_object_or_404(CourseForm, pk=form_id, course=course)
    
#     if request.method == 'POST':
#         form.name = request.POST.get('form_name')
#         form.due_date = request.POST.get('due_date')
#         form.due_time = request.POST.get('due_time')
#         form.self_evaluate = 'self_evaluate' in request.POST
#         form.color_1 = request.POST.get('color_1')
#         form.color_2 = request.POST.get('color_2')
#         form.color_3 = request.POST.get('color_3')
#         form.color_4 = request.POST.get('color_4')
#         form.color_5 = request.POST.get('color_5')

#         form.save() 
#         messages.success(request, f"Form '{form.name}' has been updated successfully.")
#         return redirect('view_forms', join_code=join_code)
    
#     return render(request, 'course/edit_form.html', {
#         'form': form,
#         'course': course,
#     })

def clear_course_forms(request, join_code):
    # Assuming you have a CourseForm model to clear forms
    try:
        course = Course.objects.get(join_code=join_code)
        # Assuming the course forms are related to the course
        CourseForm.objects.filter(course=course).delete()

        messages.success(request, 'All course forms have been cleared!')
    except Course.DoesNotExist:
        messages.error(request, 'Course not found.')

    return redirect('course_detail', join_code=join_code)

@login_required
def edit_form(request, join_code, form_id):
    course = get_object_or_404(Course, join_code=join_code)
    form = get_object_or_404(CourseForm, pk=form_id, course=course)

    if request.user.user_type != CustomUser.PROFESSOR:
        messages.error(request, "Access denied: Professors only.")
        return redirect('dashboard')
    if course.professor != request.user:
        messages.error(request, "You do not have permission to access this course.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        form.name = request.POST.get('form_name')
        form.due_date = request.POST.get('due_date')
        form.due_time = request.POST.get('due_time')
        form.self_evaluate = 'self_evaluate' in request.POST
        form.color_1 = request.POST.get('color_1')
        form.color_2 = request.POST.get('color_2')
        form.color_3 = request.POST.get('color_3')
        form.color_4 = request.POST.get('color_4')
        form.color_5 = request.POST.get('color_5')

        form.save() 
        # students = CustomUser.objects.filter(teams__course_forms=form).distinct()
        # if form.state == 'published':
        #     for student in students:
        #         subject = f"Update: '{form.name}' in {course.code}"
        #         message = (
        #             f"Hello,\n\n"
        #             f"The form \"{form.name}\" in your course \"{course.title}\" has been updated.\n\n"
        #             f"Due Date: {form.due_date} at {form.due_time.strftime('%I:%M %p')}\n\n"
        #             f"Check your course page for more details.\n\n"
        #             "Thank you!"
        #         )
        #         from_email = settings.DEFAULT_FROM_EMAIL
        #         recipient_list = [student.email]
        #         send_mail(subject, message, from_email, recipient_list)
    
        messages.success(request, f"Form '{form.name}' has been updated successfully.")
        return redirect('view_forms', join_code=join_code)
    
    return render(request, 'course/edit_form.html', {
        'form': form,
        'course': course,
    })

# @login_required
# def answer_form(request, join_code, form_id):
#     # 1) Fetch course & form, enforce student-only
#     course = get_object_or_404(Course, join_code=join_code)
#     form_obj = get_object_or_404(CourseForm, pk=form_id, course=course)
#     if request.user.user_type != CustomUser.STUDENT:
#         return HttpResponseForbidden("Only students can answer forms.")

#     # 2) Handle POST: always require a peer selection
#     if request.method == "POST":
#         evaluee_id = request.POST.get("evaluee_id")
#         if not evaluee_id:
#             messages.error(request, "No evaluated student selected.")
#             return redirect(request.path)

#         try:
#             evaluee = CustomUser.objects.get(
#                 pk=evaluee_id,
#                 user_type=CustomUser.STUDENT
#             )
#         except CustomUser.DoesNotExist:
#             messages.error(request, "Selected evaluated student does not exist.")
#             return redirect(request.path)

#         # save likert responses
#         for likert in form_obj.likert_questions.all():
#             val = request.POST.get(f"likert_{likert.id}")
#             if val:
#                 try:
#                     LikertResponse.objects.create(
#                         evaluator=request.user,
#                         evaluee=evaluee,
#                         likert=likert,
#                         answer=int(val)
#                     )
#                 except ValueError:
#                     pass

#         # save open-ended responses
#         for open_q in form_obj.open_ended_questions.all():
#             txt = request.POST.get(f"open_{open_q.id}", "").strip()
#             if txt:
#                 OpenEndedResponse.objects.create(
#                     evaluator=request.user,
#                     evaluee=evaluee,
#                     open_ended=open_q,
#                     answer=txt
#                 )

#         messages.success(request, "Your responses have been submitted successfully!")
#         return redirect("course_detail", join_code=course.join_code)

#     # 3) GET: prepare data for the form
#     likert_questions = form_obj.likert_questions.all()
#     open_questions = form_obj.open_ended_questions.all()
#     teams = course.teams.filter(students=request.user)
#     potential_peers = {
#         student
#         for team in teams
#         for student in team.students.exclude(pk=request.user.pk)
#     }

#     # preload any existing responses if ?evaluee_id=… is present
#     selected_evaluee_id = request.GET.get("evaluee_id")
#     existing_likert = {}
#     existing_open = {}

#     if selected_evaluee_id:
#         try:
#             ev = CustomUser.objects.get(
#                 pk=selected_evaluee_id,
#                 user_type=CustomUser.STUDENT
#             )
#             existing_likert = {
#                 r.likert_id: r.answer
#                 for r in LikertResponse.objects.filter(
#                     evaluator=request.user,
#                     evaluee=ev,
#                     likert__course_form=form_obj
#                 )
#             }
#             existing_open = {
#                 r.open_ended_id: r.answer
#                 for r in OpenEndedResponse.objects.filter(
#                     evaluator=request.user,
#                     evaluee=ev,
#                     open_ended__course_form=form_obj
#                 )
#             }
#             selected_evaluee_id = int(selected_evaluee_id)
#         except CustomUser.DoesNotExist:
#             selected_evaluee_id = None

#     # 4) Single consolidated context
#     context = {
#         "course":                course,
#         "form_obj":              form_obj,
#         "likert_questions":      likert_questions,
#         "open_questions":        open_questions,
#         "likert_scale_values":   [1, 2, 3, 4, 5],
#         "potential_peers":       list(potential_peers),
#         "selected_evaluee_id":   selected_evaluee_id,
#         "existing_likert":       existing_likert,
#         "existing_open":         existing_open,
#     }

#     return render(request, "course/answer_form.html", context)

@login_required
def answer_form(request, join_code, form_id):
    # 1) Fetch course & form; enforce student-only access
    course   = get_object_or_404(Course, join_code=join_code)
    form_obj = get_object_or_404(CourseForm, pk=form_id, course=course)
    if request.user.user_type != CustomUser.STUDENT:
        return HttpResponseForbidden("Only students can answer forms.")

    # 2) POST: update or create responses
    if request.method == "POST":
        evaluee_id = request.POST.get("evaluee_id")
        if not evaluee_id:
            messages.error(request, "No evaluated student selected.")
            return redirect(request.path)

        try:
            evaluee = CustomUser.objects.get(
                pk=evaluee_id,
                user_type=CustomUser.STUDENT
            )
        except CustomUser.DoesNotExist:
            messages.error(request, "Selected evaluated student does not exist.")
            return redirect(request.path)

        # Likert responses: update existing or create new
        for likert in form_obj.likert_questions.all():
            val = request.POST.get(f"likert_{likert.id}")
            if val:
                try:
                    LikertResponse.objects.update_or_create(
                        evaluator=request.user,
                        evaluee=evaluee,
                        likert=likert,
                        defaults={"answer": int(val)}
                    )
                except ValueError:
                    pass

        # Open-ended responses: update existing or create new
        for open_q in form_obj.open_ended_questions.all():
            txt = request.POST.get(f"open_{open_q.id}", "").strip()
            if txt:
                OpenEndedResponse.objects.update_or_create(
                    evaluator=request.user,
                    evaluee=evaluee,
                    open_ended=open_q,
                    defaults={"answer": txt}
                )

        messages.success(request, "Your responses have been submitted successfully!")
        return redirect("course_detail", join_code=course.join_code)

    # 3) GET: prepare everything for rendering
    likert_questions   = form_obj.likert_questions.all()
    open_questions     = form_obj.open_ended_questions.all()
    teams              = course.teams.filter(students=request.user)
    potential_peers    = {
        student
        for team in teams
        for student in team.students.exclude(pk=request.user.pk)
    }

    # if self-evaluation is enabled, allow user to evaluate themselves
    if form_obj.self_evaluate:
        potential_peers.add(request.user)

    # If an evaluee was selected, load their existing answers
    selected_evaluee_id = request.GET.get("evaluee_id")
    existing_likert     = {}
    existing_open       = {}

    if selected_evaluee_id:
        try:
            ev = CustomUser.objects.get(
                pk=selected_evaluee_id,
                user_type=CustomUser.STUDENT
            )
            existing_likert = {
                r.likert_id: r.answer
                for r in LikertResponse.objects.filter(
                    evaluator=request.user,
                    evaluee=ev,
                    likert__course_form=form_obj
                )
            }
            existing_open = {
                r.open_ended_id: r.answer
                for r in OpenEndedResponse.objects.filter(
                    evaluator=request.user,
                    evaluee=ev,
                    open_ended__course_form=form_obj
                )
            }
            selected_evaluee_id = int(selected_evaluee_id)
        except CustomUser.DoesNotExist:
            selected_evaluee_id = None
    
    colors = [
      form_obj.color_1,
      form_obj.color_2,
      form_obj.color_3,
      form_obj.color_4,
      form_obj.color_5,
    ]
    scale = [1, 2, 3, 4, 5]
    likert_choices = list(zip(scale, colors))

    # 4) Consolidated context
    context = {
        "course":               course,
        "form_obj":             form_obj,
        "likert_questions":     likert_questions,
        "open_questions":       open_questions,
        "likert_choices":       likert_choices,
        "potential_peers":      list(potential_peers),
        "selected_evaluee_id":  selected_evaluee_id,
        "existing_likert":      existing_likert,
        "existing_open":        existing_open,
    }

    return render(request, "course/answer_form.html", context)

@login_required
def update_open_ended_response(request, join_code, course_form_id, response_id):
    if request.method == 'POST':
        new_answer = request.POST.get('answer')

        # Use get_object_or_404 to get the response, providing better error handling
        response = get_object_or_404(OpenEndedResponse, id=response_id)

        # Update the response with the new answer
        response.answer = new_answer
        response.save()

        # Return a JsonResponse instead of redirecting
        # return JsonResponse({
        #     'success': True,
        #     'message': 'Response updated successfully!',
        #     'updated_answer': new_answer,  # Optionally include the updated answer in the response
        #     'response_id': response_id,
        # })
        return redirect('view_form_responses', join_code=join_code, course_form_id=course_form_id)
    
    # If the request is not POST, return an error
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method.'
    })

@login_required


@login_required
def peer_results(request, join_code, form_id):
    course = get_object_or_404(Course, join_code=join_code)
    course_form = get_object_or_404(CourseForm, id=form_id, course=course)

    # Get Likert and OpenEnded questions
    likert_questions = course_form.likert_questions.all()
    open_ended_questions = course_form.open_ended_questions.all()

    # Get all Likert responses where this user was evaluated
    likert_responses = LikertResponse.objects.filter(
        likert__course_form=course_form,
        evaluee=request.user
    )

    # Calculate average per Likert question
    likert_averages = {}
    for likert in likert_questions:
        responses = likert_responses.filter(likert=likert)
        avg_score = responses.aggregate(avg=Avg('answer'))['avg']
        if avg_score is not None:
            likert_averages[likert.question] = round(avg_score, 2)
        else:
            likert_averages[likert.question] = "No responses yet"

    barchart_data = []
    for likert in likert_questions:
        qs = LikertResponse.objects.filter(evaluee=request.user, likert=likert)
        total = qs.count() or 1  # avoid div by zero

        bars = []
        for i in range(1, 6):
            cnt = qs.filter(answer=i).count()
            pct = (cnt / total) * 100
            color = getattr(course_form, f'color_{i}')
            bars.append({
                "width": f"{pct:.1f}%",
                "color": color
            })
        barchart_data.append({
            "question": likert.question,
            "avg": likert_averages.get(likert.question),
            "bars": bars
        })

    overall_score = likert_responses.aggregate(avg=Avg('answer'))['avg']
    if overall_score is not None:
        overall_score = round(overall_score, 2)

    open_ended_responses = OpenEndedResponse.objects.filter(
        open_ended__course_form=course_form,
        evaluee=request.user
    ).values_list('answer', flat=True)

    feedback_list = sorted(open_ended_responses)
    context = {
        'course': course,
        'course_form': course_form,
        'likert_averages': likert_averages,
        'score': overall_score,
        'feedback': feedback_list,
        'barchart_data': barchart_data,
    }

    return render(request, 'course/peer_results.html', context)