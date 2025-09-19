# simulation.py
# Agent state, environment (obstacles), simple physics update

from dataclasses import dataclass, field
import numpy as np
import pandas as pd
import random
from typing import List, Tuple

@dataclass
class AgentState:
    def __init__(self, agent_id, x, y):
        self.id = agent_id
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.speed = 0.0
        self.heading = 0.0  # in degrees
        self.mode = "idle"
        self.target = None
        self.log = []
        self.traj = [(x, y)]   # <-- NEW: keep list of positions

    def to_dict(self):
        return {
            "id": self.id,
            "x": self.x,
            "y": self.y,
            "vx": self.vx,
            "vy": self.vy,
            "speed": self.speed,
            "heading": self.heading,
            "mode": self.mode,
            "log": " | ".join(self.log[-5:])  # last 5 messages    
        }

    def step(self, env):
        if self.target:
            self.move_towards_target(env)

    def move_towards_target(self, env):
        # existing movement code...
        # after updating self.x, self.y:
        self.traj.append((self.x, self.y))   # <-- track trajectory

class Environment:
    def __init__(self, width=100, height=100, n_obstacles=5, seed=42):
        self.width = width
        self.height = height
        self.rng = np.random.RandomState(seed)
        self.obstacles = self._gen_obstacles(n_obstacles)

    def _gen_obstacles(self, n):
        obs = []
        for _ in range(n):
            x = float(self.rng.uniform(10, self.width-10))
            y = float(self.rng.uniform(10, self.height-10))
            r = float(self.rng.uniform(3, 8))
            obs.append({"x": x, "y": y, "r": r})
        return obs

    def obstacles_df(self):
        return pd.DataFrame(self.obstacles)

def create_fleet(n_agents=4, env=None):
    agents = []
    for i in range(n_agents):
        x = float(np.random.uniform(5, env.width-5))
        y = float(np.random.uniform(5, env.height-5))
        agents.append(AgentState(agent_id=f"Agent_{i+1}", x=x, y=y))
    return agents

def state_snapshot(agents):
    return pd.DataFrame([a.to_dict() for a in agents])