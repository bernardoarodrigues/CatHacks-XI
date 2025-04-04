import flappy_bird_gymnasium
import gymnasium as gym
import threading

class GameManager:
    def __init__(self):
        self.env = gym.make("FlappyBird-v0", render_mode="rgb_array")
        self.players = {}
        self.lock = threading.Lock()

    def add_player(self, player_id):
        with self.lock:
            self.players[player_id] = {
                "observation": self.env.reset()[0],
                "score": 0,
                "alive": True
            }

    def remove_player(self, player_id):
        with self.lock:
            if player_id in self.players:
                del self.players[player_id]

    def update_player_action(self, player_id, action):
        with self.lock:
            if player_id in self.players and self.players[player_id]["alive"]:
                obs, reward, done, _, _ = self.env.step(action)
                self.players[player_id]["observation"] = obs
                self.players[player_id]["score"] += reward
                self.players[player_id]["alive"] = not done

    def get_game_state(self):
        with self.lock:
            return {
                player_id: {
                    "observation": player_data["observation"],
                    "score": player_data["score"],
                    "alive": player_data["alive"]
                }
                for player_id, player_data in self.players.items()
            }