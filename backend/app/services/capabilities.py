"""Configuration presence only: no secret values and no billable health probes."""
import os
import shutil
from app.services.evidence_policy import POLICY_VERSION
from app.core.openrouter_service import configured_models, OpenRouterError
from app.services.hive_service import hive_v3_enabled


def capability_report():
    def configured(*keys):
        return all(bool(os.getenv(key, "").strip()) for key in keys)
    def provider(*keys):
        return {"configured": configured(*keys), "operational_status": "not_tested"}
    try:
        models, model_status = configured_models(), "valid"
    except OpenRouterError:
        models, model_status = [], "invalid_paid_model_blocked"
    return {"policy_version": POLICY_VERSION,
            "warning": "Configuração presente não comprova credenciais válidas, acesso, quota ou precisão.",
            "truth_policy": "exact_claim_two_editorial_families",
            "providers": {"google_fact_check": provider("GOOGLE_FACT_CHECK_KEY"),
                "gemini": provider("GEMINI_API_KEY"), "sightengine_image": provider("SIGHTENGINE_API_USER", "SIGHTENGINE_API_SECRET"),
                "hive_image": provider("HIVE_IMAGE_API_KEY"), "hive_audio": provider("HIVE_AUDIO_API_KEY"),
                "hive_deepfake": provider("HIVE_DEEPFAKE_API_KEY"),
                "hive_legacy": provider("HIVE_API_KEY"), "huggingface_image": provider("HUGGINGFACE_API_TOKEN", "HUGGINGFACE_IMAGE_API_URL"),
                "hive_v3": {"configured": configured("HIVE_V3_API_KEY") or configured("HIVE_API_KEY"),
                    "enabled": hive_v3_enabled(), "media_types": os.getenv("HIVE_V3_MEDIA_TYPES", ""),
                    "operational_status": "not_tested", "requires_credit": True, "combined_image_and_deepfake": True},
                "openrouter": {**provider("OPENROUTER_API_KEY"), "enabled": os.getenv("OPENROUTER_ENABLED", "true").lower() == "true",
                    "free_only": True, "models": models, "model_configuration": model_status, "decision_role": "search_hints_only"},
                "serper": {**provider("SERPERAPI_KEY"), "decision_role": "context_only"},
                "serpapi": {**provider("SERPAPI_KEY"), "decision_role": "public_reverse_image_only_not_private_uploads"},
                "assemblyai": {**provider("ASSEMBLYAI_API_KEY"), "model": "universal-2", "decision_role": "transcription_only"},
                "sightengine_audio": {**provider("SIGHTENGINE_API_USER", "SIGHTENGINE_API_SECRET"),
                    "enabled": os.getenv("SIGHTENGINE_AUDIO_ENABLED", "false").lower() == "true",
                    "requires_model_entitlement": True}},
            "tools": {"ffmpeg": bool(shutil.which("ffmpeg")), "ffprobe": bool(shutil.which("ffprobe")),
                      "c2patool": bool(shutil.which("c2patool")), "exiftool": bool(shutil.which("exiftool"))},
            "unsupported_guarantees": ["identidade da pessoa", "autenticidade pela ausência de sinais",
                                       "perícia temporal completa/lip-sync", "porcentagem calibrada de verdade"]}
