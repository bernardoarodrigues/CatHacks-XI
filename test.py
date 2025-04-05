import flappy_bird_gymnasium
import gymnasium
import numpy as np
env = gymnasium.make("FlappyBird-v0", render_mode="human", use_lidar=False)

import torch
import torch.nn as nn
class DQN(nn.Module):
    def __init__(self, input_dim, output_dim):
        super(DQN, self).__init__()
        self.fc1 = nn.Linear(input_dim, 128)
        self.fc2 = nn.Linear(128, 128)
        self.fc3 = nn.Linear(128, output_dim)
    
    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        return self.fc3(x)

policy_net = DQN(12, 2)
policy_net.load_state_dict(torch.load("dqn_flappy_bird.pth"))
policy_net.eval()

obs, _ = env.reset()
c1, c2 = 0, 0
while True:
    with torch.no_grad():
        obs_tensor = torch.tensor(obs, dtype=torch.float32).unsqueeze(0)
        q_values = policy_net(obs_tensor)
        action = int(q_values.argmax().item())

    # Processing:
    obs, reward, terminated, _, info = env.step(action)
    
    # Checking if the player is still alive
    if terminated:
        break

print(f"Random actions: {c1}, Agent actions: {c2}")

env.close()