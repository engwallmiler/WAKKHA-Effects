"""Perfil offline sem rede nem hardware, usando cinco segundos do demo."""
import cProfile
import pstats
import numpy as np
from beatlight.audio.demo import structure_demo_samples
from beatlight.contracts import AudioBlock
from beatlight.dsp.pipeline import AudioAnalyzer

analyzer = AudioAnalyzer()
profiler = cProfile.Profile()
profiler.enable()
for seq, first in enumerate(range(0, 48000 * 5, 512)):
    t = np.arange(first, first+512) / 48000
    samples = structure_demo_samples(t)
    samples.setflags(write=False)
    at = 100 + first / 48000
    analyzer.process(AudioBlock("profile", samples, 48000, 2, seq, 512, at, at+512/48000))
profiler.disable()
pstats.Stats(profiler).sort_stats("cumulative").print_stats(30)
