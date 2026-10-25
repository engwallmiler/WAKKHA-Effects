"""Efeitos determinísticos sobre descritores musicais e relógio monotônico.

Prioridade: blackout > desarmado > manual > automação. Sem canais DMX,
renderização, acesso a driver ou análise de amostras.
"""
from dataclasses import replace
import math
from beatlight.contracts import FixtureDefinition, FixtureState, LightingInput, LightingSnapshot
from beatlight.lighting.config import LightingControls, PALETTES
from beatlight.lighting.fixtures import default_fixtures
from beatlight.lighting.musical import MusicalProfile, visual_profile
from beatlight.music.clock import project_clock
from beatlight.music.grid import grid_clock
from beatlight.lighting.colors import automatic_colors, automatic_texture_colors
from beatlight.lighting.show import ShowSequencer, ShowFrame, NAMES
from beatlight.lighting.movers import MoverSequencer
from beatlight.lighting.breakdown import BreakdownWash
from beatlight.lighting.rgbw import preview_rgb, to_rgbw
from beatlight.lighting.phrase import PhraseSequencer, MOTIF_NAMES
from beatlight.lighting.phrase_clock import PhraseClock


def envelope(age: float, duration: float) -> float:
    return max(0.0, 1 - max(0.0, age) / duration) ** 2 if age >= 0 else 0.0


class LightingEngine:
    def __init__(self, fixtures: tuple[FixtureDefinition, ...] | None = None):
        self.fixtures = fixtures if fixtures is not None else default_fixtures()
        ids = [f.fixture_id for f in self.fixtures]
        if not ids or len(set(ids)) != len(ids) or any(not i for i in ids):
            raise ValueError("Inventário deve conter identificadores únicos e não vazios.")
        if any(f.kind not in ("par", "moving_head") or not {"intensity", "rgb"} <= set(f.capabilities)
               or not ({"A", "B"} & set(f.groups)) or {"A", "B"} <= set(f.groups) for f in self.fixtures):
            raise ValueError("Luminária abstrata inválida ou grupo A/B ambíguo.")
        self._base = tuple(FixtureState(f.fixture_id, 0.0, (0.0, 0.0, 0.0), 0.5, 0.5) for f in self.fixtures)
        self._controls = None
        self._transition_from = None
        self._transition_at = 0.0
        self._ambient_at = None
        self._last_at = -math.inf
        self._frame_id = 0
        self._musical_at = None
        self._musical_profile = None
        self._motion_cycles = 0.0
        self._breathe_cycles = 0.0
        self._movement_hz = self._white_mix = 0.0
        self._texture_at = None
        self._texture_cycles = 0.0
        self._texture_hz = 0.0
        self._show = ShowSequencer()
        self._phrase = PhraseSequencer()
        self._phrase_clock = PhraseClock()
        self._phrase_key = None
        self._movers = MoverSequencer()
        self._calm = BreakdownWash()

    def _dark(self):
        return tuple(replace(s, intensity=0.0, white=0.0) for s in self._base)

    def render(self, music: LightingInput, controls: LightingControls, at: float) -> LightingSnapshot:
        if not math.isfinite(at) or at < self._last_at:
            raise ValueError("Relógio da iluminação deve avançar monotonamente.")
        self._last_at = at
        self._frame_id += 1
        cfg = controls.config
        previous = self._controls
        scene_key = lambda c: (c.armed, c.manual, c.manual_rgbw, c.manual_pan, c.manual_tilt,
            c.config.light_effect, c.config.light_palette, c.config.light_color_mode, c.config.light_movement_speed)
        if previous is None or scene_key(previous) != scene_key(controls):
            self._transition_from = self._base
            self._transition_at = at
            if cfg.light_effect == "ambient" and (previous is None or not previous.armed or previous.config.light_effect != "ambient"):
                self._ambient_at = at
        if (previous is None or previous.config.light_effect != cfg.light_effect or not controls.armed
                or controls.blackout or controls.manual or not music.source_active or not music.audio_fresh):
            self._show.reset()
            self._phrase.reset()
            self._movers.reset()
            self._calm.reset()
        if previous and previous.phrase_sync_id != controls.phrase_sync_id:
            self._phrase.realign()
            self._transition_from = None
        self._phrase_frame = None
        self._phrase_gain = 1.0
        self._show_frame = None
        self._sync_flash = False
        self._mover_rhythm = ""
        self._calm_amount = 0.0
        self._controls = controls
        beat = (project_clock(music.beat, at) if music.beat and music.source_active and controls.armed
                and not controls.blackout and not controls.manual
                and cfg.light_effect in ("beat_pulse", "beat_chase", "musical", "rhythmic_show", "orchestrated_show", "phrase_show") else None)
        grid_beat = (grid_clock(music.structure.grid, at, music.beat) if music.structure
            and music.source_active and music.audio_fresh and 0 <= at - music.structure.updated_at < 0.6
            and music.structure.state != "silence" else None)
        if grid_beat and cfg.light_effect in ("beat_pulse", "beat_chase", "musical", "rhythmic_show", "orchestrated_show", "phrase_show"):
            beat = grid_beat
        beat_valid = bool(beat and beat.state in ("locked", "coasting") and beat.period and beat.confidence >= 0.35)
        beat_state = beat.state if beat else "unlocked"
        grid = music.structure.grid if music.structure else None
        phrase_key = (grid.revision, grid.phrase_origin) if grid else None
        if phrase_key != self._phrase_key:
            self._phrase.reset()
        self._phrase_key = phrase_key
        phrase_position = self._phrase_clock.project(beat, grid, controls, at, active=(
            cfg.light_effect == "phrase_show" and controls.armed
            and music.source_active and music.audio_fresh and music.structure is not None
            and 0 <= at - music.structure.updated_at < .6 and music.structure.state != "silence"))
        if phrase_position is None:
            self._phrase.reset()
        status, reason, bypass = "active", "Efeito em execução.", False
        self._movement_hz = self._white_mix = 0.0
        self._color_profile = "fixo · " + cfg.light_palette
        self._color_targets = PALETTES[cfg.light_palette]
        fresh_structure = (music.structure if music.source_active and music.audio_fresh and music.structure
            and 0 <= at - music.structure.updated_at < 0.6 and music.structure.state != "silence" else None)
        if cfg.light_color_mode == "automatic" and not controls.manual:
            if fresh_structure:
                self._color_targets, self._color_profile = automatic_colors(fresh_structure)
                if cfg.light_effect not in ("musical", "rhythmic_show", "orchestrated_show", "phrase_show") and fresh_structure.state == "buildup":
                    self._white_mix = visual_profile(fresh_structure, cfg.light_movement_speed).white_mix
                    self._color_targets = tuple(tuple(c + (1 - c) * self._white_mix for c in color) for color in self._color_targets)
            elif music.audio_fresh and music.texture and 0 <= at - music.texture.updated_at < 0.6 and not music.texture.silent:
                self._color_targets, self._color_profile = automatic_texture_colors(music.texture)
            else:
                self._color_profile = "auto · aguardando áudio; paleta de apoio"
            if (fresh_structure and fresh_structure.state in ("warming", "groove") and music.texture
                    and music.audio_fresh and 0 <= at - music.texture.updated_at < 0.6 and not music.texture.silent):
                self._color_targets, self._color_profile = automatic_texture_colors(music.texture)
        if controls.blackout:
            target, status, reason, bypass = self._dark(), "blackout", "Blackout prioritário ativo.", True
        elif not controls.armed:
            target, status, reason, bypass = self._dark(), "disabled", "Motor desativado.", True
        elif controls.manual:
            target = tuple(FixtureState(f.fixture_id, controls.manual_intensity,
                (controls.manual_red, controls.manual_green, controls.manual_blue) if controls.manual_rgbw else PALETTES[cfg.light_palette][0 if "A" in f.groups else 1],
                controls.manual_pan if "pan" in f.capabilities else 0.5,
                controls.manual_tilt if "tilt" in f.capabilities else 0.5,
                white=controls.manual_white if controls.manual_rgbw else 0.0) for f in self.fixtures)
            status, reason = "manual", "Controle manual tem prioridade sobre a automação."
        elif cfg.light_effect != "ambient" and not music.source_active:
            target, status, reason, bypass = self._dark(), "waiting", "Inicie a captura para usar o efeito musical.", True
        elif cfg.light_effect in ("beat_pulse", "beat_chase") and not beat_valid:
            target, status, reason, bypass = self._dark(), "waiting", "Aguardando sincronismo confiável do Beat Tracker.", True
        elif cfg.light_effect in ("musical", "rhythmic_show", "orchestrated_show", "phrase_show"):
            structure = music.structure
            if not music.audio_fresh or structure is None or not 0 <= at - structure.updated_at < 0.6:
                target, status, reason, bypass = self._dark(), "waiting", "Aguardando descritores recentes da estrutura musical.", True
                self._show.reset()
            elif structure.state == "silence" or (cfg.light_effect in ("rhythmic_show", "orchestrated_show", "phrase_show") and music.texture
                    and 0 <= at - music.texture.updated_at < .6 and music.texture.silent):
                target, status, reason, bypass = self._dark(), "waiting", "Silêncio: efeitos musicais em repouso.", True
                self._show.reset()
            else:
                target, status, reason = self._musical_states(music, controls, structure, at)
                if cfg.light_effect == "phrase_show" and phrase_position is not None:
                    target, reason = self._phrase_states(target, music, controls, beat, phrase_position, at)
                elif cfg.light_effect in ("rhythmic_show", "orchestrated_show", "phrase_show"):
                    target, reason = self._show_states(target, music, controls, beat if beat_valid else None, at)
        elif cfg.light_effect in ("bass_flow", "density_wash"):
            texture = music.texture
            if not music.audio_fresh or texture is None or not 0 <= at - texture.updated_at < 0.6:
                target, status, reason, bypass = self._dark(), "waiting", "Aguardando análise recente de graves e densidade.", True
            elif texture.silent or (texture.bass_db < -65 and texture.density < 0.01):
                target, status, reason, bypass = self._dark(), "waiting", "Silêncio: textura em repouso.", True
            else:
                target, status, reason = self._texture_states(texture, controls, at)
        else:
            kick_events = music.confirmed_kicks if music.confirmed_kicks is not None else music.kicks
            kick = max((k for k in kick_events if math.isfinite(k.occurred_at) and k.occurred_at <= at),
                       key=lambda k: k.occurred_at, default=None)
            states = []
            for f in self.fixtures:
                side = 0 if "A" in f.groups else 1
                color = self._color_targets[side]
                if cfg.light_color_mode == "automatic":
                    dt_color = max(0.0, at - getattr(self, "_color_at", at - 0.02))
                    mix = 1 - math.exp(-min(0.1, dt_color) / 0.3)
                    color = tuple(a + (b - a) * mix for a, b in zip(preview_rgb(self._base[len(states)]), color))
                pan, tilt = 0.5, 0.5
                if cfg.light_effect == "kick_pulse":
                    pulse_at = music.kick_confirmed_at if music.kick_confirmed_at is not None else kick.occurred_at if kick else at
                    intensity = (kick.intensity * envelope(at - pulse_at, cfg.light_pulse_ms / 1000)
                                 if kick and music.audio_fresh else 0.0)
                    reason = "Pulsos pelos kicks detectados." if music.audio_fresh else "Aguardando novos blocos de áudio."
                    if not music.audio_fresh:
                        status = "waiting"
                elif cfg.light_effect == "beat_pulse":
                    intensity = envelope(beat.phase * beat.period, cfg.light_pulse_ms / 1000)
                elif cfg.light_effect == "beat_chase":
                    fade = min(1.0, beat.phase / 0.2)
                    fade = fade * fade * (3 - 2 * fade)
                    intensity = 0.1 + 0.9 * (fade if beat.beat_index % 2 == side else 1 - fade)
                else:
                    intensity = 0.45
                    status, reason = "ambient", "Movimento ambiente independente da captura."
                if cfg.light_effect in ("beat_pulse", "beat_chase", "ambient") and cfg.light_movement_speed:
                    cycles = ((at - self._ambient_at) * 0.1 if cfg.light_effect == "ambient" else (beat.beat_index + beat.phase) / 4) * cfg.light_movement_speed
                    angle = 2 * math.pi * cycles + side * math.pi
                    if "pan" in f.capabilities:
                        pan = 0.5 + 0.35 * math.sin(angle)
                    if "tilt" in f.capabilities:
                        tilt = 0.5 + 0.2 * math.sin(angle * 0.5)
                states.append(FixtureState(f.fixture_id, intensity, color, pan, tilt))
            target = tuple(states)
            if beat_valid and cfg.light_effect in ("beat_pulse", "beat_chase"):
                reason = "Grade local estimada durante ausência de kicks." if beat.state == "coasting" else "Grade local sincronizada."
                status = "estimated" if beat.state == "coasting" else "active"
        musical_effect = cfg.light_effect in ("musical","rhythmic_show","orchestrated_show","phrase_show")
        if musical_effect and not bypass and not controls.manual and fresh_structure:
            calm = self._calm.render(at=at,structure=fresh_structure,cfg=cfg,palette=self._color_targets)
            if calm and calm.amount>1e-4:
                target = self._calm_states(target,calm)
                if calm.amount>.5:
                    reason = f"Breakdown calmo · {calm.style} · fades livres do grid"
            if fresh_structure.state in ("warming","groove"):
                position = phrase_position if cfg.light_effect=="phrase_show" else (
                    beat.beat_index+beat.phase-(grid.phrase_origin if grid else 0) if beat_valid else None)
                target = self._groove_movers(target,music,cfg,position,at)
        else:
            self._calm.reset()
        if bypass:
            self._transition_from = None
        elif self._transition_from is not None and cfg.light_transition_ms > 0:
            amount = min(1.0, max(0.0, (at - self._transition_at) / (cfg.light_transition_ms / 1000)))
            amount = amount * amount * (3 - 2 * amount)
            target = tuple(FixtureState(b.fixture_id, a.intensity + (b.intensity - a.intensity) * amount,
                tuple(x + (y - x) * amount for x, y in zip(a.color, b.color)),
                a.pan + (b.pan - a.pan) * amount, a.tilt + (b.tilt - a.tilt) * amount, a.white + (b.white - a.white) * amount)
                for a, b in zip(self._transition_from, target))
            if amount >= 1:
                self._transition_from = None
        if not controls.manual and not bypass:
            target = self._coordinate_movers(target, moving=bool(cfg.light_movement_speed))
        self._color_at = at
        self._base = target
        output = tuple(to_rgbw(replace(s, intensity=min(1.0,s.intensity * self._phrase_gain) * cfg.light_master),
            "white" in f.capabilities, cfg.light_white_strength, controls.manual and controls.manual_rgbw)
            for f, s in zip(self.fixtures, target))
        return LightingSnapshot(self._frame_id, at, output, cfg.light_effect, status, reason,
            cfg.light_master, controls.blackout, controls.manual, beat_state,
            movement_hz=self._movement_hz, white_mix=self._white_mix, color_profile=self._color_profile,
            show_pattern=self._show_frame.pattern if self._show_frame else self._phrase_frame.pattern if self._phrase_frame else "",
            show_step=self._show_frame.step if self._show_frame else self._phrase_frame.step if self._phrase_frame else 0,
            show_fills=self._show_frame.fills if self._show_frame else self._phrase_frame.changes if self._phrase_frame else 0,
            show_novelty=self._show_frame.novelty if self._show_frame else self._phrase_frame.novelty if self._phrase_frame else 0.0,
            phrase_step=self._phrase_frame.step if self._phrase_frame else 0,
            phrase_cycle=self._phrase_frame.cycle if self._phrase_frame else 0,
            phrase_phase=self._phrase_frame.phase if self._phrase_frame else 0.0,
            phrase_gain=self._phrase_gain,
            phrase_preparation=self._phrase_frame.preparation if self._phrase_frame else False,
            phrase_pending=self._phrase_frame.pending if self._phrase_frame else False,
            phrase_synced=self._phrase_clock.manual, phrase_sync_id=self._phrase_clock.command,
            phrase_pattern=self._phrase_frame.pattern if self._phrase_frame else "",
            phrase_repetition=self._phrase_frame.repetition if self._phrase_frame else 0,
            phrase_sync_flash=self._sync_flash,
            phrase_change_reason=self._phrase_frame.change_reason if self._phrase_frame else "",
            show_rhythm=self._show_frame.rhythm if self._show_frame else self._phrase_frame.rhythm if self._phrase_frame else "",
            show_masks=self._show_frame.masks if self._show_frame else self._phrase_frame.masks if self._phrase_frame else (),
            show_phase=self._show_frame.phase if self._show_frame else self._phrase_frame.phase if self._phrase_frame else 0.0,
            mover_rhythm=self._mover_rhythm, breakdown_calm=self._calm_amount>.5, breakdown_blend=self._calm_amount)

    def _groove_movers(self,states,music,cfg,position,at):
        texture=music.texture if music.texture and 0<=at-music.texture.updated_at<.6 and not music.texture.silent else None
        # Alterações de contexto mudam o motivo; o ciclo estável continua repetindo.
        key=(cfg.light_effect,self._phrase_frame.pattern if self._phrase_frame else
             self._show_frame.pattern if self._show_frame else "musical",
             self._phrase_frame.changes if self._phrase_frame else self._show_frame.fills if self._show_frame else 0)
        frame=self._movers.render(position=position,texture=texture,cfg=cfg,palette=self._color_targets,key=key)
        self._mover_rhythm=frame.rhythm
        level=frame.level
        if cfg.light_effect=="musical":
            bed=max((s.intensity for f,s in zip(self.fixtures,states) if f.kind=="moving_head"),default=0.0)
            level*=min(1.0,bed/.5)
        return tuple(replace(s,intensity=level,color=frame.color,white=frame.white)
            if f.kind=="moving_head" else s for f,s in zip(self.fixtures,states))

    def _calm_states(self,states,frame):
        self._calm_amount=frame.amount
        result=[]
        index=0
        for fixture,state in zip(self.fixtures,states):
            if fixture.kind=="par":
                amount=frame.amount
                state=replace(state,intensity=state.intensity*(1-amount)+frame.levels[index%4]*amount,
                    color=tuple(a*(1-amount)+b*amount for a,b in zip(state.color,frame.colors[index%4])),
                    white=state.white*(1-amount))
                index+=1
            result.append(state)
        if frame.amount>.5:
            if self._show_frame:
                self._show_frame=replace(self._show_frame,rhythm=frame.style+" · fade livre",step=0,masks=(),phase=0.0)
            else:
                self._show_frame=ShowFrame(frame.levels,frame.colors,"breakdown",0,0,0.0,
                    rhythm=frame.style+" · fade livre")
        return tuple(result)

    def _coordinate_movers(self, states, *, moving):
        """Moving heads formam um par; a alternância A/B pertence aos PARs."""
        indices = [i for i, f in enumerate(self.fixtures) if f.kind == "moving_head"]
        if len(indices) < 2:
            return states
        lead = states[indices[0]]
        intensity = max(states[i].intensity for i in indices)
        result = list(states)
        for order, index in enumerate(indices):
            fixture, state = self.fixtures[index], states[index]
            result[index] = replace(state, intensity=intensity, color=lead.color, white=lead.white,
                pan=(lead.pan if order % 2 == 0 else 1-lead.pan) if moving and "pan" in fixture.capabilities else state.pan,
                tilt=lead.tilt if moving and "tilt" in fixture.capabilities else state.tilt)
        return tuple(result)

    def _phrase_states(self, base, music, controls, beat, position, at):
        cfg = controls.config
        texture = music.texture if music.texture and not music.texture.silent and 0 <= at-music.texture.updated_at < .6 else None
        events = music.confirmed_kicks if music.confirmed_kicks is not None else music.kicks
        kick = max((k for k in events if k.occurred_at <= at), key=lambda k:k.occurred_at, default=None)
        pulse_at = music.kick_confirmed_at if music.kick_confirmed_at is not None else kick.occurred_at if kick else at
        pulse = kick.intensity * envelope(at-pulse_at,cfg.light_pulse_ms/1000) if kick else 0.0
        frame = self._phrase.render(at=at,position=position,period=beat.period,texture=texture,cfg=cfg,
            palette=self._color_targets,state=music.structure.state,kick=pulse)
        self._phrase_frame, self._phrase_gain = frame, frame.gain
        if music.structure.state not in ("warming", "groove"):
            result, reason = self._show_states(base,music,controls,beat,at,position=position)
            return result, reason
        sync_age = at-controls.phrase_sync_at if controls.phrase_sync_at is not None else math.inf
        self._sync_flash = bool(self._phrase_clock.manual and self._phrase_clock.command==controls.phrase_sync_id and 0<=sync_age<.22)
        result, par, mover = [], 0, 0
        for fixture,state in zip(self.fixtures,base):
            if fixture.kind == "par":
                state = replace(state,intensity=frame.levels[par%4],color=frame.colors[par%4],white=0.0)
                par += 1
            else:
                state = replace(state,intensity=frame.mover_levels[mover%2],color=frame.colors[mover%4],white=0.0)
                mover += 1
            if self._sync_flash and fixture.kind=="par":
                state = replace(state,intensity=max(state.intensity,.95),
                    color=(1.0,1.0,1.0) if cfg.light_color_mode=="automatic" else state.color,white=0.0)
            result.append(state)
        suffix = " · preparando destaque" if frame.preparation else " · troca no próximo ciclo" if frame.pending else ""
        return tuple(result), f"Ciclo {frame.cycle} · {MOTIF_NAMES[frame.pattern]} · tempo {frame.step}/8" + suffix

    def _show_states(self, base, music, controls, beat, at, position=None):
        cfg = controls.config
        texture = music.texture if music.texture and not music.texture.silent and 0 <= at - music.texture.updated_at < .6 else None
        events = music.confirmed_kicks if music.confirmed_kicks is not None else music.kicks
        kick = max((k for k in events if k.occurred_at <= at), key=lambda k: k.occurred_at, default=None)
        pulse_at = music.kick_confirmed_at if music.kick_confirmed_at is not None else kick.occurred_at if kick else at
        pulse = kick.intensity * envelope(at - pulse_at, cfg.light_pulse_ms / 1000) if kick else 0.0
        frame = self._show.render(at=at, beat=beat, structure=music.structure, texture=texture,
            cfg=cfg, palette=self._color_targets, kick=pulse, layered=cfg.light_effect in ("orchestrated_show", "phrase_show"),
            position_override=position+(music.structure.grid.phrase_origin if music.structure.grid else 0) if position is not None else None)
        self._show_frame = frame
        states, par = [], 0
        for fixture, state in zip(self.fixtures, base):
            if fixture.kind == "par":
                state = replace(state, intensity=frame.levels[par % 4], color=frame.colors[par % 4], white=frame.whites[par % 4])
                par += 1
            states.append(state)
        name = "Show RGBW" if cfg.light_effect == "orchestrated_show" else "Show"
        reason = (f"{name} · {NAMES[frame.pattern]} · {frame.rhythm} · tempo {frame.step}/8 · viradas {frame.fills}"
                  if frame.step else f"{name} · {NAMES[frame.pattern]}")
        return tuple(states), reason

    def _musical_states(self, music, controls, structure, at):
        cfg = controls.config
        state, tension = structure.state, structure.tension
        desired = visual_profile(structure, cfg.light_movement_speed)
        if music.texture and 0 <= at - music.texture.updated_at < 0.6 and state in ("warming", "groove"):
            fill = music.texture.density * cfg.light_density_weight
            desired = replace(desired, movement_hz=desired.movement_hz * (0.4 + fill + 0.25 * music.texture.bass_activity),
                pan_span=0.15 + 0.3 * fill, tilt_span=0.08 + 0.2 * fill)
        dt = min(0.1, max(0.0, at - self._musical_at)) if self._musical_at is not None else 0.0
        self._musical_at = at
        if self._musical_profile is None:
            self._musical_profile = desired
        else:
            amount = 1 - math.exp(-dt / 0.22)
            previous = self._musical_profile
            self._musical_profile = MusicalProfile(**{key: getattr(previous, key) +
                (getattr(desired, key) - getattr(previous, key)) * amount
                for key in MusicalProfile.__dataclass_fields__})
        profile = self._musical_profile
        # Integra frequência: alterar tensão/velocidade não salta a fase da senoide.
        movement_hz = profile.movement_hz if cfg.light_movement_speed else 0.0
        self._motion_cycles = (self._motion_cycles + dt * movement_hz) % 4
        self._breathe_cycles = (self._breathe_cycles + dt * profile.breathe_hz) % 1
        self._movement_hz, self._white_mix = movement_hz, profile.white_mix if cfg.light_color_mode == "automatic" else 0.0
        kick_events = (music.confirmed_kicks if music.confirmed_kicks is not None else
            structure.confirmed_kicks if structure.grid is not None else music.kicks)
        kick = max((k for k in kick_events if k.occurred_at <= at), key=lambda k: k.occurred_at, default=None)
        pulse_at = music.kick_confirmed_at if music.kick_confirmed_at is not None else kick.occurred_at if kick else at
        pulse = envelope(at - pulse_at, cfg.light_pulse_ms / 1000) if kick else 0.0
        color_amount = 1 - math.exp(-dt / (0.12 if state == "drop" else 0.3)) if dt else 1.0
        texture = music.texture if music.texture and 0 <= at - music.texture.updated_at < 0.6 else None
        bass = texture.bass_level * cfg.light_bass_weight if texture else 0.0
        density = texture.density * cfg.light_density_weight if texture else 0.0
        result = []
        for index, fixture in enumerate(self.fixtures):
            side = 0 if "A" in fixture.groups else 1
            palette_side = side ^ (((max(1, structure.drop_kicks) - 1) // 4) % 2 if state == "drop" else 0)
            color = self._color_targets[palette_side]
            pan, tilt = 0.5, 0.5
            white = profile.white_mix if cfg.light_color_mode == "automatic" else 0.0
            if state in ("breakdown", "buildup"):
                breathe = 0.5 + 0.5 * math.sin(2 * math.pi * self._breathe_cycles + side * math.pi)
                if state == "buildup":
                    intensity = 0.18 + 0.48 * tension + (0.08 + 0.08 * tension) * breathe
                else:
                    intensity = 0.05 + 0.1 * tension + (0.07 + 0.12 * tension) * breathe
                    if cfg.light_color_mode == "automatic":
                        color = tuple(c * 0.8 + cool * 0.2 for c, cool in zip(color, (0.25, 0.4, 1.0)))
            elif state == "drop":
                alternate = (structure.drop_kicks - 1) % 2 == side
                intensity = 0.75 + 0.25 * pulse + (0.1 if alternate else 0.0)
                if cfg.light_color_mode == "automatic":
                    white = min(1.0, white + 0.65 * pulse)
            else:
                accent = pulse * kick.intensity * cfg.light_kick_weight if kick else 0.0
                bed = (0.65 * bass + 0.35 * density) if fixture.kind == "par" else (0.3 * bass + 0.65 * density)
                intensity = min(1.0, bed + accent)
            if state == "breakdown" and texture:
                intensity = max(intensity, 0.25 * bass + 0.25 * density)
            color = tuple(c + (1 - c) * white for c in color)
            previous_color = preview_rgb(self._base[index])
            color = tuple(a + (b - a) * color_amount for a, b in zip(previous_color, color))
            if "pan" in fixture.capabilities:
                angle = 2 * math.pi * self._motion_cycles
                if cfg.light_movement_speed:
                    pan = 0.5 + profile.pan_span * math.sin(angle + side * math.pi)
                    tilt = 0.5 + profile.tilt_span * math.cos(angle * 0.5 + side * math.pi)
                else:
                    pan, tilt = self._base[index].pan, self._base[index].tilt
            result.append(FixtureState(fixture.fixture_id, min(1.0, intensity), color, pan, tilt))
        return tuple(result), state if state in ("breakdown", "buildup", "drop") else "active", structure.reason

    def _texture_states(self, texture, controls, at):
        cfg = controls.config
        dt = min(0.1, max(0.0, at - self._texture_at)) if self._texture_at is not None else 0.0
        self._texture_at = at
        density_mode = cfg.light_effect == "density_wash"
        drive = texture.density if density_mode else texture.bass_level
        target_hz = cfg.light_movement_speed * (0.06 + 0.6 * texture.density + 0.18 * texture.bass_activity)
        self._texture_hz += (target_hz - self._texture_hz) * (1 - math.exp(-dt / 0.25)) if dt else target_hz
        hz = self._texture_hz if cfg.light_movement_speed else 0.0
        self._texture_cycles = (self._texture_cycles + dt * hz) % 4
        self._movement_hz = hz
        states = []
        for index, fixture in enumerate(self.fixtures):
            side = 0 if "A" in fixture.groups else 1
            if density_mode:
                # Entrada gradual de luminárias; sem liga/desliga brusco ou strobe.
                spread = max(0.0, min(1.0, texture.density * 1.4 - index * 0.12))
                intensity = cfg.light_density_weight * (0.15 + 0.85 * drive) * spread
            else:
                intensity = cfg.light_bass_weight * min(1.0, drive * 0.8 + texture.bass_activity * 0.2)
            old = self._base[index]
            mix = 1 - math.exp(-dt / 0.25) if dt else 1.0
            color = tuple(a + (b - a) * mix for a, b in zip(preview_rgb(old), self._color_targets[side]))
            pan, tilt = 0.5, 0.5
            if "pan" in fixture.capabilities:
                angle = 2 * math.pi * self._texture_cycles + side * math.pi
                pan = 0.5 + (0.15 + drive * 0.25) * math.sin(angle) if hz else old.pan
                tilt = 0.5 + (0.1 + drive * 0.16) * math.cos(angle * 0.5) if hz else old.tilt
            states.append(FixtureState(fixture.fixture_id, intensity, color, pan, tilt))
        reason = (f"Densidade sonora {texture.density:.0%}: distribuição gradual dos fachos." if density_mode else
            f"Envelope dos graves {texture.bass_level:.0%}: acompanha o baixo sem exigir kicks ou BPM.")
        return tuple(states), "active", reason
