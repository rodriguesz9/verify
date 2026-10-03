"""Configuration presence only: no secret values and no billable health probes."""
import os
import shutil
from app.services.evidence_policy import POLICY_VERSION


def capability_report():
    def configured(*keys):
        return all(bool(os.getenv(key, "").strip()) for key in keys)
    def provider(*keys):
        return {"configured": configured(*keys), "operational_status": "not_tested"}
    return {"policy_version": POLICY_VERSION,
            "warning": "Configuração presente não comprova credenciais válidas, acesso, quota ou precisão.",
            "truth_policy": "exact_claim_two_editorial_families",
            "providers": {"google_fact_check": provider("GOOGLE_FACT_CHECK_KEY"),
                "gemini": provider("GEMINI_API_KEY"), "sightengine_image": provider("SIGHTENGINE_API_USER", "SIGHTENGINE_API_SECRET"),
                "hive_image": provider("HIVE_IMAGE_API_KEY"), "hive_audio": provider("HIVE_AUDIO_API_KEY"),
                "hive_deepfake": provider("HIVE_DEEPFAKE_API_KEY"),
                "hive_legacy": provider("HIVE_API_KEY"), "huggingface_image": provider("HUGGINGFACE_API_TOKEN", "HUGGINGFACE_IMAGE_API_URL"),
                "assemblyai": provider("ASSEMBLYAI_API_KEY"),
                "sightengine_audio": {**provider("SIGHTENGINE_API_USER", "SIGHTENGINE_API_SECRET"),
                    "enabled": os.getenv("SIGHTENGINE_AUDIO_ENABLED", "false").lower() == "true",
                    "requires_model_entitlement": True}},
            "tools": {"ffmpeg": bool(shutil.which("ffmpeg")), "ffprobe": bool(shutil.which("ffprobe")),
                      "c2patool": bool(shutil.which("c2patool")), "exiftool": bool(shutil.which("exiftool"))},
            "unsupported_guarantees": ["identidade da pessoa", "autenticidade pela ausência de sinais",
                                       "perícia temporal completa/lip-sync", "porcentagem calibrada de verdade"]}
