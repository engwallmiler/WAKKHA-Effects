"""Desenhos espaciais e ritmos de um ciclo de oito tempos."""
from collections import deque
from random import Random
from beatlight.lighting.show import PATTERNS, NAMES

MOTIFS = {"unison": (15,)*8, "chase": PATTERNS["chase"], "reverse": (8,4,2,1)*2,
          **{k: PATTERNS[k] for k in ("pairs", "mirror", "bounce", "sweep", "question",
                                     "cross", "wave", "double", "response")},
          "syncopated": (1,0,4,10,0,2,8,15),
          "push_pull": (9,0,6,15,9,0,6,15),
          "staircase": (1,3,0,7,8,12,0,15),
          "sparks": (1,8,2,4,8,1,4,15),
          "pendulum": (9,1,6,2,9,8,6,15),
          "offbeat": (0,2,0,8,0,4,0,15),
          "staccato": (15,0,5,0,15,0,10,15),
          "heartbeat": (15,0,9,0,15,0,6,15),
          "comet": (1,3,2,6,4,12,8,15),
          "ripple": (9,6,0,15,1,2,4,8),
          "braid": (3,4,10,1,12,2,5,8),
          "fan": (6,9,15,0,1,3,7,15),
          "delayed": (0,1,2,4,0,8,4,15),
          "gallop": (1,2,4,8,9,6,5,15),
          "orbit": (1,4,8,2,3,12,6,15),
          "echo": (9,9,0,6,6,0,15,15)}
MOTIF_NAMES = {**NAMES, "unison": "Todos juntos", "reverse": "Sequência inversa",
    "syncopated": "Síncope", "push_pull": "Chamada no contratempo",
    "staircase": "Escada com pausas", "sparks": "Saltos",
    "pendulum": "Pêndulo", "offbeat": "Contratempos",
    "staccato": "Cortes rítmicos", "heartbeat": "Pulso duplo",
    "comet":"Cometa", "ripple":"Ondulação com pausa", "braid":"Trançado",
    "fan":"Abertura em leque", "delayed":"Sequência atrasada", "gallop":"Galope",
    "orbit":"Órbita", "echo":"Ecos de pares"}
BANK = tuple(MOTIFS)
# Uma entrada por colcheia; as pausas e respostas mudam o ritmo, além da ordem.
RHYTHMS = {
    "syncopated": (1,0,0,2,4,0,10,0,0,8,2,0,8,4,15,0),
    "push_pull": (9,0,0,6,6,0,15,0,9,0,0,6,6,9,15,0),
    "staircase": (1,0,3,0,0,7,7,0,8,0,12,0,0,14,15,0),
    "sparks": (1,4,8,0,2,0,4,8,8,2,1,0,4,0,15,0),
    "pendulum": (9,0,1,0,6,0,2,4,9,0,8,0,6,0,15,0),
    "offbeat": (0,1,2,0,0,4,8,0,0,8,4,0,0,2,15,0),
    "staccato": (15,0,0,0,5,0,0,10,15,0,0,0,10,0,15,0),
    "heartbeat": (15,15,0,0,9,9,0,0,15,15,0,0,6,6,15,0),
    "comet": (1,3,2,0,4,6,8,0,8,12,4,0,2,3,15,0),
    "ripple": (9,0,6,0,0,0,15,0,1,2,4,8,8,4,2,1),
    "braid": (3,0,4,8,10,0,1,2,12,0,2,1,5,0,8,4),
    "fan": (6,0,9,0,15,0,0,0,1,3,7,15,8,12,14,15),
    "delayed": (0,1,2,0,4,0,8,0,0,8,4,0,2,1,15,0),
    "gallop": (1,0,2,4,4,0,8,1,9,0,6,9,5,0,15,10),
    "orbit": (1,4,8,0,2,8,4,0,3,0,12,0,6,9,15,0),
    "echo": (9,9,0,0,6,6,0,0,15,0,15,0,9,6,15,0),
}
RHYTHM_NAMES = {k: ("Colcheias e pausas" if k in RHYTHMS else
    "Pulsos largos" if k in ("unison","wave","sweep") else "Batidas com acentos")
    for k in MOTIFS}
FAMILIES = {k: ("broken" if k in RHYTHMS else "paired" if k in ("pairs","mirror","cross")
    else "all" if k=="unison" else "growing" if k=="sweep" else "travel") for k in MOTIFS}


def slots_for(pattern):
    return RHYTHMS.get(pattern, tuple(v for mask in MOTIFS[pattern] for v in (mask,0)))


class PatternPicker:
    """Sorteio somente na troca musical, evitando a família e os últimos desenhos."""
    def __init__(self, seed=17):
        self.random = Random(seed)
        self.recent = deque(maxlen=3)

    def choose(self, current, complexity=1.0):
        bank = BANK if complexity >= .35 else ("unison","chase","reverse","mirror","question")
        options = [k for k in bank if k != current and k not in self.recent
                   and FAMILIES[k] != FAMILIES[current]]
        if not options:
            options = [k for k in bank if k != current]
        chosen = self.random.choice(options)
        self.recent.append(current)
        return chosen
