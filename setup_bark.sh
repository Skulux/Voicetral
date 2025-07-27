#!/bin/bash
# Install Bark TTS and preload models
pip install -r requirements.txt
python - <<'PY'
from bark import preload_models
preload_models()
PY
