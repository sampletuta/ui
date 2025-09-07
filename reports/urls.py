from django.urls import path
from .views import download_comments_pdf_view

app_name = 'reports'

urlpatterns = [
    path('comments/<str:entity_type>/<uuid:entity_id>/download/', download_comments_pdf_view, name='download_comments_pdf'),
]




