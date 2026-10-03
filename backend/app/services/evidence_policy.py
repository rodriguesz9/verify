"""Conservative, reproducible decisions. Scores are NOT calibrated accuracy."""
import math

POLICY_VERSION = "2026-10-03.1"
DETECTOR_FIELDS = {"sightengine": "genai_probability", "huggingface": "ai_probability", "hive": "ai_generated_score"}
AUDIO_DETECTOR_FIELDS = {"sightengine_audio": "ai_speech_score", "hive": "ai_generated_score"}


def detector_score(result: dict, field: str) -> float | None:
    if not isinstance(result, dict) or result.get("available") is not True or result.get("status", "success") != "success":
        return None
    value = result.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if math.isfinite(value) and 0 <= value <= 1 else None


def media_report(forensics: dict, kind: str = "image") -> dict:
    fields = AUDIO_DETECTOR_FIELDS if kind == "audio" else DETECTOR_FIELDS
    scores = {name: detector_score(forensics.get(name, {}), field) for name, field in fields.items()}
    observed = {name: value for name, value in scores.items() if value is not None}
    high = [name for name, value in observed.items() if value >= .8]
    low = [name for name, value in observed.items() if value <= .2]
    c2pa = forensics.get("c2pa", {})
    signed_ai = c2pa.get("validation_state") == "valid" and c2pa.get("generative_ai_flag") is True and kind != "audio"
    consensus_ai = len(high) >= 2 and not low
    ai = consensus_ai or signed_ai
    dedicated_deep = detector_score(forensics.get("hive_deepfake", {}), "deepfake_score")
    deep_name = "hive_deepfake" if dedicated_deep is not None else "hive"
    deep_scores = {"sightengine": detector_score(forensics.get("sightengine", {}), "deepfake_probability"),
                   deep_name: dedicated_deep if dedicated_deep is not None else detector_score(forensics.get("hive", {}), "deepfake_score")}
    if kind == "audio":
        deep_scores = {}
    deep_high = [name for name, value in deep_scores.items() if value is not None and value >= .8]
    deep_low = [name for name, value in deep_scores.items() if value is not None and value <= .2]
    deepfake = len(deep_high) >= 2 and not deep_low
    coverage = {name: {"status": "success" if scores.get(name) is not None or deep_scores.get(name) is not None else result.get("status", "unavailable"),
                       "ai_score": scores.get(name), "deepfake_score": deep_scores.get(name),
                       "reason": result.get("reason") or result.get("error"),
                       "api_version": result.get("api_version"), "model_used": result.get("model_used"),
                       "shared_request": result.get("shared_request")}
                for name in [*fields, *(["hive_deepfake"] if kind != "audio" and "hive_deepfake" in forensics else [])]
                for result in [forensics.get(name, {})]}
    for name, role in (("ocr", "ocr_only"), ("gemini_vision", "inspection_only")):
        result = forensics.get(name)
        if isinstance(result, dict):
            coverage[name] = {"status": result.get("status", "unavailable"), "decision_role": role,
                              "provider": result.get("provider", "gemini"), "model_used": result.get("model_used"),
                              "reason": result.get("reason") or result.get("error"), "ai_score": None, "deepfake_score": None}
    speech = forensics.get("audio")
    if isinstance(speech, dict):
        detail = speech.get("transcription_detail")
        detail = detail if isinstance(detail, dict) else {}
        coverage["transcription"] = {"status": "success" if speech.get("transcription") else detail.get("status", "unavailable"),
            "decision_role": "transcription_only", "provider": speech.get("transcription_provider"),
            "reason": detail.get("reason"), "model_used": detail.get("model_used"), "ai_score": None, "deepfake_score": None}
    limitations = [
        "Ausência de sinais de IA não comprova autenticidade ou veracidade da cena.",
        "Pontuações de detectores são sinais não calibrados; compressão e edição podem gerar erros.",
        "EXIF e nomes de arquivo podem ser alterados e não comprovam a origem.",
        "A inspeção visual por IA é auxiliar e não constitui perícia conclusiva.",
    ]
    if kind == "video":
        limitations.append("Quadros selecionados não verificam todo o vídeo, sincronização labial ou identidade; áudio é uma camada separada quando disponível.")
    if kind == "audio":
        limitations.append("Um sinal em um trecho não determina que toda a gravação seja sintética; veja os segmentos quando o detector os disponibilizar.")
    disagreement = bool((low and high) or (deep_low and deep_high))
    if disagreement:
        limitations.append("Detectores discordaram: revisão humana necessária.")
    if deepfake:
        explanation = "Há indícios concordantes de possível manipulação facial nos detectores disponíveis. Isso requer confirmação humana."
    elif deep_high:
        explanation = "Há um sinal de possível manipulação facial, mas a evidência é insuficiente para concluir."
    elif ai:
        explanation = "Há indícios concordantes de geração por IA nas camadas disponíveis. Confirme a procedência antes de concluir."
    elif not observed:
        explanation = "Não houve resposta válida dos detectores de IA. Não é possível determinar a origem deste arquivo."
    elif high:
        explanation = "Há um sinal de possível geração por IA, mas a evidência é insuficiente ou contraditória."
    else:
        explanation = "Os detectores disponíveis não trouxeram evidência suficiente para confirmar geração por IA nem autenticidade."
    return {
        "verdict": "Manipulated" if deepfake else "AI_Generated" if ai else "Suspicious",
        "score": 20 if ai or deepfake else 50,
        "analysis_status": "partial" if ai or deepfake else "inconclusive",
        "confidence": None, "authenticity_percentage": None,
        "score_semantics": "legacy_decision_index_not_probability",
        "veracity_status": "unverified",
        "authenticity_status": "manipulation_indications" if deepfake else "ai_indications" if ai else "undetermined",
        "detector_disagreement": disagreement,
        "summary": explanation, "plain_explanation": explanation,
        "elderly_tip": "Confirme com a pessoa ou fonte original por outro canal. Não envie dinheiro com base nesta mídia.",
        "red_flags": ["Sinais de possível manipulação facial"] if deepfake else ["Sinais de geração por IA" ] if ai else [], "positives": [],
        "whatsapp_share_text": f"🔎 Verify: {explanation} Não é uma garantia de autenticidade.",
        "provider_coverage": coverage, "limitations": limitations, "forensics": forensics,
        "policy_version": POLICY_VERSION, "model_used": "evidence_policy",
        "content_type": kind,
    }


def forensic_contract(report: dict) -> dict:
    return {**report, "veredito_final": "deepfake" if report["verdict"] == "Manipulated" else "gerado_ia" if report["verdict"] == "AI_Generated" else "inconclusivo",
            "confianca_geral": None, "camadas_concordantes": [], "camadas_contraditorias": [],
            "evidencias_chave": report.get("red_flags", []), "explicacao_forense": report["plain_explanation"],
            "explicacao_leiga": report["summary"], "dica_seguranca": report["elderly_tip"],
            "recomendacao": "revisar_manualmente"}
