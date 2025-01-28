import random
import string
from uuid import uuid4

class Games:
    active_games = {} #Przechowuje aktywne gry
    finished_games = {}


    @classmethod
    def create_game(cls):
        game = Game()
        cls.active_games[game.game_code] = game
        return game

    @classmethod
    def get_game(cls, game_code):
        return cls.active_games.get(game_code)

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
        self.winner =  None
        self.deck = CARDS.copy()
        self.deck = CARDS.copy()  # Skopiowana lista kart dostępnych w grze
        self.available_cards = self.draw_initial_cards()  # Karty dostępne do kupienia
        self.logs = []  # Lista do przechowywania logów akcj

    def draw_initial_cards(self):
        # Wybiera np. 3 karty z talii na start gry
        return random.sample(self.deck, 3)

    def replace_card(self, card):
        # Zastąp kartę po zakupie nową kartą z talii
        if card in self.available_cards:
            self.available_cards.remove(card)
            if self.deck:
                new_card = random.choice(self.deck)
                self.available_cards.append(new_card)
                self.deck.remove(new_card)
                self.add_log(f"New card available: {new_card.name}")

    def add_log(self, message):
        # Dodaje wiadomość do logów gry i ogranicza liczbę logów
        self.logs.append(message)
        if len(self.logs) > 3:
            self.logs.pop(0)  # Usuń najstarszą wiadomość, jeśli jest ich za dużo

    def add_player(self, player):
        if len(self.players) < 6:
            self.players.append(player)
            self.add_log(f"Player {player.nickname} joined")
        else:
            raise Exception('Too many players')

    def start_game(self):
        self.status = 'playing'

        self.add_log("Game started")
        self.add_log(f"It's {self.players[0].nickname}'s turn!")


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

        self.add_log(f"Now it's {current_player.nickname}'s turn!")



    def generate_game_code(self):
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            if code not in Games.active_games:
                return code

    def get_current_player(self):
        return self.players[self.current_turn]

    def check_end_game(self):
        # Sprawdź, czy któryś gracz zdobył 20 punktów zwycięstwa
        winner = next((player for player in self.players if player.victory >= 20), None)
        if winner:
            self.status = 'finished'
            self.winner = winner  # Przechowujemy zwycięzcę
            self.add_log(f"Game ended")
            return True

        # Sprawdź, czy został tylko jeden aktywny gracz
        active_players = [player for player in self.players if player.is_active]
        if len(active_players) == 1:
            self.status = 'finished'
            self.winner = active_players[0]
            return True

        return False

    @staticmethod
    def roll_dice(num_dice=6):
        return [random.choice(DICE) for _ in range(num_dice)]



class Player:
    MAX_HEALTH = 10
    MAX_VICTORY = 20

    def __init__(self, nickname, monster):
        self.id = uuid4()
        self.nickname = nickname
        self.monster = monster
        self.health = 3 #self.MAX_HEALTH
        self.victory = 0
        self.energy = 10 #0
        self.in_tokyo = False
        self.is_active = True
        self.dice_result = []
        self.kept_dice = []
        self.roll_count = 0
        self.was_attacked = False
        self.displayed_dice = []

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
        if self.energy <= 0:
            self.energy = 0

    def roll_player_dice(self):
        self.dice_result = []
        num_dice_to_roll = 6 - len(self.kept_dice)
        result = Game.roll_dice(num_dice_to_roll)
        self.dice_result += result
        self.roll_count += 1
        self.displayed_dice=self.dice_result

    def save_results(self, game):
        counts = {die.name: sum(d.name == die.name for d in self.kept_dice) for die in DICE}

        self.gain_energy(counts.get("energy", 0))

        if not self.in_tokyo:
            self.gain_health(counts.get("heart", 0))

        for num in ["1", "2", "3"]:
            count = counts.get(num, 0)
            if count >= 3:
                self.gain_victory(int(num))  # Dodaje punkty równe wartości symbolu
                self.gain_victory(count-3) # Za każdą dodatkową kość powyżej 3: dodaje 1 punkt zwycięstwa

        if counts.get("attack", 0) > 0:
            game.attacking_player = self
            if self.in_tokyo:
                game.add_log(f'{self.nickname} attacked everyone outside Tokyo!')
                # Gracz w Tokio zadaje obrażenia wszystkim poza Tokio
                for player in game.players:
                    if not player.in_tokyo:
                        player.take_damage(counts["attack"])
            else:
                # Gracz poza Tokio zadaje obrażenia graczowi w Tokio
                game.add_log(f'{self.nickname} attacked Tokyo player!')
                for player in game.players:
                    if player.in_tokyo:
                        player.take_damage(counts["attack"])
                        player.was_attacked = True
                        break
        else:
            game.attacking_player = None
            self.was_attacked = False

    def buy_card(self, card, game):
        if self.energy >= card.cost:
            self.energy -= card.cost
            card.effect(self, game)  # Aktywuj efekt karty
            game.replace_card(card)
            game.add_log(f"{self.nickname} bought card {card.name}")
        else:
            raise Exception("Not enough energy to buy this card.")


class Monster:
    def __init__(self, name, image):
        self.name = name
        self.image = image

# Stała lista potworów
MONSTERS = {
    "gigazaur": Monster(name="Gigazaur", image="images/monster1.png"),
    "mekadragon": Monster(name="Meka Dragon", image="images/monster2.png"),
    "thekraken": Monster(name="The Kraken", image="images/monster3.png"),
    "cyberbunny": Monster(name="Cyber Bunny", image="images/monster4.png"),
    "alienoid": Monster(name="Alienoid", image="images/monster5.png"),
    "spacepenguin": Monster(name="Space Penguin", image="images/monster6.png"),
}


class Die:
    def __init__(self, name, image):
        self.name = name
        self.image = image


# Przykładowe kostki
DICE = [
    Die(name="1", image="images/dice1.png"),
    Die(name="2", image="images/dice2.png"),
    Die(name="3", image="images/dice3.png"),
    Die(name="heart", image="images/dice_heart.png"),
    Die(name="attack", image="images/dice_attack.png"),
    Die(name="energy", image="images/dice_energy.png"),
]


class Card:
    def __init__(self, name, cost, effect, description):
        self.name = name
        self.cost = cost
        self.effect = effect
        self.description = description

CARDS = [
    Card(
        name="Extra Claw",
        cost=3,
        effect=lambda player, game: [p.take_damage(1) for p in game.players if p.id != player.id and p.is_active],
        description="Attack all players (health -1)."
    ),
    Card(
        name="Health Boost",
        cost=4,
        effect=lambda player, game: player.gain_health(2),
        description="Gain 2 health."
    ),
    Card(
        name="Energy Drain",
        cost=2,
        effect=lambda player, game: [p.gain_energy(-3) for p in game.players if p.id != player.id and p.is_active],
        description="Remove 3 energy from opponents."
    ),
    Card(
        name="Group Heal",
        cost=3,
        effect=lambda player, game: [p.gain_health(1) for p in game.players if p.is_active],
        description="All players gain 1 health."
    ),
    Card(
        name="Overcharge",
        cost=2,
        effect=lambda player, game: [player.gain_energy(6), player.take_damage(2)],
        description="Gain 6 energy, but take 2 damage."
    ),
    Card(
        name="Piercing Strike",
        cost=5,
        effect=lambda player, game: [p.take_damage(2) for p in game.players if p.id != player.id and p.is_active],
        description="Attack all opponents (health -2)."
    ),
    Card(
        name="Life Leech",
        cost=5,
        effect=lambda player, game: [
            p.take_damage(1) for p in game.players if p.id != player.id and p.is_active
            ] + [player.gain_health(sum(1 for p in game.players if p.id != player.id and p.is_active))],
        description="Steal 1 health from all opponents."
    ),
    Card(
        name="Reinforcements",
        cost=6,
        effect=lambda player, game: [player.gain_health(3), player.gain_victory(1)],
        description="Gain 3 health and 1 victory."
    ),
    Card(
        name="Equalizer",
        cost=6,
        effect=lambda player, game: [
            p.gain_energy(player.energy - p.energy) for p in game.players if p.is_active
        ],
        description="Equalize energy among all players."
    ),
    Card(
        name="Chaos Wave",
        cost=7,
        effect=lambda player, game: [
                                        p.take_damage(3) for p in game.players
                                    ] + [p.gain_energy(-3) for p in game.players],
        description="Damage all players (health -3) and drain 3 energy."
    ),
    Card(
        name="Victory Rush",
        cost=7,
        effect=lambda player, game: player.gain_victory(3),
        description="Gain 3 victory points."
    ),
    Card(
        name="Sacrificial Pact",
        cost=3,
        effect=lambda player, game: [player.take_damage(5), player.gain_victory(3)],
        description="Lose 5 health to gain 3 victory points."
    )


]