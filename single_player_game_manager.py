import gymnasium as gym
import threading
import time
import numpy as np
import torch
import torch.nn as nn
from flappy_bird_gymnasium.envs.flappy_bird_env import FlappyBirdEnv

class DQN(nn.Module):
    """DQN model used by the AI player"""
    def __init__(self, input_dim, output_dim):
        super(DQN, self).__init__()
        self.fc1 = nn.Linear(input_dim, 128)
        self.fc2 = nn.Linear(128, 128)
        self.fc3 = nn.Linear(128, output_dim)
    
    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        return self.fc3(x)

class SinglePlayerGameManager:
    """Game manager for a single player vs AI game"""
    def __init__(self):
        self.env = None
        self.game_thread = None
        self.game_running = False
        self.game_over = False
        self.lock = threading.Lock()
        self.frame_rate = 40  # Target frame rate for game loop
        self.last_frame_time = 0
        
        # Game state tracking
        self.player_data = {
            "position": {"x": 50, "y": 256, "rotation": 0},
            "alive": True,
            "score": 0
        }
        
        self.ai_data = {
            "position": {"x": 50, "y": 256, "rotation": 0},
            "alive": True,
            "score": 0
        }
        
        # Load AI model
        self.ai_model = DQN(12, 2)  # 12 input features, 2 output actions
        try:
            self.ai_model.load_state_dict(torch.load("dqn_flappy_bird.pth"))
            self.ai_model.eval()
            print("AI model loaded successfully")
        except Exception as e:
            print(f"Error loading AI model: {e}")
        
        # Game state for frontend rendering
        self.game_state = {
            "player": self.player_data,
            "ai": self.ai_data,
            "_metadata": {
                "game_over": False,
                "winner": None,
                "countdown": {
                    "active": False,
                    "remaining": 0
                },
                "game_data": {
                    "screen_width": 288,
                    "screen_height": 512,
                    "ground_y": 400,
                    "pipe_width": 52,
                    "pipes": []
                }
            }
        }

    def start_game(self):
        """Start the game in a separate thread"""
        if self.game_thread and self.game_thread.is_alive():
            return False
        
        self.game_running = True
        self.game_over = False
        self.game_thread = threading.Thread(target=self._game_loop)
        self.game_thread.daemon = True
        self.game_thread.start()
        return True

    def stop_game(self):
        """Stop the running game"""
        self.game_running = False
        if self.game_thread:
            self.game_thread.join(timeout=1.0)
            self.game_thread = None

    def reset_game(self):
        """Reset the game state for a new game"""
        with self.lock:
            self.stop_game()
            self.game_over = False
            
            # Reset player data
            self.player_data = {
                "position": {"x": 50, "y": 256, "rotation": 0},
                "alive": True,
                "score": 0
            }
            
            self.ai_data = {
                "position": {"x": 50, "y": 256, "rotation": 0},
                "alive": True,
                "score": 0
            }
            
            # Reset game state
            self.game_state["_metadata"]["game_over"] = False
            self.game_state["_metadata"]["winner"] = None
            self.game_state["_metadata"]["countdown"] = {
                "active": True,
                "remaining": 3
            }
            self.game_state["_metadata"]["game_data"]["pipes"] = []
            
            # Reset the environment
            if self.env:
                try:
                    self.env.close()
                except:
                    pass
            
            try:
                self.env = gym.make("FlappyBird-v0", render_mode=None)
            except Exception as e:
                print(f"Error creating environment: {e}")

    def update_player_action(self, action):
        """Update player action (0 = do nothing, 1 = flap)"""
        with self.lock:
            if not self.game_running or not self.player_data["alive"]:
                return
            
            if action == 1:  # Flap
                # Update player velocity to simulate a flap
                # The actual flap will be processed in the game loop
                self.player_action = 1
            else:
                self.player_action = 0

    def get_game_state(self):
        """Get the current game state for frontend rendering"""
        with self.lock:
            return self.game_state.copy()

    def _game_loop(self):
        """Main game loop that runs in a separate thread"""
        try:
            # Initialize environment
            self.env = gym.make("FlappyBird-v0", render_mode=None)
            observation, _ = self.env.reset()
            
            # Track player and AI actions
            self.player_action = 0
            
            # Start with countdown
            countdown_start = time.time()
            countdown_duration = 3  # seconds
            
            # Update metadata to show countdown
            with self.lock:
                self.game_state["_metadata"]["countdown"] = {
                    "active": True,
                    "remaining": countdown_duration
                }
            
            # Wait for countdown
            while self.game_running and time.time() - countdown_start < countdown_duration:
                remaining = countdown_duration - (time.time() - countdown_start)
                
                with self.lock:
                    self.game_state["_metadata"]["countdown"]["remaining"] = remaining
                
                # Control frame rate
                current_time = time.time()
                elapsed = current_time - self.last_frame_time
                sleep_time = max(0, 1.0/self.frame_rate - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)
                self.last_frame_time = time.time()
            
            # Disable countdown
            with self.lock:
                self.game_state["_metadata"]["countdown"] = {
                    "active": False,
                    "remaining": 0
                }
            
            # Reset environment to start fresh after countdown
            observation, _ = self.env.reset()
            self.player_env = gym.make("FlappyBird-v0", render_mode=None)
            player_obs, _ = self.player_env.reset()
            
            # Main game loop
            while self.game_running and not self.game_over:
                # Control frame rate
                current_time = time.time()
                elapsed = current_time - self.last_frame_time
                sleep_time = max(0, 1.0/self.frame_rate - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)
                self.last_frame_time = time.time()
                
                # Process AI action
                with torch.no_grad():
                    obs_tensor = torch.tensor(observation, dtype=torch.float32).unsqueeze(0)
                    q_values = self.ai_model(obs_tensor)
                    ai_action = int(q_values.argmax().item())
                
                # Get player action
                player_action = self.player_action
                self.player_action = 0  # Reset to do nothing by default
                
                # Step AI environment
                observation, ai_reward, ai_terminated, _, ai_info = self.env.step(ai_action)
                
                # Step player environment
                player_obs, player_reward, player_terminated, _, player_info = self.player_env.step(player_action)
                
                # Extract game state from the environment
                # We need to access the underlying environment attributes
                with self.lock:
                    # Update AI position
                    self.ai_data["position"]["y"] = self.env.unwrapped._player_y
                    self.ai_data["position"]["rotation"] = -30 if ai_action == 1 else 30
                    self.ai_data["alive"] = not ai_terminated
                    self.ai_data["score"] += ai_reward if not ai_terminated else 0
                    
                    # Update player position
                    self.player_data["position"]["y"] = self.player_env.unwrapped._player_y
                    self.player_data["position"]["rotation"] = -30 if player_action == 1 else 30
                    self.player_data["alive"] = not player_terminated
                    self.player_data["score"] += player_reward if not player_terminated else 0
                    
                    # Update pipe data for rendering
                    if hasattr(self.env.unwrapped, '_upper_pipes') and hasattr(self.env.unwrapped, '_lower_pipes'):
                        pipes = []
                        for i, (upper, lower) in enumerate(zip(self.env.unwrapped._upper_pipes, self.env.unwrapped._lower_pipes)):
                            pipes.append({
                                'x': upper['x'],
                                'upper_y': upper['y'],  # Upper pipe height
                                'lower_y': lower['y']   # Lower pipe y position
                            })
                        
                        self.game_state["_metadata"]["game_data"]["pipes"] = pipes
                        if hasattr(self.env.unwrapped, '_ground'):
                            self.game_state["_metadata"]["game_data"]["ground_y"] = self.env.unwrapped._ground['y']
                    
                    # Check if game is over
                    self.game_over = not self.ai_data["alive"] and not self.player_data["alive"]
                    
                    # Check for winner if one player died but the other is still alive
                    if not self.ai_data["alive"] and self.player_data["alive"]:
                        self.game_state["_metadata"]["winner"] = "player"
                        self.game_state["_metadata"]["game_over"] = True
                    elif self.ai_data["alive"] and not self.player_data["alive"]:
                        self.game_state["_metadata"]["winner"] = "ai"
                        self.game_state["_metadata"]["game_over"] = True
                    elif not self.ai_data["alive"] and not self.player_data["alive"]:
                        # If both died on the same frame, highest score wins
                        if self.ai_data["score"] > self.player_data["score"]:
                            self.game_state["_metadata"]["winner"] = "ai"
                        else:
                            self.game_state["_metadata"]["winner"] = "player"
                        self.game_state["_metadata"]["game_over"] = True
                
                # If game is over, exit the loop
                if self.game_state["_metadata"]["game_over"]:
                    break
            
            # Mark game as over
            with self.lock:
                self.game_state["_metadata"]["game_over"] = True
                if not self.game_state["_metadata"]["winner"]:
                    # Determine winner based on score if not already set
                    if self.ai_data["score"] > self.player_data["score"]:
                        self.game_state["_metadata"]["winner"] = "ai"
                    else:
                        self.game_state["_metadata"]["winner"] = "player"
            
            # Clean up
            self.env.close()
            self.player_env.close()
            
        except Exception as e:
            print(f"Error in game loop: {e}")
            import traceback
            traceback.print_exc()
            with self.lock:
                self.game_state["_metadata"]["game_over"] = True
        finally:
            self.game_running = False