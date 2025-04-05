import flappy_bird_gymnasium
import gymnasium as gym
import threading
import numpy as np
import base64
from io import BytesIO
from PIL import Image

class GameManager:
    def __init__(self):
        self.env = gym.make("FlappyBird-v0", render_mode="rgb_array")
        self.players = {}
        self.lock = threading.Lock()
        self.game_thread = None
        self.game_running = False

    def add_player(self, player_id):
        with self.lock:
            if player_id not in self.players:
                self.players[player_id] = {
                    "observation": self.env.reset()[0],
                    "score": 0,
                    "alive": True,
                    "action": 0  # Default action (do nothing)
                }

    def remove_player(self, player_id):
        with self.lock:
            if player_id in self.players:
                del self.players[player_id]

    def update_player_action(self, player_id, action):
        with self.lock:
            if player_id in self.players and self.players[player_id]["alive"]:
                self.players[player_id]["action"] = action

    def get_game_state(self):
        with self.lock:
            game_state = {}
            for player_id, player_data in self.players.items():
                # Convert observation (numpy array) to base64 encoded image for frontend
                img_data = None
                if player_data["observation"] is not None:
                    img = Image.fromarray(player_data["observation"])
                    buffered = BytesIO()
                    img.save(buffered, format="PNG")
                    img_data = base64.b64encode(buffered.getvalue()).decode("utf-8")
                
                game_state[player_id] = {
                    "observation": img_data,
                    "score": player_data["score"],
                    "alive": player_data["alive"]
                }
            return game_state

    def start_game(self):
        """Start the game with all players in a shared environment."""
        if self.game_thread is not None and self.game_thread.is_alive():
            return  # Game already running
            
        self.game_running = True
        self.game_thread = threading.Thread(target=self._game_loop)
        self.game_thread.daemon = True
        self.game_thread.start()

    def _game_loop(self):
        """Internal game loop that runs in a separate thread."""
        # Reset the environment
        self.env = gym.make("FlappyBird-v0", render_mode="rgb_array")
        observation, info = self.env.reset()

        # Initialize all players
        with self.lock:
            for player_id in self.players:
                self.players[player_id]["observation"] = observation
                self.players[player_id]["score"] = 0
                self.players[player_id]["alive"] = True
                self.players[player_id]["action"] = 0  # Default action

        # Game loop
        while self.game_running:
            # Check if all players are dead
            all_dead = True
            with self.lock:
                for player_id in self.players:
                    if self.players[player_id]["alive"]:
                        all_dead = False
                        break
            
            if all_dead or len(self.players) == 0:
                self.game_running = False
                break

            # Process each player's action
            with self.lock:
                for player_id in self.players:
                    if self.players[player_id]["alive"]:
                        action = self.players[player_id]["action"]
                        # Reset action after processing
                        self.players[player_id]["action"] = 0
                        
                        obs, reward, done, _, _ = self.env.step(action)
                        self.players[player_id]["observation"] = obs
                        self.players[player_id]["score"] += reward
                        self.players[player_id]["alive"] = not done

        self.env.close()
        
    def stop_game(self):
        """Stop the running game."""
        self.game_running = False
        if self.game_thread is not None:
            self.game_thread.join(timeout=1.0)
            self.game_thread = None