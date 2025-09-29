import pytest
from datetime import datetime
from django.db import IntegrityError
from django.utils import timezone
from django.urls import reverse
from django.contrib.messages import get_messages
from accounts.models import CustomUser
from dashboard.models import Course
from course.models import CourseForm

pytestmark = pytest.mark.django_db


# --------- Fixtures ---------

@pytest.fixture
def professor_user():
    return CustomUser.objects.create_user(
        username="prof_jane",
        email="prof@example.com",
        password="strong-pass",
        user_type=CustomUser.PROFESSOR,
    )

@pytest.fixture
def other_professor():
    return CustomUser.objects.create_user(
        username="prof_john",
        email="prof2@example.com",
        password="strong-pass",
        user_type=CustomUser.PROFESSOR,
    )

@pytest.fixture
def student_user():
    return CustomUser.objects.create_user(
        username="stud_mia",
        email="student@example.com",
        password="strong-pass",
        user_type=CustomUser.STUDENT,
    )

@pytest.fixture
def course(professor_user):
    return Course.objects.create(
        title="Software Engineering",
        code="CSCI-3333",
        semester="Fall",
        year=2030,
        professor=professor_user,
    )

# URL for creating a form for a given course
@pytest.fixture
def create_form_url(course):
    return reverse("create_form", args=[course.join_code])


# --------- Login required ---------

# Ensure that unauthenticated users are redirected to login when accessing the form creation page
def test_create_form_requires_login_redirects_to_login(client, create_form_url):
    resp = client.get(create_form_url)
    # Should be a redirect to login with ?next=...
    assert resp.status_code in (302, 301)
    assert "next=" in resp.url


# --------- GET access control ---------

# Ensure the form creation page loads correctly for professors with proper context variables
def test_get_create_form_professor_ok(client, professor_user, course, create_form_url):
    client.force_login(professor_user)
    resp = client.get(create_form_url)
    assert resp.status_code == 200
    assert "default_colors" in resp.context
    assert set(resp.context["default_colors"].keys()) == {
        "color_1", "color_2", "color_3", "color_4", "color_5"
    }
    assert "forms" in resp.context

# Ensure students cannot access the form creation page
def test_get_create_form_denied_for_student(client, student_user, course, create_form_url):
    client.force_login(student_user)
    resp = client.get(create_form_url, follow=True)
    assert resp.status_code == 200
    msgs = [m.message for m in get_messages(resp.wsgi_request)]
    assert any("Access denied: Professors only." in m for m in msgs)

# Ensure professors who do not own the course cannot access the form creation page
def test_get_create_form_denied_for_non_owner_prof(client, other_professor, course, create_form_url):
    client.force_login(other_professor)
    resp = client.get(create_form_url, follow=True)
    assert resp.status_code == 200
    msgs = [m.message for m in get_messages(resp.wsgi_request)]
    assert any("You do not have permission to access this course." in m for m in msgs)


# --------- POST success paths ---------

# Test creating a form with all fields provided
def test_post_create_form_success_with_all_fields(client, professor_user, course, create_form_url):
    client.force_login(professor_user)
    payload = {
        "form_name": "Sprint 1 Peer Eval",
        "self_evaluate": "on",
        "num_likert": "3",
        "num_open_ended": "2",
        "due_datetime": "2030-12-31T23:59",
        "color_1": "#111111",
        "color_2": "#222222",
        "color_3": "#333333",
        "color_4": "#444444",
        "color_5": "#555555",
    }
    resp = client.post(create_form_url, data=payload, follow=True)
    assert resp.status_code == 200

    cf = CourseForm.objects.get(name="Sprint 1 Peer Eval")
    assert cf.self_evaluate is True
    assert cf.num_likert == 3
    assert cf.num_open_ended == 2

    expected_naive = datetime(2030, 12, 31, 23, 59)
    expected_aware = timezone.make_aware(expected_naive, timezone.get_current_timezone())
    assert timezone.localtime(cf.due_datetime, timezone.get_current_timezone()) == expected_aware

    assert (cf.color_1, cf.color_2, cf.color_3, cf.color_4, cf.color_5) == (
        "#111111", "#222222", "#333333", "#444444", "#555555"
    )

# Test creating a form with only required fields provided
def test_post_create_form_uses_defaults_for_missing_fields(client, professor_user, course, create_form_url):
    """
    Missing name -> 'Untitled Form'
    Missing due_datetime -> None
    Missing colors -> default palette from view
    """
    client.force_login(professor_user)
    payload = {
        # no form_name
        "num_likert": "0",
        "num_open_ended": "0",
        # no due_datetime, no color_* keys
    }
    resp = client.post(create_form_url, data=payload, follow=True)
    assert resp.status_code == 200

    cf = CourseForm.objects.get(name="Untitled Form")
    assert cf.due_datetime is None
    assert (cf.color_1, cf.color_2, cf.color_3, cf.color_4, cf.color_5) == (
        "#872729", "#C44B4B", "#F2F0EF", "#3D5A80", "#293241"
    )


# --------- POST invalid inputs ---------

# Test that duplicate form names for the same course are rejected
def test_post_create_form_invalid_date_shows_message_and_no_create(client, professor_user, course, create_form_url):
    client.force_login(professor_user)
    payload = {
        "form_name": "Bad Date",
        "num_likert": "2",
        "num_open_ended": "1",
        "due_datetime": "not-a-date",
    }
    resp = client.post(create_form_url, data=payload, follow=True)
    assert resp.status_code == 200
    assert CourseForm.objects.filter(name="Bad Date").count() == 0
    msgs = [m.message for m in get_messages(resp.wsgi_request)]
    assert any("Invalid date/time format." in m for m in msgs)

# Test that non-integer counts raise ValueError and do not create a form
@pytest.mark.django_db
def test_post_create_form_noninteger_counts_raises_value_error(
    client, professor_user, course, create_form_url
):
    client.force_login(professor_user)
    payload = {"form_name": "Bad Counts", "num_likert": "abc", "num_open_ended": "1"}
    with pytest.raises(ValueError):
        client.post(create_form_url, data=payload, follow=False)
    assert CourseForm.objects.filter(name="Bad Counts").count() == 0

# --------- POST permissions ---------

# Ensure students cannot create forms
def test_post_create_form_denied_for_student(client, student_user, course, create_form_url):
    client.force_login(student_user)
    resp = client.post(create_form_url, data={
        "form_name": "Student Try",
        "num_likert": "1",
        "num_open_ended": "0",
    }, follow=True)

    assert resp.status_code == 200
    assert CourseForm.objects.filter(name="Student Try").count() == 0
    msgs = [m.message for m in get_messages(resp.wsgi_request)]
    assert any("Access denied: Professors only." in m for m in msgs)

def test_post_create_form_denied_for_non_owner_prof(client, other_professor, course, create_form_url):
    client.force_login(other_professor)
    resp = client.post(create_form_url, data={
        "form_name": "Wrong Owner",
        "num_likert": "1",
        "num_open_ended": "0",
    }, follow=True)

    assert resp.status_code == 200
    assert CourseForm.objects.filter(name="Wrong Owner").count() == 0
    msgs = [m.message for m in get_messages(resp.wsgi_request)]
    assert any("You do not have permission to access this course." in m for m in msgs)

# ------------------- Form Edge Case Tests -------------------

#fails
#check that the form 255 limit works
def test_post_create_form_name_too_long(client, professor_user, course, create_form_url):
    client.force_login(professor_user)
    payload = {"form_name": "A"*256, "num_likert": "1", "num_open_ended": "0"}
    resp = client.post(create_form_url, data=payload, follow=True)
    assert resp.status_code == 200
    assert CourseForm.objects.filter(name="A"*256).count() == 0
    msgs = [m.message for m in get_messages(resp.wsgi_request)]
    assert any("Ensure this value has at most" in m for m in msgs)

#fails
#check if negative numbers can be used
@pytest.mark.parametrize("field,value", [("num_likert",-1), ("num_open_ended",-5)])
def test_post_create_form_negative_counts(client, professor_user, course, create_form_url, field, value):
    client.force_login(professor_user)
    payload = {"form_name": "Negative Test", field: str(value)}
    resp = client.post(create_form_url, data=payload, follow=True)
    assert resp.status_code == 200
    assert CourseForm.objects.filter(name="Negative Test").count() == 0

#fails
#check if default colors apply (I thought they did, but fails)
def test_post_create_form_empty_colors_uses_default(client, professor_user, course, create_form_url):
    client.force_login(professor_user)
    payload = {"form_name": "Empty Colors", "num_likert":"1","num_open_ended":"1",
               "color_1":"","color_2":"","color_3":"","color_4":"","color_5":""}
    resp = client.post(create_form_url, data=payload, follow=True)
    cf = CourseForm.objects.get(name="Empty Colors")
    assert (cf.color_1, cf.color_2, cf.color_3, cf.color_4, cf.color_5) == (
        "#872729", "#C44B4B", "#F2F0EF", "#3D5A80", "#293241"
    )

#fails
#check if duplicate names can happen
def test_post_create_form_duplicate_names_same_course(client, professor_user, course, create_form_url):
    client.force_login(professor_user)
    payload = {"form_name": "DupTest", "num_likert":"1","num_open_ended":"1"}
    client.post(create_form_url, data=payload)
    with pytest.raises(IntegrityError):
        CourseForm.objects.create(course=course, name="DupTest")

#fails
#check if forms can be instantiated in the past (known issue)
def test_post_create_form_due_date_in_past(client, professor_user, course, create_form_url):
    client.force_login(professor_user)
    payload = {"form_name": "Past Date", "num_likert":"1","num_open_ended":"1",
               "due_datetime":"2000-01-01T12:00"}
    resp = client.post(create_form_url, data=payload, follow=True)
    msgs = [m.message for m in get_messages(resp.wsgi_request)]
    assert any("due date cannot be in the past" in m.lower() for m in msgs)

#check if weird symbols mess up the form
def test_post_create_form_unicode_name(client, professor_user, course, create_form_url):
    client.force_login(professor_user)
    payload = {"form_name": "Peer Eval ✅", "num_likert":"2","num_open_ended":"1"}
    resp = client.post(create_form_url, data=payload, follow=True)
    cf = CourseForm.objects.get(name="Peer Eval ✅")
    assert cf is not None

# ------------------- Endpoint Tests -------------------

# GET requests

#check if unlogged in users get moved
def test_get_endpoint_requires_login(client, create_form_url):
    resp = client.get(create_form_url)
    assert resp.status_code in (301, 302)
    assert "next=" in resp.url

#check if owning professor can access form creation
def test_get_endpoint_professor_access(client, professor_user, create_form_url):
    client.force_login(professor_user)
    resp = client.get(create_form_url)
    assert resp.status_code == 200
    # Check context variables exist
    assert "default_colors" in resp.context
    assert "forms" in resp.context

#check if students can access form creation
def test_get_endpoint_student_forbidden(client, student_user, create_form_url):
    client.force_login(student_user)
    resp = client.get(create_form_url, follow=True)
    messages = [m.message for m in get_messages(resp.wsgi_request)]
    assert any("Access denied" in m for m in messages)
    assert resp.status_code == 200


# POST requests

#check if professors can create forms
def test_post_endpoint_create_form_success(client, professor_user, create_form_url):
    client.force_login(professor_user)
    payload = {
        "form_name": "Endpoint Test Form",
        "num_likert": "2",
        "num_open_ended": "1",
        "self_evaluate": "on",
    }
    resp = client.post(create_form_url, data=payload, follow=True)
    assert resp.status_code == 200
    form = CourseForm.objects.get(name="Endpoint Test Form")
    assert form.num_likert == 2
    assert form.num_open_ended == 1

#check if students can create forms (shouldn't be able to)
def test_post_endpoint_student_forbidden(client, student_user, create_form_url):
    client.force_login(student_user)
    payload = {"form_name": "Student Try", "num_likert": "1", "num_open_ended": "0"}
    resp = client.post(create_form_url, data=payload, follow=True)
    assert resp.status_code == 200
    assert CourseForm.objects.filter(name="Student Try").count() == 0
    messages = [m.message for m in get_messages(resp.wsgi_request)]
    assert any("Access denied" in m for m in messages)

#check if messed up date can create a form
def test_post_endpoint_invalid_data(client, professor_user, create_form_url):
    client.force_login(professor_user)
    payload = {"form_name": "Invalid Date Form", "due_datetime": "not-a-date"}
    resp = client.post(create_form_url, data=payload, follow=True)
    assert resp.status_code == 200
    assert CourseForm.objects.filter(name="Invalid Date Form").count() == 0
    messages = [m.message for m in get_messages(resp.wsgi_request)]
    assert any("Invalid date/time" in m for m in messages)


# Endpoint redirect behavior

#check what happens after submitting a form
def test_post_endpoint_redirects_to_course_page(client, professor_user, course):
    client.force_login(professor_user)
    url = reverse("create_form", args=[course.join_code])
    payload = {"form_name": "Redirect Test", "num_likert": "1", "num_open_ended": "0"}
    resp = client.post(url, data=payload)
    assert resp.status_code in (301, 302)
    assert course.join_code in resp.url