"""Descritores fixos do sinal original; ataques gerais e de percussão separados."""
from collections import deque
from statistics import median
import math
import numpy as np
from beatlight.contracts import AudioBlock, StructureFeatures
from beatlight.dsp.config import DspConfig
from beatlight.dsp.preprocess import AudioPreprocessor
from beatlight.dsp.spectrum import StreamingSpectrum


class AttackEnvelope:
    """Fluxo adaptativo com cruzamento/novo ataque; até rolls de ~20 ataques/s.

    Refratário curto não produz redisparo enquanto o mesmo ataque continua
    subindo. Mediana em Python e limiar a 20 Hz evitam trabalho extra no DSP.
    """
    def __init__(self, floor, ceiling):
        self.floor, self.ceiling = floor, ceiling
        self.history = deque(maxlen=120)
        self.previous = None
        self.previous_power = None
        self.attack_power = 0.0
        self.scores = (0.0, 0.0)
        self.threshold = floor
        self.last_at = -math.inf

    def process(self, power, at, frame_id):
        self.attack_power = (float(np.maximum(power - self.previous_power, 0).sum())
                             if self.previous_power is not None else 0.0)
        self.previous_power = power
        magnitude = np.sqrt(power)
        score = (float(np.maximum(magnitude - self.previous, 0).sum()) /
                 max(float(magnitude.sum()), 1e-12) if self.previous is not None else 0.0)
        if frame_id % 5 == 0 and self.history:
            center = median(self.history)
            mad = median(abs(value - center) for value in self.history)
            self.threshold = min(self.ceiling, max(self.floor, center + 2.5 * mad))
        previous, older = self.scores
        rising = score > previous and previous <= older
        crossing = score > self.threshold and previous <= self.threshold
        audible = float(power.sum()) > 10 ** (-65 / 10)
        onset = bool(len(self.history) >= 8 and audible and score > self.threshold
                     and (rising or crossing) and at - self.last_at >= 0.04)
        if onset:
            self.last_at = at
        if frame_id % 5 == 0:
            self.history.append(score)
        self.previous, self.scores = magnitude, (score, previous)
        return onset


class StructureFeatureExtractor:
    def __init__(self):
        self.config = DspConfig(fft_size=2048, fft_overlap=75)
        self.reset()

    def reset(self):
        self._signature = None
        self._preprocessor = None
        self._spectrum = StreamingSpectrum(self.config)
        self._general = AttackEnvelope(0.12, 0.55)
        self._percussion = AttackEnvelope(0.08, 0.4)
        self._masks = None
        self._texture_masks = None
        self._spectral_background = None
        self._novelty_at = None

    def push(self, block: AudioBlock) -> list[StructureFeatures]:
        signature = block.sample_rate, block.channels
        if signature != self._signature:
            self.reset()
            self._signature = signature
            self._preprocessor = AudioPreprocessor(self.config, *signature)
        result = []
        samples = self._preprocessor.process(block.samples)
        for frame in self._spectrum.push(samples, block.sample_rate, block.acquired_at):
            freq, power = frame.frequencies, frame.power
            if self._masks is None:
                self._masks = ((freq >= 30) & (freq < 180), (freq >= 2000) & (freq < 16000),
                    (freq >= 300) & (freq < 16000), (freq >= 30) & (freq < 16000),
                    (freq >= 300) & (freq < 3000))
                edges = np.geomspace(30, min(16000, block.sample_rate / 2), 13)
                self._texture_masks = tuple((freq >= a) & (freq < b) for a, b in zip(edges, edges[1:]))
            low, high, attacks, visible, percussion = self._masks
            at = (frame.started_at + frame.ended_at) / 2
            onset = self._general.process(power[attacks], at, frame.id)
            roll_onset = self._percussion.process(power[percussion], at, frame.id)
            # Rejeita vazamento espectral de hats: o ataque precisa ter corpo em médios.
            roll_onset = bool(roll_onset and self._percussion.attack_power >
                max(self._general.attack_power * 0.12, float(power[attacks].sum()) * 0.01))
            shape_power = power[(freq >= 30) & (freq < 250)]
            shape = np.sqrt(shape_power / max(float(shape_power.sum()), 1e-12))
            total = float(power[visible].sum())
            centroid = float((power[visible] * freq[visible]).sum()) / max(total, 1e-12)
            db = lambda mask: float(10 * np.log10(max(float(power[mask].sum()), 1e-12)))
            bands = np.asarray([float(power[mask].sum()) for mask in self._texture_masks])
            distribution = bands / max(float(bands.sum()), 1e-12)
            novelty = float(np.abs(distribution-self._spectral_background).sum()*.5) if self._spectral_background is not None else 0.0
            if total>1e-6:
                amount = 1-math.exp(-max(0,at-self._novelty_at)/.9) if self._novelty_at is not None else 1.0
                self._spectral_background = distribution if self._spectral_background is None else self._spectral_background+(distribution-self._spectral_background)*amount
                self._novelty_at = at
            result.append(StructureFeatures(frame.id, at, db(low), db(high),
                float(10 * np.log10(max(total, 1e-12))), min(1.0, centroid / 8000),
                onset, roll_onset, db(percussion), tuple(float(v) for v in shape),
                db((freq >= 250) & (freq < 1500)), db((freq >= 30) & (freq < 250)),
                tuple(float(10*np.log10(max(value,1e-12))) for value in bands),
                min(1.0,max(0.0,self._general.scores[0])),min(1.0,max(0.0,novelty))))
        return result
