# utils.py
# helpers for mission planning & explainable logs

from typing import List, Tuple
import numpy as np

def generate_waypoints_for_agents(n_agents=4, env_width=100, env_height=100, n_waypoints=3):
    # create list-of-list of waypoints per agent
    all_wps = []
    rng = np.random.RandomState(1234)
    for i in range(n_agents):
        wps = []
        for j in range(n_waypoints):
            wps.append((float(rng.uniform(5, env_width-5)), float(rng.uniform(5, env_height-5))))
        all_wps.append(wps)
    return all_wps