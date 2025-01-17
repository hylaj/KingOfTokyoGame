import random
import string
from uuid import uuid4

class Monster:
    def __init__(self, name, image):
        self.name = name
        self.image = image

# Stała lista potworów
MONSTERS = {
    "gigazaur": Monster(name="Gigazaur", image="static/images/gigazaur.jpg"),
    "mekadragon": Monster(name="Meka Dragon", image="static/images/mekadragon.jpg"),
    "thekraken": Monster(name="The Kraken", image="static/images/thekraken.jpg"),
    "cyberbunny": Monster(name="Cyber Bunny", image="static/images/cyberbunny.jpg"),
    "alienoid": Monster(name="Alienoid", image="static/images/alienoid.jpg"),
    "spacepenguin": Monster(name="Space Penguin", image="static/images/spacepenguin.jpg"),
}

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
