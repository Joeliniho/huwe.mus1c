"""Los pedales del Amplificador y sus ruedas. Lo usan la ventana y el motor de audio."""

# id, nombre (es, en), ruedas: (id, es, en, mínimo, máximo, por defecto, unidad)
PEDALES = [
    ("gate", ("Puerta", "Gate"), [
        ("umbral", "Umbral", "Threshold", -80, -20, -58, "dB")]),
    ("comp", ("Compresor", "Compressor"), [
        ("umbral", "Sustain", "Sustain", -40, 0, -18, "dB"),
        ("ratio", "Ratio", "Ratio", 1, 10, 3, ":1"),
        ("nivel", "Nivel", "Level", 0, 12, 4, "dB")]),
    ("drive", ("Saturación", "Drive"), [
        ("drive", "Drive", "Drive", 0, 45, 18, "dB"),
        ("tono", "Tono", "Tone", 1500, 9000, 4500, "Hz"),
        ("nivel", "Nivel", "Level", -24, 6, -8, "dB")]),
    ("eq", ("Ecualizador", "Amp EQ"), [
        ("graves", "Graves", "Bass", -12, 12, 0, "dB"),
        ("medios", "Medios", "Mid", -12, 12, 0, "dB"),
        ("agudos", "Agudos", "Treble", -12, 12, 0, "dB")]),
    ("cab", ("Pantalla", "Cabinet"), [
        ("brillo", "Brillo", "Brightness", 2500, 9000, 5200, "Hz")]),
    ("talk", ("Talk box", "Talk box"), [
        ("sens", "Sensibilidad", "Sensitivity", 0, 100, 60, "%"),
        ("boca", "Apertura", "Mouth", 0, 100, 80, "%"),
        ("mezcla", "Mezcla", "Mix", 0, 100, 85, "%")]),
    ("trem", ("Trémolo", "Tremolo"), [
        ("vel", "Velocidad", "Speed", 0.5, 12, 5, "Hz"),
        ("prof", "Profundidad", "Depth", 0, 100, 60, "%")]),
    ("chorus", ("Chorus", "Chorus"), [
        ("vel", "Velocidad", "Speed", 0.1, 5, 0.8, "Hz"),
        ("prof", "Profundidad", "Depth", 0, 100, 35, "%"),
        ("mezcla", "Mezcla", "Mix", 0, 100, 40, "%")]),
    ("delay", ("Delay", "Delay"), [
        ("tiempo", "Tiempo", "Time", 40, 1200, 380, "ms"),
        ("repes", "Repeticiones", "Feedback", 0, 90, 30, "%"),
        ("mezcla", "Mezcla", "Mix", 0, 100, 25, "%")]),
    ("reverb", ("Reverb", "Reverb"), [
        ("sala", "Sala", "Room", 0, 100, 45, "%"),
        ("mezcla", "Mezcla", "Mix", 0, 100, 22, "%")]),
    ("master", ("Volumen", "Master"), [
        ("vol", "Volumen", "Volume", -30, 6, -6, "dB")]),
]

ENCENDIDOS = {"gate": True, "comp": False, "drive": False, "eq": True, "cab": True, "talk": False, "trem": False,
              "chorus": False, "delay": False, "reverb": True, "master": True}


def por_defecto():
    return {pid: {"on": ENCENDIDOS[pid], **{r[0]: r[5] for r in ruedas}} for pid, _, ruedas in PEDALES}


def tono(nombre_es, nombre_en, **cambios):
    t = por_defecto()
    for pid, valores in cambios.items():
        t[pid].update(valores)
    return {"nombre": (nombre_es, nombre_en), "pedales": t}


# Tonos de fábrica (sin plugin: suenan con los pedales de huwe.mus1c)
FABRICA = [
    tono("Limpio", "Clean", comp={"on": True}, reverb={"mezcla": 25}),
    tono("Limpio con trémolo", "Surf tremolo", trem={"on": True, "vel": 6, "prof": 65},
         reverb={"sala": 70, "mezcla": 35}, eq={"agudos": 3}),
    tono("Crunch", "Crunch", drive={"on": True, "drive": 16, "tono": 5000, "nivel": -8},
         eq={"medios": 2}),
    tono("Rock clásico", "Classic rock", drive={"on": True, "drive": 26, "tono": 4800, "nivel": -12},
         eq={"graves": 2, "medios": 4, "agudos": 1}, delay={"on": True, "tiempo": 320, "mezcla": 15}),
    tono("Solo", "Lead", comp={"on": True}, drive={"on": True, "drive": 32, "tono": 5500, "nivel": -14},
         eq={"medios": 5}, delay={"on": True, "tiempo": 420, "repes": 35, "mezcla": 25},
         reverb={"mezcla": 25}),
    tono("Metal", "Metal", gate={"umbral": -50}, drive={"on": True, "drive": 42, "tono": 6000, "nivel": -16},
         eq={"graves": 4, "medios": -5, "agudos": 3}, reverb={"mezcla": 12}),
    tono("Gotas de agua", "Water drops", comp={"on": True, "umbral": -24, "ratio": 4},
         eq={"graves": -2, "agudos": 4}, cab={"brillo": 7500},
         chorus={"on": True, "vel": 2.4, "prof": 22, "mezcla": 45},
         delay={"on": True, "tiempo": 285, "repes": 38, "mezcla": 32}, reverb={"sala": 80, "mezcla": 38},
         master={"vol": 0}),
    tono("Chill", "Chill", comp={"on": True}, eq={"graves": 1, "medios": -2, "agudos": 1}, cab={"brillo": 4800},
         chorus={"on": True, "vel": 0.5, "prof": 25, "mezcla": 35},
         delay={"on": True, "tiempo": 420, "repes": 25, "mezcla": 18}, reverb={"sala": 60, "mezcla": 30},
         master={"vol": -1}),
    tono("Talk box", "Talk box", comp={"on": True}, drive={"on": True, "drive": 20, "tono": 5000, "nivel": -10},
         talk={"on": True, "sens": 65, "boca": 85, "mezcla": 90}, reverb={"sala": 30, "mezcla": 15}),
    tono("Hard rock de los 80", "80s hard rock", drive={"on": True, "drive": 30, "tono": 5000, "nivel": -13},
         eq={"graves": 2, "medios": 4, "agudos": 1}, delay={"on": True, "tiempo": 400, "repes": 20, "mezcla": 12},
         reverb={"sala": 40, "mezcla": 15}),
]
