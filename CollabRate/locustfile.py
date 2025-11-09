import os
import random

from locust import HttpUser, task, between
from locust.exception import RescheduleTask

# ---------- Django setup ----------
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings")

import django
django.setup() 

from accounts.models import CustomUser


# ---------- Constants ----------
PASSWORD = "Passw0rd!"
LOGIN_URL = "/accounts/login/"
DASHBOARD_URL = "/dashboard/"


# Pre-load usernames from DB
STUDENT_USERNAMES = list(
    CustomUser.objects.filter(user_type=CustomUser.STUDENT)
    .values_list("username", flat=True)
)
PROFESSOR_USERNAMES = list(
    CustomUser.objects.filter(user_type=CustomUser.PROFESSOR)
    .values_list("username", flat=True)
)


def pick_username(usernames):
    """
    Pick a random username from a non-empty list.
    Raise RescheduleTask if list is empty so Locust doesn’t break.
    """
    if not usernames:
        raise RescheduleTask("No users available in the database for this user type")
    return random.choice(usernames)


class BaseDjangoUser(HttpUser):
    """
    Shared logic for StudentUser and ProfessorUser.
    Handles login in on_start and then exposes a task that hits the dashboard.
    """

    abstract = True
    wait_time = between(1, 3)
    username_list = None

    def on_start(self):
        """
        Called once when a simulated user starts.
        Choose a username from DB
        Load the login page to get CSRF token
        POST credentials
        Confirm we can reach the dashboard
        """
        if self.username_list is None:
            raise RescheduleTask("No username list configured for this user type")
        if not self.username_list:
            raise RescheduleTask("No users available in the database for this user type")

        username = pick_username(self.username_list)

        # GET login page to set CSRF cookie
        with self.client.get(
            LOGIN_URL,
            name="GET /accounts/login/",
            catch_response=True,
        ) as resp:
            if resp.status_code != 200:
                resp.failure(
                    f"[LOGIN GET] status={resp.status_code}, "
                    f"body={resp.text[:200]!r}"
                )
                raise RescheduleTask("login-page-failed")

        # CSRF token is stored in cookie 'csrftoken'
        csrftoken = self.client.cookies.get("csrftoken", "")

        # POST login form
        login_data = {
            "login": username,
            "password": PASSWORD,
            "csrfmiddlewaretoken": csrftoken,
        }
        headers = {
            "Referer": self.client.base_url + LOGIN_URL,
        }

        with self.client.post(
            LOGIN_URL,
            data=login_data,
            headers=headers,
            name="POST /accounts/login/",
            allow_redirects=True,
            catch_response=True,
        ) as resp:
            if resp.status_code not in (200, 302):
                resp.failure(
                    f"[LOGIN POST] user={username}, status={resp.status_code}, "
                    f"body={resp.text[:200]!r}"
                )
                raise RescheduleTask(f"login-post-failed-{resp.status_code}")

        # Hit dashboard to confirm login/redirect worked
        with self.client.get(
            DASHBOARD_URL,
            name="GET /dashboard/",
            catch_response=True,
        ) as resp:
            if resp.status_code != 200:
                resp.failure(
                    f"[DASHBOARD GET] user={username}, status={resp.status_code}, "
                    f"body={resp.text[:200]!r}"
                )
                raise RescheduleTask("dashboard-failed")
            else:
                resp.success()

    @task
    def dashboard(self):
        """
        Simple steady-state task: after login, keep hitting dashboard
        to generate load on the main page.
        """
        self.client.get(DASHBOARD_URL, name="GET /dashboard/")


class StudentUser(BaseDjangoUser):
    """
    Locust user that logs in as a student.
    """
    username_list = STUDENT_USERNAMES


class ProfessorUser(BaseDjangoUser):
    """
    Locust user that logs in as a professor.
    """
    username_list = PROFESSOR_USERNAMES
