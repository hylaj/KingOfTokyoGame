from django.urls import path
from . import views

urlpatterns = [
    #    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('game_rules/', views.game_rules, name='game_rules'),
    path('join_game/', views.create_form_join_game, name='join_game'),
    path('create_game/', views.create_new_game, name='create_game'),
    path('rejoin_game/', views.rejoin_game, name='rejoin_game'),
    path('wait_for_game', views.wait_for_game, name='wait_for_game'),
    path('gameplay', views.gameplay, name='gameplay'),
    path("check_game_status", views.check_game_status, name="check_game_status"),
    path("get_players", views.get_players, name="get_players"),
    path("get_gameplay_data", views.get_gameplay_data, name="get_gameplay_data"),
    path("get_tokyo_player", views.get_tokyo_player, name="get_tokyo_player"),
    path("start_game", views.start_game, name="start_game"),
    path('check_current_player', views.check_current_player, name='check_current_player'),
    path('gameplay_view', views.gameplay_view, name='gameplay_view'),
    path('end_turn', views.end_turn, name='end_turn'),
    path('end_game/', views.end_game, name='end_game'),
    path('eliminated_player_view/', views.eliminated_player_view, name='eliminated_player_view'),
    path('leave_tokyo', views.leave_tokyo, name='leave_tokyo'),
]