"""Hive v2 detection. Project-specific keys and exact documented class names."""
import math
import os
import httpx

HIVE_API_URL = "https://api.thehive.ai/api/v2/task/sync"


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


async def check_hive_media(file_bytes: bytes, filename: str = "media.jpg", media_type: str = "image") -> dict:
    return await _request_hive(media_type, files={"media": (filename, file_bytes)})


async def check_hive_text(text: str) -> dict:
    return await _request_hive("text", json={"text_data": text[:3000]})
