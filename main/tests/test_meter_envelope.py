"""A redução visual rápida conserva todos os extremos, inclusive nas bordas."""
import numpy as np
import pytest
from beatlight.dsp.meter import LevelAnalyzer


@pytest.mark.parametrize("frames", [1, 17, 479, 480, 481, 512, 1025, 9600, 9701])
@pytest.mark.parametrize("channels", [1, 2])
def test_all_envelope_bins_preserve_extremes_for_uneven_and_partial_windows(block_factory, frames, channels):
    signal = np.random.default_rng(11).uniform(-.9, .9, (frames, channels)).astype(np.float32)
    snapshot = LevelAnalyzer().process(block_factory(signal))
    columns = min(480, frames)
    # Especificação do envelope: 480 partições contíguas da janela, com min/max.
    for channel in range(channels):
        actual = snapshot.waveform[channel]
        assert len(actual) == columns * 2
        for column in range(columns):
            left = column * frames // columns
            right = (column + 1) * frames // columns
            interval = signal[left:right, channel]
            assert actual[column*2] == float(min(interval))
            assert actual[column*2+1] == float(max(interval))


def test_visual_window_retains_latest_200ms_in_correct_channel_order(block_factory):
    analyzer = LevelAnalyzer()
    for seq in range(25):
        signal = np.full((512, 2), (seq / 100, -seq / 100), dtype=np.float32)
        snapshot = analyzer.process(block_factory(signal, sequence=seq))
    assert len(snapshot.waveform[0]) == len(snapshot.waveform[1]) == 960
    assert max(snapshot.waveform[0]) == pytest.approx(.24)
    assert min(snapshot.waveform[1]) == pytest.approx(-.24)
    assert min(snapshot.waveform[0]) > .05  # blocos antigos saíram da janela
    assert max(snapshot.waveform[1]) < -.05
