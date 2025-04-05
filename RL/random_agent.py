"""Agent with random policy"""

import gymnasium
import numpy as np

import flappy_bird_gymnasium


def play(audio_on=False, render_mode="human", use_lidar=False):
    env = gymnasium.make(
        "FlappyBird-v0", audio_on=audio_on, render_mode=render_mode, use_lidar=use_lidar
    )
    obs = env.reset()
    while True:
        # Getting random action:
        action = env.action_space.sample()

        # Processing:
        obs, _, done, _, info = env.step(action)

        print(f"Obs: {obs}\n" f"Score: {info['score']}\n")

        if done:
            break

    env.close()
    assert obs.shape == env.observation_space.shape
    assert info["score"] == 0


if __name__ == "__main__":
    play()