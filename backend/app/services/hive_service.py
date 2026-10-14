"""Hive v2 projects / v3 service keys. Exact classes; no billable retries."""
import math
import os
import threading
import httpx

HIVE_API_URL = "https://api.thehive.ai/api/v2/task/sync"
HIVE_V3_MODEL = "hive/ai-generated-and-deepfake-content-detection"
HIVE_V3_API_URL = f"https://api.thehive.ai/api/v3/{HIVE_V3_MODEL}"


class HiveV3Budget:
    """Atomic process-local admission, not a provider balance/spend ledger.

    Reservations are not refunded: a timeout/cancellation/error does not prove
    the remote provider did not process the input. Counters survive local env
    changes, but not a process restart, and are not shared across replicas.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._image_requests = 0
        self._audio_seconds = 0

    @staticmethod
    def _limit(name):
        value = os.getenv(name, "0").strip()
        if not value or len(value) > 6 or not value.isascii() or not value.isdigit():
            return None
        number = int(value)
        return number if number <= 100000 else None

    def reserve(self, media_type, duration_seconds=None):
        if media_type == "image":
            name, units = "HIVE_V3_IMAGE_REQUEST_LIMIT", 1
        elif media_type == "audio":
            # Caller must supply the duration obtained during media validation,
            # never a duration guessed from byte size or user-supplied filename.
            if (isinstance(duration_seconds, bool) or not isinstance(duration_seconds, (int, float))
                    or not math.isfinite(duration_seconds) or not 0 < duration_seconds <= 120):
                return {"available": False, "status": "invalid_configuration", "api_version": "v3",
                        "reason": "Hive áudio exige duração validada entre zero e 120 segundos; nenhum arquivo foi enviado."}
            name, units = "HIVE_V3_AUDIO_SECONDS_LIMIT", math.ceil(duration_seconds)
        else:
            return {"available": False, "status": "unsupported", "api_version": "v3"}
        limit = self._limit(name)
        if limit is None:
            return {"available": False, "status": "invalid_configuration", "api_version": "v3",
                    "reason": "Limite local Hive v3 inválido; nenhum arquivo foi enviado."}
        if limit == 0:
            return {"available": False, "status": "disabled", "api_version": "v3",
                    "reason": "Chamadas Hive v3 desta modalidade desativadas por limite local zero."}
        with self._lock:
            used = self._image_requests if media_type == "image" else self._audio_seconds
            if used + units > limit:
                return {"available": False, "status": "budget_exhausted", "api_version": "v3",
                        "reason": "Limite local Hive v3 atingido; nenhum arquivo foi enviado. O saldo do fornecedor não foi consultado."}
            if media_type == "image":
                self._image_requests += units
            else:
                self._audio_seconds += units
        return None


hive_v3_budget = HiveV3Budget()


def hive_v3_enabled():
    return os.getenv("HIVE_API_VERSION", "v2").strip().lower() == "v3"


def parse_hive_v3_scores(data: dict, media_type="image") -> dict:
    """v3 uses output[].classes[].value, and a DISTINCT audio head."""
    if not isinstance(data, dict) or data.get("model") != HIVE_V3_MODEL or not isinstance(data.get("output"), list):
        return {"available": False, "status": "invalid_response", "api_version": "v3"}
    outputs = []
    for output in data["output"][:50]:
        if not isinstance(output, dict) or not isinstance(output.get("classes"), list):
            return {"available": False, "status": "invalid_response", "api_version": "v3"}
        classes = []
        for item in output["classes"]:
            if not isinstance(item, dict):
                continue
            label = item.get("class")
            if media_type == "audio":
                if label != "ai_generated_audio":
                    continue
                label = "ai_generated"
            elif label not in {"ai_generated", "deepfake"}:
                continue
            classes.append({"class": label, "score": item.get("value")})
        outputs.append({"classes": classes})
    result = parse_hive_scores({"status": [{"status": {"code": "0"}, "response": {"output": outputs}}]})
    return {**result, "api_version": "v3", "model_used": HIVE_V3_MODEL,
            "model_version": str(data.get("version", ""))[:50], "decision_role": "media_detector"}


async def _request_hive_v3(file_bytes, filename, media_type, mime_type, duration_seconds=None):
    key = (os.getenv("HIVE_V3_API_KEY") or os.getenv("HIVE_API_KEY", "")).strip()
    enabled = {part.strip() for part in os.getenv("HIVE_V3_MEDIA_TYPES", "").lower().split(",")}
    if not key or media_type not in enabled:
        return {"available": False, "status": "not_configured", "api_version": "v3",
                "reason": "Hive v3 exige Secret Key e autorização de custo em HIVE_V3_MEDIA_TYPES.",
                "ai_generated_score": None, "deepfake_score": None}
    rejected = hive_v3_budget.reserve(media_type, duration_seconds)
    if rejected is not None:
        return rejected
    try:
        async with httpx.AsyncClient(timeout=15, trust_env=False, follow_redirects=False) as client:
            response = await client.post(HIVE_V3_API_URL, headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
                                         files={"media": (filename, file_bytes, mime_type)})
        if response.status_code == 202:
            return {"available": False, "status": "pending", "api_version": "v3",
                    "reason": "Hive aceitou a tarefa, mas não retornou detecção síncrona. Não houve reenvio."}
        if response.status_code != 200:
            status = {401: "invalid_credentials", 403: "access_denied", 402: "quota_exhausted",
                      429: "rate_limited", 503: "unavailable"}.get(response.status_code, "error")
            return {"available": False, "status": status,
                    "api_version": "v3", "reason": f"Hive v3 indisponível (HTTP {response.status_code})."}
        return parse_hive_v3_scores(response.json(), media_type)
    except httpx.TimeoutException:
        return {"available": False, "status": "timeout", "api_version": "v3",
                "reason": "Tempo limite do detector Hive v3 atingido; não houve reenvio."}
    except Exception:
        return {"available": False, "status": "error", "api_version": "v3",
                "reason": "Não foi possível obter resposta válida do Hive v3."}


def parse_hive_scores(data: dict) -> dict:
    classes = {}
    segments = []
    task_errors = 0
    if not isinstance(data, dict) or not isinstance(data.get("status"), list):
        return {"available": False, "status": "invalid_response"}
    for task in data["status"]:
        if not isinstance(task, dict) or not isinstance(task.get("status"), dict) or str(task["status"].get("code")) != "0":
            task_errors += 1
            continue
        response = task.get("response")
        outputs = response.get("output") if isinstance(response, dict) else None
        if not isinstance(outputs, list):
            task_errors += 1
            continue
        for output in outputs[:50]:
            if not isinstance(output, dict):
                task_errors += 1
                continue
            faces = output.get("bounding_poly", [])
            groups = [output, *(faces if isinstance(faces, list) else [])]
            observations = {}
            for group in groups:
                items = group.get("classes", []) if isinstance(group, dict) else []
                if not isinstance(items, list):
                    continue
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    label, score = item.get("class"), item.get("score")
                    if isinstance(label, str) and not isinstance(score, bool) and isinstance(score, (int, float)) and math.isfinite(score) and 0 <= score <= 1:
                        observations[label.lower()] = max(observations.get(label.lower(), 0), float(score))
                        classes[label.lower()] = max(classes.get(label.lower(), 0), float(score))
            start, end = output.get("time"), output.get("end_time")
            if (all(isinstance(t, (int, float)) and not isinstance(t, bool) and math.isfinite(t) for t in (start, end))
                    and 0 <= start <= end <= 120 and "ai_generated" in observations):
                segments.append({"start_seconds": start, "end_seconds": end,
                                 "ai_generated_score": observations["ai_generated"]})
    # Never match substrings: not_ai_generated and not_deepfake are negative classes.
    ai, deepfake = classes.get("ai_generated"), classes.get("yes_deepfake", classes.get("deepfake"))
    available = ai is not None or deepfake is not None
    return {"available": available, "status": "partial" if available and task_errors else "success" if available else "invalid_response",
            "ai_generated_score": ai, "deepfake_score": deepfake,
            "is_ai_detected": (ai is not None and ai >= .8) or (deepfake is not None and deepfake >= .8),
            "raw_classes": classes,
            "segments": segments, "score_aggregation": "maximum_valid_observation_not_probability_of_whole_file",
            "reason": "Parte das tarefas Hive falhou; não usar como consenso completo." if task_errors else None if available else "Hive não retornou classes de detecção válidas para este projeto."}


async def _request_hive(media_type: str, **payload) -> dict:
    # Do not silently call the image/legacy project again as a deepfake model.
    legacy = "" if media_type == "deepfake" else os.getenv("HIVE_API_KEY", "")
    api_key = (os.getenv(f"HIVE_{media_type.upper()}_API_KEY") or legacy).strip()
    if not api_key:
        return {"available": False, "status": "skipped", "reason": "Chave do projeto Hive não configurada.",
                "ai_generated_score": None, "deepfake_score": None}
    try:
        async with httpx.AsyncClient(timeout=15, trust_env=False) as client:
            response = await client.post(HIVE_API_URL, headers={"Authorization": f"token {api_key}", "Accept": "application/json"}, **payload)
        if response.status_code != 200:
            return {"available": False, "status": "error", "reason": f"Hive indisponível (HTTP {response.status_code}).",
                    "ai_generated_score": None, "deepfake_score": None}
        return parse_hive_scores(response.json())
    except Exception:
        return {"available": False, "status": "error", "reason": "Não foi possível obter resposta válida do Hive.",
                "ai_generated_score": None, "deepfake_score": None}


async def check_hive_media(file_bytes: bytes, filename: str = "media.jpg", media_type: str = "image", mime_type: str = "application/octet-stream", *, duration_seconds=None) -> dict:
    if hive_v3_enabled():
        # v3 combines image and facial heads. Caller reuses ONE image request.
        if media_type == "deepfake":
            return {"available": False, "status": "skipped", "reason": "Cabeça facial incluída na única chamada Hive v3 de imagem."}
        if media_type not in {"image", "audio"}:
            return {"available": False, "status": "unsupported"}
        return await _request_hive_v3(file_bytes, filename, media_type, mime_type, duration_seconds)
    return await _request_hive(media_type, files={"media": (filename, file_bytes, mime_type)})


async def check_hive_text(text: str) -> dict:
    if hive_v3_enabled():
        return {"available": False, "status": "unsupported", "reason": "O detector Hive v3 configurado não recebe texto."}
    return await _request_hive("text", json={"text_data": text[:3000]})
