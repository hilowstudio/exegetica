# Baseten

`comfyui/` is the Image Studio's self-hosted route: a plain ComfyUI server on one H100 that scales
to zero when idle, with MiniMax H3 mounted read-only: the fl2va weights (words, first and last
frames, stills) and the ref2va weights (reference pictures and pictures at set seconds). The studio talks to it through
`webapp/studio_comfy.py`. See `docs/decisions/0017-image-studio.md`.

## Deploy

Truss lives in its own environment so its pins stay out of the app's:

```
py -3.14 -m venv %USERPROFILE%\.venvs\baseten
%USERPROFILE%\.venvs\baseten\Scripts\pip install truss
```

`truss` reads the key from the environment when both of these are set, so it never lands in a file:

```
$env:BASETEN_TRUSS_AUTH_REMOTE_URL = "https://app.baseten.co"
$env:BASETEN_TRUSS_AUTH_API_KEY = <BASETEN_API_KEY from .env>
%USERPROFILE%\.venvs\baseten\Scripts\truss push baseten\comfyui --non-interactive --promote
```

Without `--promote`, a second push builds a new deployment and leaves the old one in production.

The push prints the model ID. Put it in `.env` as `BASETEN_COMFY_MODEL_ID`, then shorten the idle
wait (Baseten's default keeps the GPU for 15 minutes after the last request):

```
PATCH https://api.baseten.co/v1/models/<model id>/deployments/<deployment id>/autoscaling_settings
{"min_replica": 0, "max_replica": 1, "scale_down_delay": 300}
```

## Costs

Baseten bills the image build per minute, and the GPU from cold start until the idle wait runs
out. A failed boot is not billed. The H100 is $6.50 an hour.
