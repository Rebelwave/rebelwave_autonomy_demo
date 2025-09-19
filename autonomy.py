# autonomy.py
# Simple autonomy: waypoint following + reactive obstacle avoidance + explainable logs

import math
from typing import List, Tuple
from simulation import AgentState, Environment
import numpy as np

def distance(a_x, a_y, b_x, b_y):
    return math.hypot(a_x - b_x, a_y - b_y)

def angle_to(a_x, a_y, b_x, b_y):
    return math.atan2(b_y - a_y, b_x - a_x)

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

class Autonomy:
    def __init__(self, env: Environment, obstacle_avoidance_radius=10.0):
        self.env = env
        self.avoid_rad = obstacle_avoidance_radius

    def compute_control(self, agent: AgentState, waypoint: Tuple[float,float], dt=1.0, sensor_ok=True):
        """
        Returns (new_x, new_y, mode, reason)
        - If sensor_ok is False -> simulate sensor dropout and enter safe_mode
        - Simple behavior:
           1) If near obstacle -> steer away
           2) Else head to waypoint
        """
        if not sensor_ok:
            # sensor failure -> go to safe mode (hover/stop)
            agent.mode = "safe_mode"
            agent.log.append("Sensor dropout -> safe_mode (stop)")
            return agent.x, agent.y, agent.mode, "sensor_dropout"

        # base heading towards waypoint
        wx, wy = waypoint
        target_theta = angle_to(agent.x, agent.y, wx, wy)
        dist_to_wp = distance(agent.x, agent.y, wx, wy)

        # Obstacle check (reactive)
        for obs in self.env.obstacles:
            d = distance(agent.x, agent.y, obs["x"], obs["y"])
            if d < (obs["r"] + self.avoid_rad):
                # simple avoidance: compute vector away from obstacle and blend
                away_theta = angle_to(obs["x"], obs["y"], agent.x, agent.y)
                # blend heading: weighted between target and away vector
                blend = 0.7
                new_theta = (1-blend)*target_theta + blend*away_theta
                speed = clamp(agent.speed, 0.2, agent.speed)
                agent.heading = new_theta
                agent.vx = math.cos(new_theta) * speed
                agent.vy = math.sin(new_theta) * speed
                agent.mode = "avoiding"
                agent.log.append(f"Obstacle near ({obs['x']:.1f},{obs['y']:.1f}) -> avoiding")
                new_x = agent.x + agent.vx * dt
                new_y = agent.y + agent.vy * dt
                # clamp to environment
                new_x = clamp(new_x, 0, self.env.width)
                new_y = clamp(new_y, 0, self.env.height)
                return new_x, new_y, agent.mode, "avoid_obstacle"

        # No obstacle: go to waypoint
        speed = agent.speed
        # slow down when close to waypoint
        if dist_to_wp < 3.0:
            speed = max(0.2, speed * 0.3)
        agent.heading = target_theta
        agent.vx = math.cos(agent.heading) * speed
        agent.vy = math.sin(agent.heading) * speed
        agent.mode = "navigating" if dist_to_wp > 0.5 else "arrived"
        new_x = agent.x + agent.vx * dt
        new_y = agent.y + agent.vy * dt
        # clamp
        new_x = clamp(new_x, 0, self.env.width)
        new_y = clamp(new_y, 0, self.env.height)
        if agent.mode == "arrived":
            agent.log.append(f"Arrived at waypoint ({wx:.1f},{wy:.1f})")
        return new_x, new_y, agent.mode, "follow_wp"