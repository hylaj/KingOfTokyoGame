from django.urls import path
from . import views

urlpatterns = [
    #    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('join_game/', views.create_form_join_game, name='join_game'),
    path('create_game/', views.create_new_game, name='create_game'),
    path('wait_for_game/<str:game_code>/', views.wait_for_game, name='wait_for_game'),
    path('gameplay/<str:game_code>/', views.gameplay, name='gameplay'),
    path('roll_dice/<str:game_code>/', views.roll_dice, name='roll_dice'),
    path("check_game_status/<str:game_code>/", views.check_game_status, name="check_game_status"),
    path("get_players/<str:game_code>/", views.get_players, name="get_players"),
    path("start_game/<str:game_code>/", views.start_game, name="start_game")

]