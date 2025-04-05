import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'environments')))

import flappy_bird_gymnasium
import gymnasium
from flappy_env import MultiplayerFlappyEnv
import pickle
import numpy as np
# from stable_baselines3 import PPO

# Create environment
env = gymnasium.make("FlappyBird-v0", render_mode="human", use_lidar=False)

# env = MultiplayerFlappyEnv(pipe_gap=130, render_mode="human")
# env.current_player = "ai_agent" # Set active player for training
# env.player_id = "ai_agent"
# env.add_player("ai_agent")


with open("./saved_policies/QTable-EG.pkl", "rb") as f:
    q_table = pickle.load(f)

obs, _ = env.reset()
obs = [int(x) for x in obs]
done = False
while not done:

    action = np.argmax(q_table[tuple(obs)])
    print("TAKING ACTION: ", action)

    obs, reward, done, truncated, info = env.step(action)
    obs = [int(x) for x in obs]
    # print(f"Action {action} gave {reward} reward...")
    print(obs, reward, done, truncated, info)

env.close()