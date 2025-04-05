import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'environments')))

import flappy_bird_gymnasium
import gymnasium
from flappy_env import MultiplayerFlappyEnv
# from stable_baselines3 import PPO

# Create environment
env = gymnasium.make("FlappyBird-v0", render_mode="human", use_lidar=False)

# env = MultiplayerFlappyEnv(pipe_gap=130, render_mode="human")
# env.current_player = "ai_agent" # Set active player for training
# env.player_id = "ai_agent"
# env.add_player("ai_agent")

# Create and train a PPO agent
# model = PPO("MlpPolicy", env, verbose=1)
# model.learn(total_timesteps=10000)

# Use the trained model
obs, _ = env.reset()
done = False
while not done:

    # random policy
    action = env.action_space.sample()

    # action, _ = model.predict(obs)

    obs, reward, done, truncated, info = env.step(action)
    # print(f"Action {action} gave {reward} reward...")
    print(obs, reward, done, truncated, info)

    # done = False

env.close()