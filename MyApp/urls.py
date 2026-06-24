from django.urls import path

from . import views

urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('policies/', views.PoliciesView.as_view(), name='policies'),
    path('orchestra/', views.OrchestraView.as_view(), name='orchestra'),
    path('plan/', views.PlanView.as_view(), name='plan'),
    path('try-on/', views.TryOnView.as_view(), name='try_on'),
]
