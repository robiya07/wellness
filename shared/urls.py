from django.urls import path
from .views import DishAnalysisView

app_name = "shared"

urlpatterns = [
    path('api/analyze-dish/', DishAnalysisView.as_view(), name='analyze-dish'),
]
