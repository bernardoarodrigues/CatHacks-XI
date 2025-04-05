import flappy_bird_gymnasium
import gymnasium as gym
import numpy as np
import copy
from custom_flappy import CustomFlappyBirdEnv

class MultiplayerFlappyEnv:
    """
    Environment wrapper that supports multiple players in a single Flappy Bird environment.
    This serves as a bridge between the RL-compatible environment and multiplayer game.
    
    Each player sees the same pipes but has their own bird, enabling true battle royale gameplay
    while maintaining compatibility with future RL agent integration.
    """
    def __init__(self, pipe_gap=100, render_mode=None):
        """Initialize the multiplayer environment with custom pipe gap."""
        self.base_env = CustomFlappyBirdEnv(pipe_gap=pipe_gap, render_mode=render_mode)
        self.players = {}  # Player-specific data: {player_id: {observation, score, etc.}}
        self.shared_pipes = {}  # Pipes that are shared across all players
        self.shared_ground = None  # Ground position shared by all players
        
    @property
    def unwrapped(self):
        """Access to the underlying environment."""
        return self.base_env.unwrapped
        
    def reset(self):
        """Reset the base environment and return initial observation."""
        observation, info = self.base_env.reset()
        
        # Track shared game elements
        unwrapped = self.unwrapped
        if hasattr(unwrapped, '_upper_pipes') and hasattr(unwrapped, '_lower_pipes'):
            self.shared_pipes = {
                'upper': copy.deepcopy(unwrapped._upper_pipes),
                'lower': copy.deepcopy(unwrapped._lower_pipes)
            }
        
        if hasattr(unwrapped, '_ground'):
            self.shared_ground = copy.deepcopy(unwrapped._ground)
        
        return observation, info
        
    def step(self, action):
        """
        Take a step in the environment with the given action.
        All players share the same pipes but have their own bird position.
        """
        observation, reward, terminated, truncated, info = self.base_env.step(action)
        
        # Update shared pipe positions after step
        unwrapped = self.unwrapped
        if hasattr(unwrapped, '_upper_pipes') and hasattr(unwrapped, '_lower_pipes'):
            self.shared_pipes = {
                'upper': copy.deepcopy(unwrapped._upper_pipes),
                'lower': copy.deepcopy(unwrapped._lower_pipes)
            }
            
        return observation, reward, terminated, truncated, info
        
    def close(self):
        """Close the environment."""
        return self.base_env.close()
        
    def render(self):
        """Render the environment."""
        return self.base_env.render()