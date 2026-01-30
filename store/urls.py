from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name="home"),
    path('indexGen/', views.indexGen, name="indexGen"),
    path('maintX/', views.maintX, name="maintX"),
    path('mycourse/', views.mycourse, name="mycourse"),
    path('login/', views.login_view, name="login"),
    path('register/', views.register_view, name="register"),
    path('logout/', views.logout_view, name="logout"),
    path('create_course/', views.create_course, name="create_course"),
    
    # API endpoints for AJAX requests
    path('api/register/', views.register_api, name="register_api"),
    path('api/login/', views.login_api, name="login_api"),
    



    
]