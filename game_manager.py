import gymnasium as gym
import threading
import numpy as np
import time
from environments.flappy_env import MultiplayerFlappyEnv

class GameManager:
    def __init__(self):
        self.env = None 
        self.PIPE_GAP = 130  # Slightly bigger gap for easier gameplay
        self.players = {}
        self.lock = threading.Lock()
        self.game_thread = None
        self.game_running = False
        self.winner = None
        self.game_over = False
        self.frame_rate = 40 # Target frame rate for game loop
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
        
        # Countdown settings
        self.countdown_seconds = 4
        self.in_countdown = True
        self.countdown_remaining = self.countdown_seconds
        
        # Create environment now that all imports are resolved
        try:
            self.env = MultiplayerFlappyEnv(pipe_gap=self.PIPE_GAP, countdown_seconds=self.countdown_seconds)
        except Exception as e:
            print(f"Error initializing environment: {e}")
            # We'll retry when needed

    def add_player(self, player_id):
        """Add a new player to the game."""
        with self.lock:
            if player_id not in self.players:
                try:
                    # Add player to environment with initial state
                    self.env.add_player(player_id)
                    
                    # Create player entry in our local state tracking
                    self.players[player_id] = {
                        "score": 0,
                        "alive": True,
                        "action": 0,  # Default action (do nothing)
                        "position": self._get_player_position(player_id)
                    }
                    
                except Exception as e:
                    print(f"Error adding player {player_id}: {e}")

    def _get_player_position(self, player_id):
        """Get the current position data for a player from the environment."""
        if hasattr(self.env, 'player_positions') and player_id in self.env.player_positions:
            pos = self.env.player_positions[player_id]
            return {
                "x": pos['x'],
                "y": pos['y'],
                "velocity": pos['vel_y'],
                "rotation": pos['rot']
            }
        # Fall back to default values if we can't get from environment
        return {
            "x": 50,
            "y": self.game_height / 2,
            "velocity": 0,
            "rotation": 0
        }

    def remove_player(self, player_id):
        """Remove a player from the game."""
        with self.lock:
            if player_id in self.players:
                # Remove from local tracking
                del self.players[player_id]
                
                # Remove from environment
                if self.env:
                    self.env.remove_player(player_id)

    def update_player_action(self, player_id, action):
        """Update a player's action."""
        with self.lock:
            if player_id in self.players and self.players[player_id]["alive"]:
                # Update local state
                self.players[player_id]["action"] = action
                
                # Pass to environment
                if self.env:
                    self.env.set_player_action(player_id, action)

    def get_game_state(self):
        """Get the current state of the game for rendering."""
        with self.lock:
            game_state = {}
            
            # Get environment for world data
            if not self.env or not hasattr(self.env, 'unwrapped'):
                return {"_metadata": {"game_over": True, "winner": None}}
                
            unwrapped_env = self.env.unwrapped
            
            # Check countdown status
            in_countdown = False
            countdown_remaining = 0
            if hasattr(self.env, 'is_in_countdown') and hasattr(self.env, 'get_countdown_remaining'):
                in_countdown = self.env.is_in_countdown()
                countdown_remaining = self.env.get_countdown_remaining()
            
            # Extract pipe positions from the environment
            pipes_data = []
            if hasattr(unwrapped_env, '_upper_pipes') and hasattr(unwrapped_env, '_lower_pipes'):
                for upper, lower in zip(unwrapped_env._upper_pipes, unwrapped_env._lower_pipes):
                    # Check for valid pipe heights
                    upper_y = upper['y']
                    lower_y = lower['y']
                    
                    # Validate upper pipe height
                    if upper_y <= 0:
                        upper_y = 50  # Minimum height
                    
                    # Get ground position
                    ground_y = unwrapped_env._ground['y'] if hasattr(unwrapped_env, '_ground') else self.game_height - 112
                    
                    # Ensure lower pipe has valid height
                    if lower_y >= ground_y:
                        lower_y = ground_y - 50
                    
                    pipes_data.append({
                        "x": upper['x'],
                        "upper_y": upper_y,
                        "lower_y": lower_y
                    })
            
            # Extract ground position
            ground_y = unwrapped_env._ground['y'] if hasattr(unwrapped_env, '_ground') else self.game_height - 112
            
            # Global game data shared by all players
            game_data = {
                "pipes": pipes_data,
                "ground_y": ground_y,
                "screen_width": self.game_width,
                "screen_height": self.game_height,
                "pipe_width": self.PIPE_WIDTH,
                "pipe_gap": self.PIPE_GAP,
                "countdown": {
                    "active": in_countdown,
                    "remaining": countdown_remaining
                }
            }
            
            # Add player data
            for player_id, player_data in self.players.items():
                # Sync from environment state where available
                is_alive = self.test_mode or (hasattr(self.env, 'is_player_alive') and self.env.is_player_alive(player_id))
                score = self.env.get_player_score(player_id) if hasattr(self.env, 'get_player_score') else player_data["score"]
                
                # Get current position - use environment data if available
                position = self._get_player_position(player_id)
                
                # Add to game state
                game_state[player_id] = {
                    "position": position,
                    "score": score,
                    "alive": is_alive
                }
            
            # Add metadata
            game_state["_metadata"] = {
                "game_over": self.game_over,
                "winner": self.winner,
                "timestamp": time.time(),
                "game_data": game_data,
                "countdown": {
                    "active": in_countdown,
                    "remaining": countdown_remaining
                }
            }
            
            return game_state

    def start_game(self):
        """Start the game loop in a separate thread."""
        if self.game_thread is not None and self.game_thread.is_alive():
            return  # Game already running
        
        # Reset game state
        self.game_over = False
        self.winner = None
        self.game_running = True
        self.last_frame_time = time.time()
        
        # Start game loop in a thread
        self.game_thread = threading.Thread(target=self._game_loop)
        self.game_thread.daemon = True
        self.game_thread.start()

    def _game_loop(self):
        """Main game loop that runs in a separate thread."""
        try:
            # Reset the environment
            self.env = MultiplayerFlappyEnv(pipe_gap=self.PIPE_GAP, countdown_seconds=self.countdown_seconds)
            observation, info = self.env.reset()
            
            # Re-initialize all players in the new environment
            with self.lock:
                for player_id in list(self.players.keys()):
                    self.env.add_player(player_id)
                    self.players[player_id]["score"] = 0
                    self.players[player_id]["alive"] = True
                    self.players[player_id]["action"] = 0
                    self.players[player_id]["position"] = self._get_player_position(player_id)
            
            # First, handle countdown phase
            while self.game_running and self.env.is_in_countdown():
                current_time = time.time()
                elapsed = current_time - self.last_frame_time
                sleep_time = max(0, 1.0/self.frame_rate - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)
                self.last_frame_time = time.time()
                
                # During countdown, just update positions but don't process physics
                with self.lock:
                    for player_id in list(self.players.keys()):
                        self.players[player_id]["position"] = self._get_player_position(player_id)
                
                # Wait for countdown to finish
                if self.env.get_countdown_remaining() <= 0:
                    print("Countdown finished, starting game!")
                    break

            # Game loop - only starts after countdown is complete
            while self.game_running:
                # Maintain frame rate
                current_time = time.time()
                elapsed = current_time - self.last_frame_time
                sleep_time = max(0, 1.0/self.frame_rate - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)
                self.last_frame_time = time.time()
                
                # Step the world forward (move pipes)
                if hasattr(self.env, 'step_world'):
                    self.env.step_world()
                
                # Process each player's state
                alive_players = []
                
                with self.lock:
                    # First collect actions for all players
                    for player_id in list(self.players.keys()):
                        # Skip dead players
                        if not self.players[player_id]["alive"] and not self.test_mode:
                            continue
                            
                        # Get action
                        action = self.players[player_id]["action"]
                        
                        # Set action in environment
                        self.env.set_player_action(player_id, action)
                        
                        # Reset action after processing
                        self.players[player_id]["action"] = 0
                    
                    # Then step each player separately
                    for player_id in list(self.players.keys()):
                        # Skip dead players
                        if not self.players[player_id]["alive"] and not self.test_mode:
                            continue
                            
                        # Process player step in environment
                        try:
                            obs, reward, done, truncated, info = self.env.step_player(player_id)
                            
                            # Handle player death
                            if done and not self.test_mode:
                                self.players[player_id]["alive"] = False
                            elif self.test_mode:
                                # In test mode, players never die
                                self.players[player_id]["alive"] = True
                                
                                # If they would have died, reset their position
                                if done:
                                    self.env.add_player(player_id)  # Reset position
                                    
                            # Update position and score
                            self.players[player_id]["position"] = self._get_player_position(player_id)
                            self.players[player_id]["score"] = self.env.get_player_score(player_id)
                            
                            # Track alive players
                            if self.players[player_id]["alive"]:
                                alive_players.append(player_id)
                                
                        except Exception as e:
                            print(f"Error processing player {player_id}: {e}")
                            if not self.test_mode:
                                self.players[player_id]["alive"] = False
                            else:
                                # Try to recover in test mode
                                try:
                                    self.env.add_player(player_id)
                                    self.players[player_id]["alive"] = True
                                    self.players[player_id]["position"] = self._get_player_position(player_id)
                                except:
                                    pass
                
                # Only check end conditions if not in test mode
                if not self.test_mode:
                    # No players left alive - game over with no winner
                    if len(alive_players) == 0:
                        self.game_over = True
                        self.game_running = False
                        break
                        
                    # Only one player left alive - we have a winner!
                    # if len(alive_players) == 1 and len(self.players) > 1:
                    #     self.winner = alive_players[0]
                    #     self.game_over = True
                    #     self.game_running = False
                    #     break
                        
        except Exception as e:
            print(f"Error in game loop: {e}")
            self.game_running = False
            self.game_over = True
        finally:
            try:
                if hasattr(self.env, 'close'):
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
                self.env = MultiplayerFlappyEnv(pipe_gap=self.PIPE_GAP, countdown_seconds=self.countdown_seconds)
            except Exception as e:
                print(f"Error resetting environment: {e}")
                # Try to recover
                try:
                    if hasattr(self.env, 'close'):
                        self.env.close()
                except:
                    pass
                self.env = MultiplayerFlappyEnv(pipe_gap=self.PIPE_GAP, countdown_seconds=self.countdown_seconds)

    def set_test_mode(self, enabled=True):
        """Enable or disable test mode (never-ending game)."""
        with self.lock:
            self.test_mode = enabled
            print(f"Test mode {'enabled' if enabled else 'disabled'}")
            
            # If in test mode, make all players alive
            if self.test_mode:
                for player_id in self.players:
                    self.players[player_id]["alive"] = True