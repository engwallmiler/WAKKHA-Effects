"""Mudanças sustentadas da mixagem, comparadas em janelas de um tempo."""


class TextureChange:
    labels = ("densidade", "ocupação", "graves", "atividade do baixo", "ataques", "brilho")
    thresholds = (.11, .13, .16, .10, .18, .10)

    def __init__(self):
        self._at = self._values = self.reference = self.current = None
        self._sum = [0.0]*6
        self._elapsed = 0.0
        self._windows = 0
        self.score = 0.0
        self.reason = ""

    def accept(self):
        if self.current is not None:
            self.reference = self.current

    def observe(self, texture, period, sensitivity):
        if texture is None or texture.silent or texture.updated_at == self._at:
            return False
        at = texture.updated_at
        values = (texture.density, texture.occupancy, texture.bass_level,
                  texture.bass_activity, min(1.0,texture.onset_rate/10), texture.brightness)
        changed = False
        if self._at is not None:
            dt = at-self._at
            if dt < 0 or dt > .6:
                self.__init__()
            else:
                window = min(.8,max(.25,period or .5))
                while dt > 1e-9:
                    chunk = min(dt,max(1e-9,window-self._elapsed))
                    self._sum = [a+v*chunk for a,v in zip(self._sum,self._values)]
                    self._elapsed += chunk
                    dt -= chunk
                    if self._elapsed >= window-1e-8:
                        self.current = tuple(v/self._elapsed for v in self._sum)
                        self._sum, self._elapsed = [0.0]*6, 0.0
                        self._windows += 1
                        if self.reference is None:
                            self.reference = self.current
                        elif self._windows == 2:
                            self.reference = tuple((a+b)/2 for a,b in zip(self.reference,self.current))
                        else:
                            scores = [abs(a-b)*sensitivity/t for a,b,t in
                                      zip(self.current,self.reference,self.thresholds)]
                            index = max(range(6),key=scores.__getitem__)
                            self.score = min(1.0,scores[index])
                            self.reason = self.labels[index] + (" ↑" if self.current[index]>self.reference[index] else " ↓")
                            changed |= scores[index] >= 1.0
                            # Pequenas flutuações acompanham o leito; uma mudança
                            # progressiva maior continua comparada ao trecho anterior.
                            if max(scores) < .5:
                                self.reference = tuple(b+(a-b)*.03 for a,b in zip(self.current,self.reference))
        self._at, self._values = at, values
        return changed
