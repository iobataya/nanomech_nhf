import logging

# Suppress noisy font matching debug logs while keeping project DEBUG logs visible.
logging.getLogger("matplotlib.font_manager").setLevel(logging.WARNING)
