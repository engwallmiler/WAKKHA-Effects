"""Ciclo de 28 s para QA: groove, breakdown, subida e drop. Sem reprodução."""
import numpy as np


def structure_demo_samples(t):
    position = np.asarray(t) % 28
    building = np.clip((position - 12) / 8, 0, 1)
    groove = (position < 8) | (position >= 20)
    kick_env = np.exp(-((position * 2) % 1) * 12) * groove
    # A fase integrada acelera de 2 a 8 ataques/s durante a subida.
    roll_time = np.maximum(0, position - 12)
    phase = np.where((position >= 12) & (position < 20), 2 * roll_time + 0.375 * roll_time ** 2, position * 2)
    snare_env = np.exp(-(phase % 1) * 18)
    snare_gain = np.where(position < 8, 0.025, np.where(position < 12, 0.04, np.where(position < 20, 0.04 + 0.16 * building, 0.1)))
    carrier = (np.sin(2 * np.pi * 1100 * t) + np.sin(2 * np.pi * 3500 * t)
               + np.sin(2 * np.pi * 6500 * t) + np.sin(2 * np.pi * 9100 * t)) / 4
    riser = np.where((position >= 12) & (position < 20), building * 0.05, 0) * np.sin(2 * np.pi * 7200 * t)
    left = 0.45 * kick_env * np.sin(2 * np.pi * 70 * t) + 0.05 * np.sin(2 * np.pi * 440 * t)
    right = 0.4 * kick_env * np.sin(2 * np.pi * 85 * t) + 0.05 * np.sin(2 * np.pi * 660 * t)
    return np.column_stack((left + snare_gain * snare_env * carrier + riser,
                            right + snare_gain * snare_env * carrier + riser)).astype(np.float32)
