from django.urls import path
from . import views

urlpatterns = [
    path('<str:join_code>/', views.course_detail, name='course_detail'),

    path('<str:join_code>/groups/', views.groups, name='groups'),
    path('<str:join_code>/group/create/', views.create_team, name='create_team'),
    path('<str:join_code>/group/delete/<int:team_id>/', views.delete_team, name='delete_team'),

    path('<str:join_code>/form/create/', views.create_form, name='create_form'),
    path('<str:join_code>/form/<int:course_form_id>/edit/info/', views.edit_info, name='edit_info'),
    path('<str:join_code>/form/<int:course_form_id>/edit/questions/', views.draft_questions, name='draft_questions'),
    path('<str:join_code>/form/<int:course_form_id>/responses/', views.view_form_responses, name='view_form_responses'),
    path('<str:join_code>/form/<int:course_form_id>/delete', views.delete_form, name='delete_form'),

    
    path('<str:join_code>/form/view/', views.view_forms, name='view_forms'),
    path('<str:join_code>/form/edit/<int:form_id>/', views.edit_form, name='edit_form'),

    path('<str:join_code>/', views.course_detail, name='course_detail'),

    path('<str:join_code>/form/edit/<int:course_form_id>/update_response/<int:response_id>/', views.update_open_ended_response, name='update_open_ended_response'),

    #debug paths
    path('course/<str:join_code>/clear/', views.clear_course_forms, name='clear_course_forms'),

    # For students answering form
    path('<str:join_code>/form/<int:form_id>/answer', views.answer_form, name='answer_form'),

    # Peer results
    path('peer_results/<str:join_code>/<int:form_id>/', views.peer_results, name='peer_results'),
]
