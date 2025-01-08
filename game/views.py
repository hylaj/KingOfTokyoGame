import random
import string
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, redirect
from uuid import uuid4
from .forms import JoinGameForm, CreateGameForm
from django.template.loader import render_to_string
from django.http import HttpResponse

class Games:
    active_games = {} #Przechowuje aktywne gry

    @classmethod
    def create_game(cls):
        game = Game()
        cls.active_games[game.game_code] = game
        return game

    @classmethod
    def get_game(cls, game_code):
        return cls.active_games.get(game_code)

    @classmethod
    def delete_game(cls, game_code):
        if game_code in cls.active_games:
            del cls.active_games[game_code]

class Game:
    def __init__(self):
        self.id = uuid4()
        self.game_code = self.generate_game_code()
        self.status = 'waiting'
        self.current_turn = 0
        self.players = []

    def add_player(self, player):
        if len(self.players) < 6:
            self.players.append(player)
        else:
            raise Exception('Too many players')

    def start_game(self):
        self.status = 'playing'

    def next_turn(self):
        current_player = self.players[self.current_turn]
        current_player.dice_result = []
        current_player.kept_dice = []
        current_player.roll_count = 0

        self.current_turn = (self.current_turn + 1) % len(self.players)
        while not self.players[self.current_turn].is_active:
            self.current_turn = (self.current_turn + 1) % len(self.players)



    def generate_game_code(self):
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            if code not in Games.active_games:
                return code

    def get_current_player(self):
        return self.players[self.current_turn]

    @staticmethod
    def roll_dice(num_dice=6):
        symbols = ["1", "2", "3", "heart", "attack", "energy"]
        return [random.choice(symbols) for _ in range(num_dice)]


class Player:
    MAX_HEALTH = 10
    MAX_VICTORY = 20

    def __init__(self, nickname, monster):
        self.id = uuid4()
        self.nickname = nickname
        self.monster = monster
        self.health = self.MAX_HEALTH
        self.victory = 0
        self.energy = 0
        self.in_tokyo = False
        self.is_active = True
        self.kept_dice = []
        self.roll_count = 0

    def take_damage(self, amount):
        self.health = max(0, self.health - amount)
        if self.health == 0:
            self.is_active = False

    def gain_health(self, amount):
        self.health = max(self.MAX_HEALTH, self.health + amount)

    def gain_victory(self, game, amount):
        self.victory = max(self.MAX_VICTORY, self.victory + amount)
        if self.victory == self.MAX_VICTORY:
            game.status = 'finished'
            Games.delete_game(game.game_code)
        #dokonczyc - przekierowanie na stornę konca gry wszystkich graczy

    def gain_energy(self, amount):
        self.energy += amount


class Monster:
    def __init__(self, id, name, image):
        self.id = id
        self.image = image #dodać scieżke do obrazka
        self.name = name

def home(request):
    return render(request, 'home.html')


# Funkcja do obsługi formularza dołączania do gry
def create_form_join_game(request):
    form = JoinGameForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            game_code = form.cleaned_data["game_code"]
            nickname = form.cleaned_data["nickname"]
            chosen_monster = form.cleaned_data["monster"]

            # Sprawdzenie, czy gra istnieje
            game = Games.get_game(game_code)
            if not game:
                messages.error(request, 'Given game code does not exist')
            elif len(game.players) >= 6:
                messages.error(request, "The game is already full.")
            elif any(player.monster == chosen_monster for player in game.players):
                messages.error(request, "The chosen monster is already taken.")
            else:
                # Dodanie gracza do gry
                new_player = Player(nickname, chosen_monster)
                game.add_player(new_player)
                request.session["player_id"] = str(new_player.id)
                request.session["game_code"] = game.game_code

                return redirect("wait_for_game", game_code=game.game_code)

    # Jeśli formularz nie jest poprawny lub wystąpił błąd, renderujemy stronę z błędami
    return render(request, "join_game.html", {"form": form})


def create_new_game(request):
    form = CreateGameForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            nickname = form.cleaned_data["nickname"]
            monster_name = form.cleaned_data["monster"]

            # Tworzenie nowej gry
            game = Games.create_game()
            request.session["game_code"] = game.game_code

            # Dodanie gracza jako pierwszego uczestnika
            new_player = Player(nickname, monster_name)
            game.add_player(new_player)
            request.session["player_id"] = str(new_player.id)

            return redirect("wait_for_game", game_code=game.game_code)
        else:
            messages.error(request, "Invalid form data. Please check your input.")

    # Renderowanie strony w przypadku GET lub błędu w formularzu
    return render(request, "create_game.html", {"form": form})


def wait_for_game(request, game_code):
    game = Games.get_game(game_code)
    if not game:
        messages.error(request, 'Given game code does not exist')
        return redirect("home")
    if game.status == "playing":
        return redirect("gameplay", game_code=game_code)

    player_id = request.session.get("player_id")
    current_player = next((player for player in game.players if str(player.id) == player_id), None)

    return render(request, "wait_for_game.html", {
        "players": game.players,
        "game_code": game.game_code,
        "current_player": current_player
    })

def gameplay(request, game_code):
    game = Games.get_game(game_code)

    if not game:
        messages.error(request, "Game not found")
        return redirect("home")

    if game.status != 'playing':
        if game.status == 'waiting':
            messages.error(request, "This game has not started yet")
            return redirect("wait_for_game", game_code=game_code)
        elif game.status == 'finished':
            messages.error(request, "This game is finished")
            return redirect("home")

    player_id = request.session.get("player_id")
    current_player = next((player for player in game.players if str(player.id) == player_id), None)

    return render(request, 'gameplay.html',{
        "players": game.players,
        "game_code": game.game_code,
        "current_player": current_player
    })

def start_game(request, game_code):
    game = Games.get_game(game_code)
    player_id = request.session.get("player_id")

    if not game:
        messages.error(request, "Game not found")
        return redirect("home")
    if len(game.players) < 2: #Musi być minimum 2 graczy, aby rozpocząć rozgrywkę
        messages.error(request, "Too few players.")
        return redirect("wait_for_game", game_code=game_code)
    if str(game.players[0].id) == player_id:  # Tylko twórca gry może ją rozpocząć
        game.start_game()
        redirect('gameplay', game_code=game_code)

def roll_dice(request, game_code):
    game = Games.get_game(game_code)
    if not game:
        messages.error(request, "Game not found")
        return redirect("home")

    session_player_id = request.session.get("player_id")
    current_player = game.get_current_player()

    if str(current_player.id) != session_player_id:
        messages.error(request, "Not your turn")
        return render(request, "partials/roll_dice.html", {"game_code": game.game_code})

    kept_dice = request.POST.getlist("kept_dice", [])
    if kept_dice:
        current_player.kept_dice.append(kept_dice)

    if current_player.roll_count >= 3:
        messages.info(request, "You have already rolled 3 times")
        game.next_turn()
        return render(request, "partials/roll_dice.html", {"game_code": game.game_code})

    num_dice_to_roll = 6 - len(current_player.kept_dice)
    current_player.dice_result = Game.roll_dice(num_dice=num_dice_to_roll)
    current_player.roll_count += 1

    if current_player.roll_count == 3:
        game.next_turn()

    request.session["dice_result"] = current_player.dice_result

    return render(request, 'partials/roll_dice.html', {
        "player": current_player,
        "kept_dice": current_player.kept_dice,
        "dice_result": current_player.dice_result,
        "game_code": game.game_code
    })

def check_game_status(request, game_code):
    game = Games.get_game(game_code)
    if not game:
        messages.error(request, "Game not found")
        return redirect("home")
    return JsonResponse({"status": game.status})


def get_players(request, game_code):
    game = Games.get_game(game_code)
    if not game:
        messages.error(request, "Game not found")
        return redirect("home")

    players_html = render_to_string("partials/players_list.html", {"players": game.players})
    return HttpResponse(players_html)