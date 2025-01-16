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
        self.tokyo_player = None
        self.show_roll = True
        self.attacking_player = None

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

        self.show_roll = True

        self.current_turn = (self.current_turn + 1) % len(self.players)
        while not self.players[self.current_turn].is_active:
            self.current_turn = (self.current_turn + 1) % len(self.players)

        # Gracz zdobywa +2 pkt na poczatku swojej tury w Tokio
        current_player = self.players[self.current_turn]
        if current_player.in_tokyo is True:
            current_player.gain_victory(2)



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
        self.dice_result = []
        self.kept_dice = []
        self.roll_count = 0
        self.was_attacked = False

    def take_damage(self, amount):
        self.health = max(0, self.health - amount)
        if self.health == 0:
            self.is_active = False

    def gain_health(self, amount):
        self.health = self.health + amount
        if self.health >= self.MAX_HEALTH:
            self.health = self.MAX_HEALTH

    def gain_victory(self, amount):
        self.victory = self.victory + amount
        if self.victory >= self.MAX_VICTORY:
            self.victory = self.MAX_VICTORY
            return redirect('end_game')

    def gain_energy(self, amount):
        self.energy += amount

    def roll_player_dice(self):
        self.dice_result = []
        num_dice_to_roll = 6 - len(self.kept_dice)
        result = Game.roll_dice(num_dice_to_roll)
        self.dice_result += result
        self.roll_count += 1



    def save_results(self, game):
        counts = {symbol: self.kept_dice.count(symbol) for symbol in ["1", "2", "3", "heart", "attack", "energy"]}

        self.gain_energy(counts["energy"])

        if not self.in_tokyo:
            self.gain_health(counts["heart"])

        for num in ["1", "2", "3"]:
            count = counts[num]
            if count >= 3:
                self.gain_victory(int(num))  # Dodaje punkty równe wartości symbolu
                self.gain_victory(count-3) # Za każdą dodatkową kość powyżej 3: dodaje 1 punkt zwycięstwa

        if counts["attack"] > 0:
            game.attacking_player = self
            if self.in_tokyo:
                # Gracz w Tokio zadaje obrażenia wszystkim poza Tokio
                for player in game.players:
                    if not player.in_tokyo:
                        player.take_damage(counts["attack"])
            else:
                # Gracz poza Tokio zadaje obrażenia graczowi w Tokio
                for player in game.players:
                    if player.in_tokyo:
                        player.take_damage(counts["attack"])
                        player.was_attacked = True
                        break


class Monster:
    def __init__(self, id, name, image):
        self.id = id
        self.image = image #dodać scieżke do obrazka
        self.name = name

def home(request):
    return render(request, 'home.html')

def game_rules(request):
    return render(request, 'game_rules.html')


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
            elif game.status == 'playing':
                messages.error(request, 'Game in progress. Cannot join.')
            elif game.status == 'finished':
                messages.error(request, 'Game is already finished. Cannot join.')
            elif len(game.players) >= 6:
                messages.error(request, "The game is already full.")
            elif any(player.nickname.lower() == nickname.lower() for player in game.players):
                messages.error(request, "The nickname is already taken in this game. Please choose another one.")
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

#Ponowne dołączanie do gry
def rejoin_game(request):
    # Sprawdź, czy w sesji są zapisane dane gracza i gry
    player_id = request.session.get("player_id")
    game_code = request.session.get("game_code")

    if player_id and game_code:
        # Sprawdź, czy gra istnieje
        game = Games.get_game(game_code)
        if game:
            # Sprawdź, czy gracz jest częścią tej gry
            player = next((p for p in game.players if str(p.id) == player_id), None)
            if player:
                # Gracz i gra istnieją - przekieruj do gry
                return redirect("gameplay", game_code=game_code)
            else:
                # Jeśli gracz nie istnieje w grze, usuń dane z sesji
                del request.session["player_id"]
                del request.session["game_code"]
                messages.error(request, "Your session is invalid. Please join the game again.")
        else:
            # Jeśli gra nie istnieje, usuń dane z sesji
            del request.session["player_id"]
            del request.session["game_code"]
            messages.error(request, "The game does not exist. Please join a new game.")
    else:
        # Jeśli brakuje danych w sesji
        messages.error(request, "No active session found. Please join a game.")

    # Przekierowanie na stronę główną lub do formularza dołączenia
    return redirect("home")



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
        return redirect('gameplay', game_code=game_code)


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

    viewing_player_id = request.session.get("player_id")
    viewing_player = next((player for player in game.players if str(player.id) == viewing_player_id), None)
    current_player = game.get_current_player()

    if str(current_player.id) != str(viewing_player_id):
        messages.error(request, "Not your turn")
        return redirect("gameplay_view", game_code=game_code)

    if request.method == 'POST':
        if 'roll_dice_btn' in request.POST:
            current_player.roll_player_dice()
            game.show_roll = False
            if current_player.roll_count == 3:
                current_player.kept_dice.extend(current_player.dice_result)
            if game.tokyo_player is None and "attack" in current_player.dice_result: #Pierwszy gracz, który na początku gry wyrzuci co najmniej jeden symbol ataku przemieszcza swój pionek do Tokio
                game.tokyo_player = current_player
                current_player.in_tokyo = True
                current_player.gain_victory(1) #Gracz zyskuje 1 pkt kiedy wchodzi do Tokio

        if 'save_dice_btn' in request.POST:
            selected_dice = request.POST.getlist("kept_dice", [])
            current_player.kept_dice.extend(selected_dice)
            game.show_roll = True

    if len(current_player.kept_dice) == 6:
        current_player.save_results(game)

    return render(request, 'gameplay.html',{
        "players": game.players,
        "game_code": game.game_code,
        "viewing_player": viewing_player,
        "current_player": current_player,
        'dice': current_player.dice_result,
        'selected_dice': current_player.kept_dice,
        'show_roll': game.show_roll,
        'game': game,
    })

def gameplay_view(request, game_code):
    game = Games.get_game(game_code)

    if not game:
        messages.error(request, "Game not found")
        return redirect("home")

    viewing_player_id = request.session.get("player_id")
    viewing_player = next((player for player in game.players if str(player.id) == viewing_player_id), None)
    current_player = game.get_current_player()

    if current_player==viewing_player:
        return redirect('gameplay', game_code=game_code)

    return render(request, 'gameplay_view.html',{
        "players": game.players,
        "game_code": game.game_code,
        "viewing_player": viewing_player,
        "current_player": current_player,
        'dice': current_player.dice_result,
        'selected_dice': current_player.kept_dice,
        'game': game,
    })

def get_gameplay_data(request, game_code):
    game = Games.get_game(game_code)
    if not game:
        messages.error(request, "Game not found")
        return redirect("home")

    viewing_player_id = request.session.get("player_id")
    viewing_player = next((player for player in game.players if str(player.id) == viewing_player_id), None)
    current_player = game.get_current_player()

    gameplay_data_html = render_to_string("partials/gameplay_data.html", {
        "players": game.players,
        "game_code": game.game_code,
        "viewing_player": viewing_player,
        "current_player": current_player,
        'dice': current_player.dice_result,
        'selected_dice': current_player.kept_dice,
        'game': game,
    })
    return HttpResponse(gameplay_data_html)

def get_tokyo_player(request, game_code):
    game = Games.get_game(game_code)
    if not game:
        messages.error(request, "Game not found")
        return redirect("home")

    tokyo_player_html=render_to_string("partials/get_tokyo_player.html", {
        "game": game,
    })
    return HttpResponse(tokyo_player_html)


def leave_tokyo(request, game_code):
    game = Games.get_game(game_code)
    if not game:
        messages.error(request, "Game not found")
        return redirect("home")

    viewing_player_id = request.session.get("player_id")
    viewing_player = next((player for player in game.players if str(player.id) == viewing_player_id), None)

#gracz może opuścić Tokio po ataku przez innego gracza w trakcie tury innego gracza lub na początku własnej tury, przed rzutem kostkami
    if viewing_player.was_attacked and viewing_player.roll_count == 0:
        viewing_player.in_tokyo = False
        game.attacking_player.in_tokyo = True
        game.tokyo_player = game.attacking_player
        game.attacking_player.gain_victory(1) #Gracz zyskuje 1 pkt za wejscie do Tokio
        viewing_player.was_attacked = False
    else:
        messages.warning(request, "You can't leave Tokyo now")
    return redirect('gameplay_view', game_code=game_code)




def check_current_player(request, game_code):
    game = Games.get_game(game_code)
    if not game:
        messages.error(request, "Game not found")
        return redirect("home")

    current_player = game.get_current_player()
    current_player_id = str(current_player.id)
    viewing_player_id = request.session.get("player_id")

    return JsonResponse({
        "currentPlayer": current_player_id,
        "viewingPlayer": viewing_player_id,
    })

def end_turn(request, game_code):
    game = Games.get_game(game_code)
    if not game:
        messages.error(request, "Game not found")
        return redirect("home")
    current_player = game.get_current_player()
    if len(current_player.kept_dice) == 6:
        game.next_turn()
        return redirect('gameplay_view', game_code=game_code)
    else:
        messages.info(request, "Roll the dice to complete your turn.")
        return redirect('gameplay', game_code=game_code)

def end_game(request):
    game_code=request.session.get("game_code")
    game = Games.get_game(game_code)
    game.status = 'finished'
    Games.delete_game(game.game_code)




