import flappy_bird_gymnasium
import gymnasium as gym
import threading
import numpy as np
import time
from environments.flappy_env import MultiplayerFlappyEnv

class GameManager:
    def __init__(self):
        self.env = None  # Initialize later to avoid import issues
        self.PIPE_GAP = 130  # Slightly bigger gap for easier gameplay
        self.players = {}
        self.lock = threading.Lock()
        self.game_thread = None
        self.game_running = False
        self.winner = None
        self.game_over = False
        self.frame_rate = 30  # Target frame rate for game loop
        self.last_frame_time = 0
        
        # Game dimensions
        self.game_width = 288  # Default Flappy Bird width
        self.game_height = 512  # Default Flappy Bird height
        
        # Game constants (from flappy_bird_gymnasium)
        self.PLAYER_WIDTH = 34  # Bird width
        self.PLAYER_HEIGHT = 24  # Bird height
        self.PIPE_WIDTH = 52  # Pipe width
        
        # Test mode flag
        self.test_mode = False
        
        # Create environment now that all imports are resolved
        try:
            self.env = MultiplayerFlappyEnv(pipe_gap=self.PIPE_GAP)
        except Exception as e:
            print(f"Error initializing environment: {e}")
            # We'll retry when needed

    def add_player(self, player_id):
        with self.lock:
            if player_id not in self.players:
                # Reset environment to get initial state
                observation, info = self.env.reset()
                
                # Extract state from the environment
                unwrapped_env = self.env.unwrapped
                
                # Store player state with position data
                self.players[player_id] = {
                    "observation": observation,  # Keep for internal use
                    "score": 0,
                    "alive": True,
                    "action": 0,  # Default action (do nothing)
                    # Position data
                    "position": {
                        "x": unwrapped_env._player_x,
                        "y": unwrapped_env._player_y,
                        "velocity": unwrapped_env._player_vel_y,
                        "rotation": unwrapped_env._player_rot
                    }
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
            
            # Get the unwrapped environment to access position data
            unwrapped_env = self.env.unwrapped
            
            # Extract pipe positions from the environment
            pipes_data = []
            if hasattr(unwrapped_env, '_upper_pipes') and hasattr(unwrapped_env, '_lower_pipes'):
                for upper, lower in zip(unwrapped_env._upper_pipes, unwrapped_env._lower_pipes):
                    # Check and validate pipe positions
                    upper_y = upper["y"]
                    lower_y = lower["y"]
                    
                    # Make sure upperY is not zero or negative (would make pipe invisible)
                    if upper_y <= 0:
                        print(f"Warning: Upper pipe has y <= 0 ({upper_y}), fixing to 50")
                        upper_y = 50
                    
                    # Calculate ground position to check lower pipe
                    ground_y = unwrapped_env._ground["y"] if hasattr(unwrapped_env, '_ground') else self.game_height - 112
                    
                    # Make sure lower pipe has positive height
                    lower_pipe_height = ground_y - lower_y
                    if lower_pipe_height <= 0:
                        print(f"Warning: Lower pipe has no height ({lower_pipe_height}), fixing lower_y to {ground_y - 50}")
                        lower_y = ground_y - 50  # Ensure at least 50px height
                    
                    # Log pipe positions for debugging
                    print(f"Pipe positions - upper y: {upper_y}, lower y: {lower_y}, gap: {lower_y - upper_y}, lower height: {ground_y - lower_y}")
                    
                    pipes_data.append({
                        "x": upper["x"],
                        "upper_y": upper_y,
                        "lower_y": lower_y
                    })
            
            # Extract ground position
            ground_y = unwrapped_env._ground["y"] if hasattr(unwrapped_env, '_ground') else self.game_height - 112
            
            # Global game data shared by all players
            game_data = {
                "pipes": pipes_data,
                "ground_y": ground_y,
                "screen_width": self.game_width,
                "screen_height": self.game_height,
                "pipe_width": self.PIPE_WIDTH,
                "pipe_gap": self.PIPE_GAP
            }
            
            # Add individual player data
            for player_id, player_data in self.players.items():
                game_state[player_id] = {
                    "position": player_data["position"],
                    "score": player_data["score"],
                    "alive": player_data["alive"]
                }
            
            # Add game state metadata
            game_state["_metadata"] = {
                "game_over": self.game_over,
                "winner": self.winner,
                "timestamp": time.time(),
                "game_data": game_data  # Global game data shared by all players
            }
            
            return game_state

    def start_game(self):
        """Start the game with all players in a shared environment."""
        if self.game_thread is not None and self.game_thread.is_alive():
            return  # Game already running
        
        # Reset game state
        self.game_over = False
        self.winner = None
        self.game_running = True
        self.last_frame_time = time.time()
        
        self.game_thread = threading.Thread(target=self._game_loop)
        self.game_thread.daemon = True
        self.game_thread.start()

    def _check_crash(self, unwrapped_env, player_x, player_y):
        """Check if the player at the given position crashes into pipes or ground."""
        # Add a small buffer for collision detection to make it more accurate visually
        # Birds have oval shapes, but we use rectangles for collision
        buffer = 4  # pixels of buffer to make collision feel more natural
        
        # Calculate bird's collision rectangle
        player_rect = {
            'x': player_x + buffer,
            'y': player_y + buffer,
            'width': self.PLAYER_WIDTH - buffer * 2,
            'height': self.PLAYER_HEIGHT - buffer * 2
        }
        
        # Check ground collision
        if hasattr(unwrapped_env, '_ground'):
            ground_y = unwrapped_env._ground['y']
            if player_y + self.PLAYER_HEIGHT - buffer >= ground_y:
                print(f"Ground collision detected at y={player_y}, ground_y={ground_y}")
                return True
        
        # Check pipe collisions
        if hasattr(unwrapped_env, '_upper_pipes') and hasattr(unwrapped_env, '_lower_pipes'):
            for i, (upper, lower) in enumerate(zip(unwrapped_env._upper_pipes, unwrapped_env._lower_pipes)):
                # Only check pipes that are horizontally in range of the bird
                pipe_left = upper['x'] 
                pipe_right = upper['x'] + self.PIPE_WIDTH
                bird_left = player_rect['x']
                bird_right = player_rect['x'] + player_rect['width']
                
                # Skip if bird is not horizontally colliding with pipe
                if bird_right < pipe_left or bird_left > pipe_right:
                    continue
                
                # Validate pipe heights
                upper_y = upper['y']
                if upper_y <= 0:
                    upper_y = 50  # Minimum height
                
                lower_y = lower['y']
                
                # Bird top and bottom positions
                bird_top = player_rect['y']
                bird_bottom = player_rect['y'] + player_rect['height']
                
                # Print detailed collision debugging
                print(f"Pipe {i} check: Bird y=[{bird_top}-{bird_bottom}], Upper pipe bottom={upper_y}, Lower pipe top={lower_y}")
                
                # Check if bird is hitting upper pipe (bird's top edge is above the bottom of upper pipe)
                if bird_top < upper_y:
                    print(f"COLLISION: Bird top edge ({bird_top}) is hitting upper pipe (bottom at {upper_y})")
                    return True
                
                # Check if bird is hitting lower pipe (bird's bottom edge is below the top of lower pipe)
                if bird_bottom > lower_y:
                    print(f"COLLISION: Bird bottom edge ({bird_bottom}) is hitting lower pipe (top at {lower_y})")
                    return True
                
                # If we get here, bird is safely flying through the gap
                print(f"Bird is in the gap: y=[{bird_top}-{bird_bottom}], Gap=[{upper_y}-{lower_y}]")
        
        return False

    def _check_rect_collision(self, rect1, rect2):
        """Check if two rectangles collide."""
        return (
            rect1['x'] < rect2['x'] + rect2['width'] and
            rect1['x'] + rect1['width'] > rect2['x'] and
            rect1['y'] < rect2['y'] + rect2['height'] and
            rect1['y'] + rect1['height'] > rect2['y']
        )

    def _game_loop(self):
        """Internal game loop that runs in a separate thread."""
        # Reset the environment
        try:
            self.env = MultiplayerFlappyEnv(pipe_gap=self.PIPE_GAP)
            observation, info = self.env.reset()
            unwrapped_env = self.env.unwrapped

            # Initialize all players
            with self.lock:
                for player_id in self.players:
                    self.players[player_id]["observation"] = observation
                    self.players[player_id]["score"] = 0
                    self.players[player_id]["alive"] = True
                    self.players[player_id]["action"] = 0  # Default action
                    
                    # Initialize position data
                    self.players[player_id]["position"] = {
                        "x": unwrapped_env._player_x,
                        "y": unwrapped_env._player_y,
                        "velocity": unwrapped_env._player_vel_y,
                        "rotation": unwrapped_env._player_rot
                    }

            # Game loop
            while self.game_running:
                # Maintain consistent frame rate
                current_time = time.time()
                elapsed = current_time - self.last_frame_time
                sleep_time = max(0, 1.0/self.frame_rate - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)
                self.last_frame_time = time.time()
                
                # Check if all players are dead or only one player is alive
                alive_players = []
                with self.lock:
                    for player_id in self.players:
                        if self.players[player_id]["alive"]:
                            alive_players.append(player_id)
                
                # Only check end conditions if not in test mode
                if not self.test_mode:
                    # No players left alive - game over with no winner
                    if len(alive_players) == 0:
                        self.game_over = True
                        self.game_running = False
                        break
                        
                    # Only one player left alive - we have a winner!
                    if len(alive_players) == 1:
                        self.winner = alive_players[0]
                        self.game_over = True
                        self.game_running = False
                        break

                # Process each player's action
                with self.lock:
                    for player_id in self.players:
                        if self.players[player_id]["alive"]:
                            action = self.players[player_id]["action"]
                            # Reset action after processing
                            self.players[player_id]["action"] = 0
                            
                            try:
                                obs, reward, done, _, _ = self.env.step(action)
                                self.players[player_id]["observation"] = obs
                                self.players[player_id]["score"] += reward
                                
                                # Update position data after step
                                player_x = unwrapped_env._player_x
                                player_y = unwrapped_env._player_y
                                player_vel_y = unwrapped_env._player_vel_y
                                player_rot = unwrapped_env._player_rot
                                
                                # Update position in player data
                                self.players[player_id]["position"] = {
                                    "x": player_x,
                                    "y": player_y,
                                    "velocity": player_vel_y,
                                    "rotation": player_rot
                                }
                                
                                # Check collisions explicitly instead of relying only on done flag
                                collision = self._check_crash(unwrapped_env, player_x, player_y)
                                
                                if self.test_mode:
                                    # In test mode, keep the player alive regardless of collision
                                    self.players[player_id]["alive"] = True
                                    
                                    # If the player would have died, reset their position
                                    if done or collision:
                                        observation, info = self.env.reset()
                                        self.players[player_id]["observation"] = observation
                                        # Update position to match reset environment
                                        self.players[player_id]["position"] = {
                                            "x": unwrapped_env._player_x,
                                            "y": unwrapped_env._player_y,
                                            "velocity": unwrapped_env._player_vel_y,
                                            "rotation": unwrapped_env._player_rot
                                        }
                                else:
                                    # Normal mode - players can die
                                    if done or collision:
                                        self.players[player_id]["alive"] = False
                                    else:
                                        self.players[player_id]["alive"] = True
                                
                            except Exception as e:
                                print(f"Error in game step: {e}")
                                if self.test_mode:
                                    # In test mode, try to recover
                                    try:
                                        observation, info = self.env.reset()
                                        self.players[player_id]["observation"] = observation
                                        self.players[player_id]["alive"] = True
                                        self.players[player_id]["position"] = {
                                            "x": unwrapped_env._player_x,
                                            "y": unwrapped_env._player_y,
                                            "velocity": unwrapped_env._player_vel_y,
                                            "rotation": unwrapped_env._player_rot
                                        }
                                    except:
                                        pass
                                else:
                                    # In normal mode, let the player die
                                    self.players[player_id]["alive"] = False
        except Exception as e:
            print(f"Error in game loop: {e}")
            if self.test_mode:
                # In test mode, try to recover instead of ending
                try:
                    print("Attempting to recover game loop...")
                    self.env = MultiplayerFlappyEnv(pipe_gap=self.PIPE_GAP)
                    return self._game_loop()  # Restart the game loop
                except Exception as e2:
                    print(f"Recovery failed: {e2}")
            
            self.game_running = False
            self.game_over = True
        finally:
            try:
                self.env.close()
            except:
                pass
        
    def stop_game(self):
        """Stop the running game."""
        self.game_running = False
        if self.game_thread is not None:
            self.game_thread.join(timeout=1.0)
            self.game_thread = None
    
    def reset_game(self):
        """Reset the game state for a new game."""
        with self.lock:
            self.stop_game()
            self.game_over = False
            self.winner = None
            self.players = {}
            try:
                self.env = MultiplayerFlappyEnv(pipe_gap=self.PIPE_GAP)
            except Exception as e:
                print(f"Error resetting environment: {e}")
                # Try to recover
                try:
                    self.env.close()
                except:
                    pass
                self.env = MultiplayerFlappyEnv(pipe_gap=self.PIPE_GAP)

    def set_test_mode(self, enabled=True):
        """Enable or disable test mode (never-ending game)."""
        with self.lock:
            self.test_mode = enabled
            print(f"Test mode {'enabled' if enabled else 'disabled'}")