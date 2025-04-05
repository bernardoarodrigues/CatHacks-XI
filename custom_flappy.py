from flappy_bird_gymnasium.envs.flappy_bird_env import FlappyBirdEnv
import random

class CustomFlappyBirdEnv(FlappyBirdEnv):
    """Custom FlappyBird environment with random pipe heights and fixed gap."""
    
    def __init__(self, pipe_gap=100, render_mode=None):
        super().__init__(render_mode=render_mode)
        # Override the pipe gap with our custom value
        self._pipe_gap_size = pipe_gap
        print(f"Initialized CustomFlappyBirdEnv with pipe gap: {self._pipe_gap_size}")
    
    def _get_pipe_pos(self):
        """Generate random pipe position with fixed gap."""
        # Ensure minimum heights for both pipes
        min_pipe_height = 50  # Minimum height for any pipe
        
        # Calculate maximum height for upper pipe considering:
        # 1. Screen height
        # 2. Fixed gap size 
        # 3. Minimum height for lower pipe
        # 4. Buffer for ground (100px)
        max_upper_pipe = self._screen_height - self._pipe_gap_size - min_pipe_height - 100
        
        # Ensure max_upper_pipe is reasonable
        max_upper_pipe = max(100, max_upper_pipe)
        min_upper_pipe = min_pipe_height
        
        # Generate a random height for the top pipe
        upper_pipe_height = random.randint(min_upper_pipe, int(max_upper_pipe))
        
        # Calculate lower pipe y-position to ensure EXACTLY fixed gap
        lower_pipe_y = upper_pipe_height + self._pipe_gap_size
        
        # Make sure lower pipe has enough height before ground
        ground_y = self._screen_height - 112  # Typical ground position
        lower_pipe_height = ground_y - lower_pipe_y
        
        # Validate the lower pipe height
        if lower_pipe_height < min_pipe_height:
            # Move both pipes up to ensure minimum lower pipe height
            adjustment = min_pipe_height - lower_pipe_height
            upper_pipe_height = max(min_pipe_height, upper_pipe_height - adjustment)
            lower_pipe_y = upper_pipe_height + self._pipe_gap_size
        
        # Final validation to guarantee proper gap
        actual_gap = lower_pipe_y - upper_pipe_height
        if actual_gap != self._pipe_gap_size:
            print(f"WARNING: Gap validation failed! Adjusting gap from {actual_gap} to {self._pipe_gap_size}")
            lower_pipe_y = upper_pipe_height + self._pipe_gap_size
        
        # Log for debugging
        lower_pipe_height = ground_y - lower_pipe_y
        print(f"Generated pipe - Upper height: {upper_pipe_height}, Lower y: {lower_pipe_y}, Lower height: {lower_pipe_height}, Gap: {lower_pipe_y - upper_pipe_height}")
        
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
            
            # Add second pipe
            upper_pipe, lower_pipe = self._get_pipe_pos()
            upper_pipe["x"] += self._pipe_gap_size * 2  # Position further right
            lower_pipe["x"] += self._pipe_gap_size * 2
            self._upper_pipes.append(upper_pipe)
            self._lower_pipes.append(lower_pipe)
        
        return observation, info
        
    def step(self, action):
        """Override step to ensure new pipes have random heights with fixed gaps."""
        observation, reward, terminated, truncated, info = super().step(action)
        
        # Check if a new pipe was added in the original step method
        # If yes, replace it with our custom pipe
        if hasattr(self, '_upper_pipes') and len(self._upper_pipes) > 1:
            last_pipe_x = self._upper_pipes[-1]["x"]
            if last_pipe_x > self._screen_width - 5:  # New pipe was just added
                # Replace the last pipe with a new random one
                upper_pipe, lower_pipe = self._get_pipe_pos()
                self._upper_pipes[-1] = upper_pipe
                self._lower_pipes[-1] = lower_pipe
        
        return observation, reward, terminated, truncated, info 