from flappy_bird_gymnasium.envs.flappy_bird_env import FlappyBirdEnv
import random
import time

class CustomFlappyBirdEnv(FlappyBirdEnv):
    """Custom FlappyBird environment with random pipe heights and fixed gap."""
    
    def __init__(self, pipe_gap=100, render_mode=None, countdown_seconds=3):
        super().__init__(render_mode=render_mode)
        # Override the pipe gap with our custom value
        self._pipe_gap_size = pipe_gap
        # Initialize the pipe width attribute to match the parent class
        self._pipe_width = 52  # Standard pipe width in Flappy Bird
        
        # Countdown timer properties
        self._countdown_seconds = countdown_seconds
        self._countdown_start_time = 0
        self._in_countdown = False
        self._countdown_remaining = 0
        
        print(f"Initialized CustomFlappyBirdEnv with pipe gap: {self._pipe_gap_size}")
    
    def _get_pipe_pos(self):
        """Generate random pipe position with fixed gap."""
        # Constants for reliable pipe generation
        min_pipe_height = 60  # Minimum height for any pipe
        ground_y = self._screen_height - 112  # Typical ground position
        screen_height = self._screen_height
        
        # Determine valid range for upper pipe height
        max_upper_pipe_height = screen_height - self._pipe_gap_size - min_pipe_height - 100  # 100px buffer from ground
        max_upper_pipe_height = max(max_upper_pipe_height, min_pipe_height + 50)  # Ensure sufficient range
        
        # Generate random height for upper pipe within valid range
        upper_pipe_height = random.randint(min_pipe_height, int(max_upper_pipe_height))
        
        # Calculate lower pipe position to ensure EXACTLY the fixed gap
        lower_pipe_y = upper_pipe_height + self._pipe_gap_size
        
        # Final validation
        if lower_pipe_y + min_pipe_height > ground_y:
            # Adjust both pipes to maintain gap while ensuring lower pipe has minimum height
            adjustment = (lower_pipe_y + min_pipe_height) - ground_y
            upper_pipe_height -= adjustment
            lower_pipe_y = upper_pipe_height + self._pipe_gap_size
            
            # Extra sanity check: upper pipe must have minimum height
            if upper_pipe_height < min_pipe_height:
                # This is a failsafe - in this case, adjust the gap slightly
                upper_pipe_height = min_pipe_height
                lower_pipe_y = upper_pipe_height + self._pipe_gap_size
                # If we still can't fit it, lower the ground height (not ideal but safer than crashing)
                if lower_pipe_y + min_pipe_height > ground_y:
                    # We'll warn but still have a valid state
                    print(f"WARNING: Gap ({self._pipe_gap_size}) is too large for this screen height, pipes may look unusual")
        
        # Debug info
        lower_pipe_height = ground_y - lower_pipe_y
        print(f"Generated pipe - Upper height: {upper_pipe_height}, Lower y: {lower_pipe_y}, Lower height: {lower_pipe_height}, Gap: {self._pipe_gap_size}")
        
        return {
            "x": self._screen_width + 10,
            "y": upper_pipe_height
        }, {
            "x": self._screen_width + 10,
            "y": lower_pipe_y
        }
        
    def reset(self, seed=None, options=None):
        """Reset the environment and use our custom pipe position generator."""
        observation, info = super().reset(seed=seed, options=options)
        
        # Clear existing pipes and add new ones with our custom positions
        if hasattr(self, '_upper_pipes'):
            self._upper_pipes = []
            self._lower_pipes = []
            
            # Add first pipe
            upper_pipe, lower_pipe = self._get_pipe_pos()
            self._upper_pipes.append(upper_pipe)
            self._lower_pipes.append(lower_pipe)
            
            # Add second pipe with proper spacing
            upper_pipe, lower_pipe = self._get_pipe_pos()
            # Use fixed horizontal spacing (200-250px) instead of relying on pipe_gap
            pipe_spacing = 220  # Better horizontal spacing between pipes
            upper_pipe["x"] += pipe_spacing
            lower_pipe["x"] += pipe_spacing
            self._upper_pipes.append(upper_pipe)
            self._lower_pipes.append(lower_pipe)
            
        # Start the countdown timer
        self.start_countdown()
        
        # Add countdown info
        info['countdown_active'] = True
        info['countdown_remaining'] = self._countdown_seconds
        
        return observation, info
        
    def step(self, action):
        """Override step to ensure new pipes have random heights with fixed gaps."""
        # Check if in countdown mode
        if self.is_in_countdown():
            # If countdown is active, freeze the game state (no movement)
            observation = self._get_observation()
            reward = 0
            terminated = False
            truncated = False
            info = {
                'countdown_active': True,
                'countdown_remaining': self.get_countdown_status()
            }
            return observation, reward, terminated, truncated, info
            
        # Normal step behavior when countdown is over
        observation, reward, terminated, truncated, info = super().step(action)
        
        # Check if a new pipe was added in the original step method
        if hasattr(self, '_upper_pipes') and len(self._upper_pipes) > 0:
            # Find the rightmost pipe (newest one)
            rightmost_index = 0
            rightmost_x = -float('inf')
            for i, pipe in enumerate(self._upper_pipes):
                if pipe['x'] > rightmost_x:
                    rightmost_x = pipe['x']
                    rightmost_index = i
                    
            # If this pipe is newly added (beyond right edge)
            if rightmost_x > self._screen_width - 10:
                # Get the second rightmost pipe to check spacing
                second_rightmost_x = -float('inf')
                for i, pipe in enumerate(self._upper_pipes):
                    if pipe['x'] > second_rightmost_x and pipe['x'] < rightmost_x:
                        second_rightmost_x = pipe['x']
                
                # Ensure minimum spacing between pipes
                min_pipe_spacing = 220
                if rightmost_x - second_rightmost_x < min_pipe_spacing:
                    # Adjust position to maintain proper spacing
                    adjustment = min_pipe_spacing - (rightmost_x - second_rightmost_x)
                    self._upper_pipes[rightmost_index]['x'] += adjustment
                    self._lower_pipes[rightmost_index]['x'] += adjustment
                
                # Replace with our custom pipe with correct gap
                upper_pipe, lower_pipe = self._get_pipe_pos()
                # Keep x position we just determined
                upper_pipe['x'] = self._upper_pipes[rightmost_index]['x']
                lower_pipe['x'] = self._lower_pipes[rightmost_index]['x']
                # Update pipe
                self._upper_pipes[rightmost_index] = upper_pipe
                self._lower_pipes[rightmost_index] = lower_pipe
                
        # Add countdown info to the info dict
        info['countdown_active'] = False
        info['countdown_remaining'] = 0
        
        return observation, reward, terminated, truncated, info
        
    def _check_crash(self):
        """Override collision detection to be more reliable and consistent."""
        # Get player rectangle with small buffer for more natural collisions
        buffer = 4  # pixels
        player_rect = {
            'x': self._player_x + buffer,
            'y': self._player_y + buffer,
            'width': 34 - buffer * 2,  # Standard bird width minus buffer
            'height': 24 - buffer * 2   # Standard bird height minus buffer
        }
        
        # Check ground collision
        if player_rect['y'] + player_rect['height'] >= self._ground['y']:
            return True
        
        # Check ceiling collision
        if player_rect['y'] <= 0:
            return True
            
        # Check pipe collisions
        for upper_pipe, lower_pipe in zip(self._upper_pipes, self._lower_pipes):
            # Check collision with upper pipe
            if (player_rect['x'] + player_rect['width'] > upper_pipe['x'] and
                player_rect['x'] < upper_pipe['x'] + self._pipe_width and
                player_rect['y'] < upper_pipe['y']):
                return True
                
            # Check collision with lower pipe
            if (player_rect['x'] + player_rect['width'] > lower_pipe['x'] and
                player_rect['x'] < lower_pipe['x'] + self._pipe_width and
                player_rect['y'] + player_rect['height'] > lower_pipe['y']):
                return True
                
        return False
        
    def _get_observation(self):
        """Override get_observation to include countdown information."""
        observation = super()._get_observation()
        
        # If using RGB array observation, we can't modify it
        # Instead, countdown will be provided in the info dict during step
        
        return observation
        
    def start_countdown(self):
        """Start the countdown timer."""
        self._countdown_start_time = time.time()
        self._in_countdown = True
        self._countdown_remaining = self._countdown_seconds
        print(f"Starting {self._countdown_seconds} second countdown")
        
    def get_countdown_status(self):
        """Get the current countdown status."""
        if not self._in_countdown:
            return 0  # Countdown not active
            
        # Calculate remaining time
        elapsed = time.time() - self._countdown_start_time
        remaining = max(0, self._countdown_seconds - elapsed)
        self._countdown_remaining = remaining
        
        if remaining <= 0:
            # Countdown finished
            self._in_countdown = False
            return 0
            
        return remaining
        
    def is_in_countdown(self):
        """Check if the game is currently in countdown mode."""
        if self._in_countdown:
            # Update countdown status
            self.get_countdown_status()
        return self._in_countdown