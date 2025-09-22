# simulation.py
# Agent state, environment (obstacles), simple physics update

from dataclasses import dataclass, field
import numpy as np
import pandas as pd
import random
from typing import List, Tuple
import json
from PIL import Image
import os


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
    def __init__(self, config_file="config.json"):
        # Load and store config
        with open(config_file, "r") as f:
            self.config = json.load(f)

        # Basic attributes
        if "floorplan" in self.config:
            self.floorplan_path = os.path.join(os.path.dirname(__file__), self.config["floorplan"])
            if not os.path.exists(self.floorplan_path):
                raise FileNotFoundError(f"Floorplan image not found: {self.floorplan_path}")
        else:
            self.floorplan_path = None
        self.width = self.config.get("width", 100)
        self.height = self.config.get("height", 100)

        # Waypoints
        self.waypoints = {
            w["id"]: tuple(w["pos"]) for w in self.config.get("waypoints", [])
        }

        # Obstacles
        self.obstacles = [
            {"id": o["id"], "pos": tuple(o["pos"]), "size": tuple(o["size"])}
            for o in self.config.get("obstacles", [])
        ]

        # Agents initialized empty — use create_fleet()
        self.agents = []

    def create_fleet(self, n_agents):
        # """
        # Create n_agents and place them at spawn points from config.json.
        # If n_agents > number of spawns, cycle through them.
        # """
        self.agents = []  # reset
        spawns = [a["spawn"] for a in self.config.get("agents", [])]
        ids = [a["id"] for a in self.config.get("agents", [])]

        for i in range(n_agents):
            spawn = spawns[i % len(spawns)]
            agent_id = ids[i % len(ids)]
            self.agents.append(AgentState(agent_id=agent_id, x=spawn[0], y=spawn[1]))

        return self.agents

def state_snapshot(agents):
    return pd.DataFrame([a.to_dict() for a in agents])