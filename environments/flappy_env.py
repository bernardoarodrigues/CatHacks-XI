import copy
from custom_flappy import CustomFlappyBirdEnv

class MultiplayerFlappyEnv:
    """
    Environment wrapper that supports multiple players in a single Flappy Bird environment.
    This handles the battle royale mechanics while maintaining compatibility with the 
    gymnasium interface for future RL integration.
    
    Each player has their own bird position but shares the same pipes and obstacles.
    """
    def __init__(self, pipe_gap=100, render_mode=None, countdown_seconds=3):
        """Initialize the multiplayer environment with custom pipe gap."""
        # Create the base environment that we'll use to manage the shared world
        self.base_env = CustomFlappyBirdEnv(pipe_gap=pipe_gap, render_mode=render_mode, countdown_seconds=countdown_seconds)
        
        # Reset base environment to initialize everything
        self.reset()
        
        # These variables will track player-specific state
        self.player_positions = {}  # {player_id: {'x', 'y', 'vel_y', 'rot'}}
        self.player_scores = {}     # {player_id: score}
        self.player_alive = {}      # {player_id: True/False}
        self.player_actions = {}    # {player_id: last_action}
        
        # Track the current active player for step execution
        self.current_player = None
        
        # Constants from the base environment
        self.player_width = 34
        self.player_height = 24
        self.gravity = 0.25
        self.flap_strength = -7
        self.max_vel_y = 10
        
        # Countdown properties
        self.countdown_active = True
        self.countdown_remaining = countdown_seconds
        
    @property
    def unwrapped(self):
        """Access to the underlying environment for pipe and ground data."""
        return self.base_env.unwrapped
        
    def reset(self):
        """Reset the base environment and return initial observation."""
        # Reset the base environment to get initial pipe positions
        observation, info = self.base_env.reset()
        
        # Cache the shared world data (pipes and ground)
        self._sync_world_data()
        
        return observation, info
    
    def _sync_world_data(self):
        """Extract and cache the world state from the base environment."""
        unwrapped = self.unwrapped
        
        # Store pipe positions
        if hasattr(unwrapped, '_upper_pipes') and hasattr(unwrapped, '_lower_pipes'):
            self.shared_pipes = {
                'upper': copy.deepcopy(unwrapped._upper_pipes),
                'lower': copy.deepcopy(unwrapped._lower_pipes)
            }
        
        # Store ground position
        if hasattr(unwrapped, '_ground'):
            self.shared_ground = copy.deepcopy(unwrapped._ground)
        
        # Store other world properties
        self.screen_width = unwrapped._screen_width if hasattr(unwrapped, '_screen_width') else 288
        self.screen_height = unwrapped._screen_height if hasattr(unwrapped, '_screen_height') else 512
        
    def add_player(self, player_id):
        """Add a new player to the game with initial position."""
        # Set up initial bird position (same as in the base environment)
        player_x = 50  # Fixed x position for all birds
        player_y = self.screen_height / 2
        
        # Store the player's initial state
        self.player_positions[player_id] = {
            'x': player_x,
            'y': player_y,
            'vel_y': 0,
            'rot': 0
        }
        self.player_scores[player_id] = 0
        self.player_alive[player_id] = True
        self.player_actions[player_id] = 0
        
        # Return the base observation for this player
        observation, _ = self.base_env.reset()
        return observation
        
    def remove_player(self, player_id):
        """Remove a player from the game."""
        if player_id in self.player_positions:
            del self.player_positions[player_id]
        if player_id in self.player_scores:
            del self.player_scores[player_id]
        if player_id in self.player_alive:
            del self.player_alive[player_id]
        if player_id in self.player_actions:
            del self.player_actions[player_id]
            
    def get_player_score(self, player_id):
        """Get the current score for a player."""
        return self.player_scores.get(player_id, 0)
        
    def is_player_alive(self, player_id):
        """Check if a player is still alive."""
        return self.player_alive.get(player_id, False)
        
    def set_player_action(self, player_id, action):
        """Set the action for a specific player."""
        if player_id in self.player_alive and self.player_alive[player_id]:
            self.player_actions[player_id] = action
    
    def step_world(self):
        """
        Move the world forward (pipes and ground) without affecting birds.
        This is used to keep the shared world state in sync.
        """
        # Check if in countdown - don't move the world yet
        if self.is_in_countdown():
            return
            
        # Track current pipe positions before step
        prev_positions = []
        if hasattr(self.unwrapped, '_upper_pipes'):
            for pipe in self.unwrapped._upper_pipes:
                prev_positions.append(pipe['x'])
        
        # Use the base environment to compute the next world state
        self.base_env.step(0)  # Use "do nothing" action
        
        # Control pipe movement speed and spacing
        if hasattr(self.unwrapped, '_upper_pipes') and prev_positions:
            # Increase pipe speed for faster gameplay (was 3)
            pipe_speed = 5  # pixels per frame
            
            # Fix pipe spacing - increased to prevent too many pipes
            min_pipe_spacing = 300  # Minimum horizontal distance between pipes
            
            # First adjust speed of existing pipes
            for i, pipe in enumerate(self.unwrapped._upper_pipes):
                if i < len(prev_positions):
                    # Calculate how much the pipe moved
                    dx = prev_positions[i] - pipe['x']
                    
                    # Enforce consistent pipe speed
                    if dx != pipe_speed:
                        adjustment = dx - pipe_speed
                        pipe['x'] += adjustment
                        # Also adjust corresponding lower pipe
                        if hasattr(self.unwrapped, '_lower_pipes') and i < len(self.unwrapped._lower_pipes):
                            self.unwrapped._lower_pipes[i]['x'] += adjustment
            
            # Then check for pipes that are too close to each other
            if len(self.unwrapped._upper_pipes) >= 2:
                pipes_to_adjust = []
                # Sort pipes by x position (left to right)
                sorted_indices = sorted(range(len(self.unwrapped._upper_pipes)), 
                                      key=lambda i: self.unwrapped._upper_pipes[i]['x'])
                
                # Check spacing between adjacent pipes
                for j in range(1, len(sorted_indices)):
                    left_idx = sorted_indices[j-1]
                    right_idx = sorted_indices[j]
                    left_pipe_x = self.unwrapped._upper_pipes[left_idx]['x']
                    right_pipe_x = self.unwrapped._upper_pipes[right_idx]['x']
                    
                    # If pipes are too close
                    if right_pipe_x - left_pipe_x < min_pipe_spacing:
                        # Move the right pipe further to the right
                        adjustment = min_pipe_spacing - (right_pipe_x - left_pipe_x)
                        self.unwrapped._upper_pipes[right_idx]['x'] += adjustment
                        if hasattr(self.unwrapped, '_lower_pipes'):
                            self.unwrapped._lower_pipes[right_idx]['x'] += adjustment
            
            # Implement pipe recycling system
            
            # 1. Remove pipes that have moved off-screen (with buffer)
            if hasattr(self.unwrapped, '_upper_pipes') and hasattr(self.unwrapped, '_lower_pipes'):
                # Get the pipe width to determine when a pipe is fully off-screen
                pipe_width = self.base_env.unwrapped._pipe_width
                
                # Create a list of indices to remove
                pipes_to_remove = []
                for i, pipe in enumerate(self.unwrapped._upper_pipes):
                    # Check if the pipe has moved completely off the left side of the screen
                    if pipe['x'] + pipe_width < -50:  # 50px buffer
                        pipes_to_remove.append(i)
                
                # Remove the pipes (in reverse order to avoid index issues)
                for i in sorted(pipes_to_remove, reverse=True):
                    if i < len(self.unwrapped._upper_pipes):
                        del self.unwrapped._upper_pipes[i]
                    if i < len(self.unwrapped._lower_pipes):
                        del self.unwrapped._lower_pipes[i]
                
                # 2. Check if we need to add a new pipe - with stricter conditions
                screen_width = self.unwrapped._screen_width
                
                # Check if there are any pipes at all
                if len(self.unwrapped._upper_pipes) == 0:
                    # No pipes at all - add the first one
                    if hasattr(self.base_env, '_get_pipe_pos'):
                        upper_pipe, lower_pipe = self.base_env._get_pipe_pos()
                        upper_pipe['x'] = screen_width + 100
                        lower_pipe['x'] = screen_width + 100
                        
                        # Add the new pipes
                        self.unwrapped._upper_pipes.append(upper_pipe)
                        self.unwrapped._lower_pipes.append(lower_pipe)
                else:
                    # Find the rightmost pipe
                    rightmost_x = max(pipe['x'] for pipe in self.unwrapped._upper_pipes)
                    
                    # Only add a new pipe when the rightmost pipe is sufficiently into the screen
                    # This prevents creating too many pipes too quickly
                    if rightmost_x < screen_width - 150:
                        # Get pipe positions from CustomFlappyBirdEnv
                        if hasattr(self.base_env, '_get_pipe_pos'):
                            upper_pipe, lower_pipe = self.base_env._get_pipe_pos()
                            # Place the new pipe with more space to prevent too many pipes
                            new_x = screen_width + 100
                            upper_pipe['x'] = new_x
                            lower_pipe['x'] = new_x
                            
                            # Add the new pipes
                            self.unwrapped._upper_pipes.append(upper_pipe)
                            self.unwrapped._lower_pipes.append(lower_pipe)
                        
                # Max number of pipes to keep in memory - prevents excessive memory use
                # Reduced to ensure we don't keep too many pipes
                max_pipes = 3
                if len(self.unwrapped._upper_pipes) > max_pipes:
                    # Keep only the rightmost pipes if we somehow end up with too many
                    sorted_indices = sorted(range(len(self.unwrapped._upper_pipes)), 
                                         key=lambda i: self.unwrapped._upper_pipes[i]['x'],
                                         reverse=True)  # Sort from right to left
                    
                    keep_indices = sorted_indices[:max_pipes]  # Keep only the max_pipes rightmost pipes
                    self.unwrapped._upper_pipes = [self.unwrapped._upper_pipes[i] for i in sorted(keep_indices)]
                    self.unwrapped._lower_pipes = [self.unwrapped._lower_pipes[i] for i in sorted(keep_indices)]
        
        # Update our cached world data from the base environment
        self._sync_world_data()
        
    def step_player(self, player_id):
        """
        Process a single step for a specific player.
        Returns (observation, reward, done, truncated, info)
        """
        if player_id not in self.player_positions or not self.player_alive[player_id]:
            return None, 0, True, False, {}
        
        # Check if in countdown - don't process player actions yet
        if self.is_in_countdown():
            observation = self.base_env.unwrapped._get_observation()
            info = {'countdown_active': True, 'countdown_remaining': self.get_countdown_remaining()}
            return observation, 0, False, False, info
            
        # Get the player's current state
        pos = self.player_positions[player_id]
        action = self.player_actions.get(player_id, 0)
        
        # Update player velocity based on action and gravity
        if action == 1:  # Flap
            pos['vel_y'] = self.flap_strength
        else:
            pos['vel_y'] += self.gravity
        
        # Clamp velocity
        pos['vel_y'] = min(pos['vel_y'], self.max_vel_y)
        
        # Update position
        pos['y'] += pos['vel_y']
        
        # Update rotation based on velocity (falling = rotated down)
        if pos['vel_y'] < 0:
            pos['rot'] = min(pos['rot'] + 3, 30)
        else:
            pos['rot'] = max(pos['rot'] - 3, -30)
            
        # Check collisions
        reward = 0.1  # Small reward for surviving
        done = self._check_collision(player_id)
        
        # Check for scoring (passing through pipes)
        reward += self._check_score(player_id)
        
        # Update player state
        self.player_alive[player_id] = not done
        if not done:
            self.player_scores[player_id] += reward
            
        # Create observation (in a real implementation, you'd render what the player sees)
        observation = self.base_env.unwrapped._get_observation()
        
        # Create info dict similar to gym
        info = {'countdown_active': False, 'countdown_remaining': 0}
        
        return observation, reward, done, False, info  # truncated=False
    
    def _check_collision(self, player_id):
        """Check if a player has collided with pipes or ground."""
        if player_id not in self.player_positions:
            return True
            
        pos = self.player_positions[player_id]
        player_rect = {
            'x': pos['x'],
            'y': pos['y'],
            'width': self.player_width,
            'height': self.player_height
        }
        
        # Check ground collision
        if hasattr(self.unwrapped, '_ground'):
            ground_y = self.unwrapped._ground['y']
            if pos['y'] + self.player_height >= ground_y:
                return True
                
        # Check ceiling collision
        if pos['y'] <= 0:
            return True
            
        # Check pipe collisions
        if hasattr(self.unwrapped, '_upper_pipes') and hasattr(self.unwrapped, '_lower_pipes'):
            for upper, lower in zip(self.unwrapped._upper_pipes, self.unwrapped._lower_pipes):
                # Create pipe rects
                upper_rect = {
                    'x': upper['x'],
                    'y': 0,
                    'width': self.base_env.unwrapped._pipe_width,
                    'height': upper['y']
                }
                
                lower_rect = {
                    'x': lower['x'],
                    'y': lower['y'],
                    'width': self.base_env.unwrapped._pipe_width,
                    'height': self.screen_height - lower['y']
                }
                
                # Check collision
                if self._check_rect_collision(player_rect, upper_rect) or \
                   self._check_rect_collision(player_rect, lower_rect):
                    return True
                    
        return False
        
    def _check_rect_collision(self, rect1, rect2):
        """Check if two rectangles collide."""
        return (
            rect1['x'] < rect2['x'] + rect2['width'] and
            rect1['x'] + rect1['width'] > rect2['x'] and
            rect1['y'] < rect2['y'] + rect2['height'] and
            rect1['y'] + rect1['height'] > rect2['y']
        )
        
    def _check_score(self, player_id):
        """Check if player has passed a pipe and update score."""
        if player_id not in self.player_positions:
            return 0
            
        pos = self.player_positions[player_id]
        
        # Check if player has passed a pipe
        if hasattr(self.unwrapped, '_upper_pipes'):
            for pipe in self.unwrapped._upper_pipes:
                pipe_centerx = pipe['x'] + self.base_env.unwrapped._pipe_width / 2
                if pipe_centerx <= pos['x'] < pipe_centerx + 5:
                    # Player just passed this pipe
                    return 1.0  # Point for passing pipe
                    
        return 0
        
    def step(self, action):
        """
        Compatibility method for gym interface.
        Takes action for current player and returns observation.
        """
        if self.current_player is None:
            # If no player is set, use base environment behavior
            return self.base_env.step(action)
            
        # Set the action for the current player
        self.player_actions[self.current_player] = action
        
        # Process the player's step
        return self.step_player(self.current_player)
        
    def close(self):
        """Close the environment."""
        return self.base_env.close()
        
    def render(self):
        """Render the environment."""
        return self.base_env.render()
        
    def is_in_countdown(self):
        """Check if the environment is in countdown state."""
        if hasattr(self.base_env, 'is_in_countdown'):
            countdown_active = self.base_env.is_in_countdown()
            self.countdown_active = countdown_active
            return countdown_active
        return False
        
    def get_countdown_remaining(self):
        """Get the remaining time in the countdown."""
        if hasattr(self.base_env, 'get_countdown_status'):
            remaining = self.base_env.get_countdown_status()
            self.countdown_remaining = remaining
            return int(remaining)
        return 0
        
    def start_countdown(self):
        """Start the countdown timer."""
        if hasattr(self.base_env, 'start_countdown'):
            self.base_env.start_countdown()
            self.countdown_active = True