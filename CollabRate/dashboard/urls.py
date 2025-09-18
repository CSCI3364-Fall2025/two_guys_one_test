from django.urls import path
from . import views

urlpatterns = [
   path('', views.dashboard, name='dashboard'),
   path('courses/join/', views.join_course, name='join_course'),
   path('courses/create/', views.create_course, name='create_course'),
   path('courses/leave/<str:join_code>/', views.leave_course, name='leave_course'),
   path('courses/delete/<str:join_code>/', views.delete_course, name='delete_course'),
   path('courses/invite/<str:join_code>/<str:token>/', views.course_invite, name='course_invite'),
   path('results/<str:course_code>/<str:delivery_number>/', views.peer_results, name='peer_results'),]
