# CatHacks-XI

# FlappyNite - Flappy Bird Battle Royale

A multiplayer battle royale Flappy Bird game built using Flask, SocketIO, and flappy-bird-gymnasium. Players compete to be the last bird flying!

## Features

- **Real-time multiplayer** battle royale gameplay
- **Responsive web interface** that works on desktop and mobile
- **Battle royale mechanics** where the last player alive wins
- **Test mode** for debugging and practice
- **Compatible with reinforcement learning** for future AI agent integration
- **Spectator mode** for watching ongoing games

## Architecture

The project uses a hybrid architecture that combines multiplayer web gameplay with a gym-compatible environment:

- **Flask + SocketIO** for real-time web communication
- **flappy-bird-gymnasium** as the underlying game engine
- **Custom environment wrappers** for multiplayer support
- **Threaded game manager** for handling multiple players

## Project Structure

- `app.py` - Flask server and SocketIO handlers
- `game_manager.py` - Core game logic and player state management
- `custom_flappy.py` - Custom Flappy Bird environment with fixed pipe gaps
- `environments/flappy_env.py` - Multiplayer environment wrapper
- `static/` - Frontend assets (CSS, JS, sprites)
- `templates/` - HTML templates

## Installation

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```
3. Run the server:
```bash
python app.py
```

## How to Play

1. Open the game in a web browser at `http://localhost:8000`
2. Enter your username and join the game
3. When the admin starts the game, press SPACE to flap your bird
4. Avoid hitting pipes and the ground
5. Last player alive wins!

## Future Extensions

### AI Agent Integration

The environment is designed to be compatible with reinforcement learning agents:

```python
from environments.flappy_env import MultiplayerFlappyEnv
from stable_baselines3 import PPO

# Create environment
env = MultiplayerFlappyEnv(pipe_gap=130)

# Set active player for training
env.current_player = "ai_agent"

# Create and train a PPO agent
model = PPO("MlpPolicy", env, verbose=1)
model.learn(total_timesteps=10000)

# Use the trained model
obs, _ = env.reset()
while True:
    action, _ = model.predict(obs)
    obs, reward, done, _, _ = env.step(action)
    if done:
        break
```

## Credits

- Built for CatHacks-XI
- Uses [flappy-bird-gymnasium](https://github.com/pygames-playground/flappy-bird-gymnasium)
- Sprites from the original Flappy Bird game