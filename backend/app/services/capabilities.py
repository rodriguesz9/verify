"""Configuration presence only: no secret values and no billable health probes."""
import os
import shutil
from app.services.evidence_policy import POLICY_VERSION
from app.services.claim_policy import POLICY_VERSION as CLAIM_POLICY_VERSION
from app.core.openrouter_service import configured_models, OpenRouterError
from app.services.hive_service import hive_v3_enabled, HiveV3Budget


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
            "policy_versions": {"media": POLICY_VERSION, "claim_review": CLAIM_POLICY_VERSION},
            "warning": "Configuração presente não comprova credenciais válidas, acesso, quota ou precisão.",
            "truth_policy": "published_claim_reviews",
            "truth_decision_paths": ["published_claim_reviews"],
            "providers": {"google_fact_check": provider("GOOGLE_FACT_CHECK_KEY"),
                "gemini": {**provider("GEMINI_API_KEY"), "media_model": os.getenv("GEMINI_MEDIA_MODEL_NAME", "") or "inherits_primary",
                    "decision_role": "claims_explanation_and_media_reading_only",
                    "roles": ["search_hints_only", "report_explanation", "ocr_only", "inspection_only", "transcription_only"]},
                "sightengine_image": provider("SIGHTENGINE_API_USER", "SIGHTENGINE_API_SECRET"),
                "hive_image": provider("HIVE_IMAGE_API_KEY"), "hive_audio": provider("HIVE_AUDIO_API_KEY"),
                "hive_deepfake": provider("HIVE_DEEPFAKE_API_KEY"),
                "hive_legacy": provider("HIVE_API_KEY"), "huggingface_image": {**provider("HUGGINGFACE_API_TOKEN", "HUGGINGFACE_IMAGE_API_URL"),
                    "enabled": os.getenv("HUGGINGFACE_ENABLED", "false").strip().lower() == "true",
                    "decision_role": "experimental_signal", "voting_eligible": False},
                "hive_v3": {"configured": configured("HIVE_V3_API_KEY") or configured("HIVE_API_KEY"),
                    "enabled": hive_v3_enabled(), "media_types": os.getenv("HIVE_V3_MEDIA_TYPES", ""),
                    "local_admission": {"scope": "process", "resets_on_restart": True,
                        "images_enabled": bool(HiveV3Budget._limit("HIVE_V3_IMAGE_REQUEST_LIMIT")),
                        "audio_enabled": bool(HiveV3Budget._limit("HIVE_V3_AUDIO_SECONDS_LIMIT"))},
                    "operational_status": "not_tested", "requires_credit": True, "combined_image_and_deepfake": True},
                "openrouter": {**provider("OPENROUTER_API_KEY"), "enabled": os.getenv("OPENROUTER_ENABLED", "true").lower() == "true",
                    "free_only": True, "models": models, "model_configuration": model_status,
                    "decision_role": "search_assistance_only", "roles": ["search_hints_only", "ocr_only"]},
                "serper": {**provider("SERPERAPI_KEY"), "decision_role": "source_discovery_only",
                    "search_snippets_are_decisive_evidence": False},
                "serpapi": {**provider("SERPAPI_KEY"), "decision_role": "public_reverse_image_only_not_private_uploads"},
                "assemblyai": {**provider("ASSEMBLYAI_API_KEY"), "model": "universal-2", "decision_role": "transcription_only",
                    "preferred_for_transcription": os.getenv("AUDIO_TRANSCRIPTION_PROVIDER", "gemini") == "assemblyai"},
                "sightengine_audio": {**provider("SIGHTENGINE_API_USER", "SIGHTENGINE_API_SECRET"),
                    "enabled": os.getenv("SIGHTENGINE_AUDIO_ENABLED", "false").lower() == "true",
                    "requires_model_entitlement": True}},
            "tools": {"ffmpeg": bool(shutil.which("ffmpeg")), "ffprobe": bool(shutil.which("ffprobe")),
                      "c2patool": bool(shutil.which("c2patool")), "exiftool": bool(shutil.which("exiftool")),
                      "tesseract": bool(shutil.which("tesseract")), "local_ocr_enabled": os.getenv("LOCAL_OCR_ENABLED", "true").lower() == "true"},
            "unsupported_guarantees": ["identidade da pessoa", "autenticidade pela ausência de sinais",
                                       "perícia temporal completa/lip-sync", "porcentagem calibrada de verdade"]}
