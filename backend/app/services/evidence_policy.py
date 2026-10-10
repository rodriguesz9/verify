"""Conservative, reproducible decisions. Scores are NOT calibrated accuracy."""
import math

POLICY_VERSION = "2026-10-03.2"
MEDIA_SIGNAL_VERSION = "1"
DETECTOR_FIELDS = {"sightengine": "genai_probability", "huggingface": "ai_probability", "hive": "ai_generated_score"}
AUDIO_DETECTOR_FIELDS = {"sightengine_audio": "ai_speech_score", "hive": "ai_generated_score"}


def detector_score(result: dict, field: str) -> float | None:
    if not isinstance(result, dict) or result.get("available") is not True or result.get("status", "success") != "success":
        return None
    value = result.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if math.isfinite(value) and 0 <= value <= 1 else None


def _signal_score(result: dict, field: str) -> float | None:
    """New diagnostics need explicit successful, eligible detector evidence.

    Keep the legacy decision function above unchanged. Missing status in an
    old layer is not enough to manufacture a new signal diagnostic.
    """
    if (not isinstance(result, dict) or result.get("status") != "success"
            or result.get("voting_eligible") is False
            or result.get("decision_role") == "experimental_signal"):
        return None
    return detector_score(result, field)


def media_signal(forensics: dict, kind: str = "image") -> dict:
    """Describe detector observations separately from the policy verdict.

    Fixed detector fields bound this helper. Hive image/facial heads remain
    one provider family, even when one response is exposed under two names.
    No score is a calibrated probability or proof of camera/voice identity.
    """
    fields = AUDIO_DETECTOR_FIELDS if kind == "audio" else DETECTOR_FIELDS
    ai = {name: score for name, field in fields.items()
          if (score := _signal_score(forensics.get(name, {}), field)) is not None}
    manipulation = {}
    if kind != "audio":
        sight = _signal_score(forensics.get("sightengine", {}), "deepfake_probability")
        hive = _signal_score(forensics.get("hive_deepfake", {}), "deepfake_score")
        if hive is None:
            hive = _signal_score(forensics.get("hive", {}), "deepfake_score")
        manipulation = {name: score for name, score in (("sightengine", sight), ("hive", hive))
                        if score is not None}
    high_ai = sorted(name for name, score in ai.items() if score >= .8)
    high_manipulation = sorted(name for name, score in manipulation.items() if score >= .8)
    low_ai = any(score <= .2 for score in ai.values())
    low_manipulation = any(score <= .2 for score in manipulation.values())
    if (high_ai and low_ai) or (high_manipulation and low_manipulation):
        state = "disagreement"
    elif len(high_manipulation) >= 2:
        state = "consensus_manipulation"
    elif len(high_ai) >= 2:
        state = "consensus_ai"
    elif high_manipulation:
        state = "isolated_manipulation"
    elif high_ai:
        state = "isolated_ai"
    else:
        state = "no_high_signal" if ai or manipulation else "unavailable"
    return {"version": MEDIA_SIGNAL_VERSION, "state": state, "scope": kind,
            "independent_provider_count": len(ai.keys() | manipulation.keys()),
            "ai_provider_count": len(ai), "manipulation_provider_count": len(manipulation),
            "valid_providers": {"ai": sorted(ai), "manipulation": sorted(manipulation)},
            "strong_providers": {"ai": high_ai, "manipulation": high_manipulation}}


def media_signal_explanation(signal: dict, kind: str = "image") -> str | None:
    """Qualified public wording for inconclusive detector observations only."""
    state = signal.get("state")
    if kind == "video":
        return {
            "isolated_ai": "Há sinais isolados de possível geração por IA em quadros amostrados. Não houve confirmação independente no mesmo quadro; isso não determina a origem do vídeo inteiro.",
            "isolated_manipulation": "Há sinais isolados de possível manipulação facial em quadros amostrados. Não houve confirmação independente no mesmo quadro; isso não verifica o vídeo inteiro nem identifica a pessoa.",
            "disagreement": "Detectores discordaram em pelo menos um quadro amostrado. A origem visual do vídeo continua inconclusiva.",
            "no_high_signal": "Não apareceram sinais fortes nos quadros amostrados. Isso não comprova autenticidade do vídeo inteiro.",
            "unavailable": "As consultas não permitiram analisar a origem dos quadros amostrados. Isso não determina a origem do vídeo inteiro.",
        }.get(state)
    if kind == "audio":
        return {
            "isolated_ai": "Um detector encontrou sinal de possível fala sintética no áudio. Isso ainda não confirma a origem da voz, não identifica a pessoa e não comprova clonagem.",
            "disagreement": "Detectores discordaram sobre a produção do áudio. A origem da gravação continua inconclusiva.",
            "no_high_signal": "Não apareceram sinais fortes nas consultas realizadas sobre este áudio. Isso não comprova autenticidade da gravação.",
            "unavailable": "As consultas não permitiram analisar a origem deste áudio.",
        }.get(state)
    return {
        "isolated_ai": "Um detector encontrou sinal de possível geração por IA. Falta confirmação independente; a origem da imagem permanece inconclusiva.",
        "isolated_manipulation": "Um detector encontrou sinal de possível manipulação facial. Falta confirmação independente; isso não confirma alteração da imagem nem identifica a pessoa.",
        "disagreement": "Detectores discordaram sobre a produção da imagem. A origem continua inconclusiva; confira o arquivo original.",
        "no_high_signal": "Não apareceram sinais fortes nas consultas realizadas sobre esta imagem. Isso não comprova autenticidade.",
        "unavailable": "As consultas não permitiram analisar a origem desta imagem.",
    }.get(state)


def media_report(forensics: dict, kind: str = "image") -> dict:
    fields = AUDIO_DETECTOR_FIELDS if kind == "audio" else DETECTOR_FIELDS
    scores = {name: detector_score(forensics.get(name, {}), field) for name, field in fields.items()}
    observed = {name: value for name, value in scores.items() if value is not None and forensics.get(name, {}).get("voting_eligible", True) is not False}
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
                       "decision_role": result.get("decision_role"), "voting_eligible": result.get("voting_eligible", True),
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
            "decision_role": "transcription_only", "provider": speech.get("transcription_provider") or detail.get("provider"),
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
    if any(result.get("voting_eligible") is False for result in forensics.values() if isinstance(result, dict)):
        limitations.append("Detectores experimentais são exibidos para inspeção, mas não participam do veredito sem validação em conjunto independente.")
    if deepfake:
        explanation = "Há indícios concordantes de possível manipulação facial nos detectores disponíveis. Isso requer confirmação humana."
    elif deep_high:
        explanation = "Há um sinal de possível manipulação facial, mas a evidência é insuficiente para concluir."
    elif ai:
        explanation = "Há indícios concordantes de geração por IA nas camadas disponíveis. Confirme a procedência antes de concluir."
    elif not observed:
        explanation = "Não houve evidência utilizável de detectores habilitados para decidir. Camadas experimentais ou indisponíveis não determinam a origem deste arquivo."
    elif high:
        explanation = "Há um sinal de possível geração por IA, mas a evidência é insuficiente ou contraditória."
    else:
        explanation = "Os detectores disponíveis não trouxeram evidência suficiente para confirmar geração por IA nem autenticidade."
    signal = media_signal(forensics, kind)
    if not ai and not deepfake:
        explanation = media_signal_explanation(signal, kind) or explanation
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
        "media_signal": signal,
        "policy_version": POLICY_VERSION, "model_used": "evidence_policy",
        "content_type": kind,
    }


def forensic_contract(report: dict) -> dict:
    return {**report, "veredito_final": "deepfake" if report["verdict"] == "Manipulated" else "gerado_ia" if report["verdict"] == "AI_Generated" else "inconclusivo",
            "confianca_geral": None, "camadas_concordantes": [], "camadas_contraditorias": [],
            "evidencias_chave": report.get("red_flags", []), "explicacao_forense": report["plain_explanation"],
            "explicacao_leiga": report["summary"], "dica_seguranca": report["elderly_tip"],
            "recomendacao": "revisar_manualmente"}
