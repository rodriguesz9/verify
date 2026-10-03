"""One media workflow shared by uploads, demos, PDFs and WhatsApp."""
import asyncio
from fastapi import HTTPException
from app.core.gemini_analyzer import analyze_image_with_vision, extract_text_from_image
from app.core.sightengine_client import check_deepfake
from app.core.huggingface_client import check_ai_image_hf
from app.services.hive_service import check_hive_media
from app.services.metadata_service import extract_metadata
from app.services.c2pa_service import verify_c2pa
from app.services.reverse_search_service import search_context_and_provenance
from app.services.audio_service import analyze_audio_quick_for_demonstration
from app.services.speech_detector import detect_synthetic_speech
from app.services.evidence_policy import media_report, detector_score, DETECTOR_FIELDS
from app.services.media_validation import ValidatedMedia, extract_video_frames, extract_video_audio


async def check_content(text: str, origin: str, timeout: float = 30) -> dict:
    if not isinstance(text, str) or not 10 <= len(text.strip()) <= 5000:
        return {"analysis_status": "inconclusive", "veracity_status": "unverified",
                "origin": origin, "summary": "Texto extraído ausente ou fora dos limites para checagem."}
    from app.core.pipeline import run_pipeline
    try:
        result = await asyncio.wait_for(run_pipeline(text.strip()), timeout)
        return {**result["report"], "origin": origin,
                "limitations": [*result["report"].get("limitations", []), "OCR/transcrição podem conter erros: compare com o arquivo original."]}
    except Exception:
        return {"analysis_status": "inconclusive", "veracity_status": "unverified", "origin": origin,
                "summary": "Não foi possível checar o conteúdo extraído."}


async def audio_layers(data: bytes, mime_type: str) -> dict:
    suffix = {"audio/wav": "wav", "audio/mpeg": "mp3", "audio/ogg": "ogg", "audio/webm": "webm",
              "audio/flac": "flac", "audio/mp4": "m4a", "audio/aac": "aac"}.get(mime_type, "bin")
    jobs = {"audio": analyze_audio_quick_for_demonstration(data, "evidence.audio", mime_type),
            "hive": check_hive_media(data, f"evidence.{suffix}", "audio"),
            "sightengine_audio": detect_synthetic_speech(data, mime_type)}
    return dict(zip(jobs, await asyncio.gather(*(safe_layer(job) for job in jobs.values()))))


async def safe_layer(coro, timeout=18):
    try:
        result = await asyncio.wait_for(coro, timeout)
        return result if isinstance(result, dict) else {"available": False, "status": "invalid_response"}
    except asyncio.TimeoutError:
        return {"available": False, "status": "timeout", "reason": "Tempo limite da camada atingido."}
    except Exception:
        return {"available": False, "status": "error", "reason": "Não foi possível executar esta camada."}


async def image_layers(data: bytes, mime_type: str, filename: str, auxiliary=True) -> dict:
    jobs = {"sightengine": check_deepfake(data), "huggingface": check_ai_image_hf(data),
            "hive": check_hive_media(data, "evidence.jpg", "image"),
            "hive_deepfake": check_hive_media(data, "evidence.jpg", "deepfake")}
    if auxiliary:
        jobs.update({"metadata": extract_metadata(data, filename), "c2pa": verify_c2pa(data, filename),
                     "context": search_context_and_provenance(image_bytes=data, filename="evidence.jpg"),
                     "ocr": extract_text_from_image(data, mime_type),
                     "gemini_vision": analyze_image_with_vision(data, mime_type, {})})
    values = await asyncio.gather(*(safe_layer(job) for job in jobs.values()))
    return dict(zip(jobs, values))


async def video_visual_layers(media: ValidatedMedia):
    try:
        frames = await asyncio.wait_for(extract_video_frames(media), 20)
    except asyncio.TimeoutError:
        raise HTTPException(504, "Extração de quadros excedeu o tempo limite. Tente um vídeo menor.")
    results = await asyncio.gather(*(image_layers(frame, "image/jpeg", "frame.jpg", auxiliary=False)
                                    for _, frame in frames))
    return frames, results


async def video_audio_layers(media: ValidatedMedia) -> dict:
    try:
        track = await asyncio.wait_for(extract_video_audio(media), 15)
        forensics = await audio_layers(track, "audio/wav")
        report = media_report(forensics, "audio")
        report["transcription"] = forensics["audio"].get("transcription", "")
        report["content_analysis"] = await check_content(report["transcription"], "video_transcription", timeout=18)
        return report
    except Exception:
        report = media_report({}, "audio")
        report["limitations"].append("Não foi possível extrair/analisar a faixa de áudio do vídeo.")
        return report


async def analyze_media(media: ValidatedMedia) -> dict:
    if media.kind == "image":
        forensics = await image_layers(media.data, media.mime_type, media.filename)
        report = media_report(forensics)
        report["content_analysis"] = await check_content(forensics.get("ocr", {}).get("text", ""), "ocr")
        if media.details.get("frames", 1) > 1:
            report["limitations"].append("Imagem animada: detecção limitada ao primeiro quadro.")
    elif media.kind == "video":
        if media.details.get("has_audio"):
            visual, track_report = await asyncio.gather(video_visual_layers(media), video_audio_layers(media), return_exceptions=True)
            if isinstance(visual, BaseException):
                raise visual
            if isinstance(track_report, BaseException):
                raise track_report
            frames, results = visual
        else:
            frames, results = await video_visual_layers(media)
            track_report = None
        frame_reports = [media_report(result) for result in results]
        forensics = {"video": {"sampled_frames": len(frames), "timestamps_seconds": [t for t, _ in frames],
                                  "frames": [{"timestamp_seconds": frames[i][0], "detections": result,
                                              "analysis_status": frame_reports[i]["analysis_status"],
                                              "verdict": frame_reports[i]["verdict"]}
                                             for i, result in enumerate(results)]}}
        for name, field in DETECTOR_FIELDS.items():
            scores = [detector_score(result.get(name, {}), field) for result in results]
            valid = [value for value in scores if value is not None]
            forensics[name] = {"available": bool(valid), "status": "aggregate_only",
                               field: sum(valid) / len(valid) if valid else None, "analyzed_frames": len(valid),
                               "deepfake_probability" if name == "sightengine" else "deepfake_score": None}
        deep_values = [detector_score(result.get("hive_deepfake", {}), "deepfake_score") for result in results]
        deep_count = sum(value is not None for value in deep_values)
        forensics["hive_deepfake"] = {"available": bool(deep_count), "status": "aggregate_only", "deepfake_score": None,
                                     "analyzed_frames": deep_count}
        report = media_report(forensics, "video")
        # A mean across different timestamps is not same-frame agreement.
        for name in DETECTOR_FIELDS:
            count = forensics[name]["analyzed_frames"]
            report["provider_coverage"][name].update(status="success" if count == len(frames) else "partial" if count else "unavailable",
                analyzed_frames=count, sampled_frames=len(frames),
                reason="Decisão baseada em concordância no mesmo quadro; médias são apenas descritivas.")
        report["provider_coverage"]["hive_deepfake"].update(status="success" if deep_count == len(frames) else "partial" if deep_count else "unavailable",
            analyzed_frames=deep_count, sampled_frames=len(frames), reason="Modelo facial separado; decisões por quadro, não por média.")
        report["detector_disagreement"] = any(r["detector_disagreement"] for r in frame_reports)
        if any(forensics[name]["available"] for name in DETECTOR_FIELDS):
            report["summary"] = "Os quadros amostrados não apresentaram concordância suficiente para determinar geração por IA ou manipulação. Isso não comprova autenticidade."
            report["plain_explanation"] = report["whatsapp_share_text"] = report["summary"]
        if report["detector_disagreement"]:
            report["limitations"].append("Houve discordância entre detectores em pelo menos um quadro; revise os resultados por tempo.")
        flagged = next((r for r in frame_reports if r["verdict"] == "Manipulated"), None)
        if flagged is None:
            flagged = next((r for r in frame_reports if r["verdict"] == "AI_Generated"), None)
        if flagged:
            report.update(verdict=flagged["verdict"], score=20, analysis_status="partial", red_flags=flagged["red_flags"],
                          summary="Há sinais concordantes de IA ou manipulação em pelo menos um quadro amostrado. Isso não verifica o vídeo inteiro.")
            report["plain_explanation"] = report["summary"]
            report["whatsapp_share_text"] = report["summary"]
            report["authenticity_status"] = flagged["authenticity_status"]
        # Preserve disagreements and missing coverage per frame, not just means.
        report["flagged_timestamps_seconds"] = [frames[i][0] for i, r in enumerate(frame_reports)
            if r["verdict"] in {"AI_Generated", "Manipulated"}]
        if track_report is not None:
            report["audio_analysis"] = track_report
            report["transcription"] = track_report.get("transcription", "")
            report["content_analysis"] = track_report.get("content_analysis", {})
            if track_report["verdict"] == "AI_Generated":
                report.update(verdict="AI_Generated" if not flagged else report["verdict"], analysis_status="partial",
                              authenticity_status=report["authenticity_status"] if flagged else "ai_indications",
                              summary=report["summary"] + " Há também indícios concordantes de fala sintética na faixa de áudio.")
                report["plain_explanation"] = report["whatsapp_share_text"] = report["summary"]
    else:
        forensics = await audio_layers(media.data, media.mime_type)
        audio = forensics["audio"]
        report = media_report(forensics, "audio")
        report["transcription"] = audio.get("transcription", "")
        report["content_risk"] = audio.get("content_risk", {})
        report["content_analysis"] = await check_content(report["transcription"], "transcription")
        report["limitations"].append("Transcrição e indícios de golpe no discurso não determinam se a voz foi clonada.")
        if report["content_risk"].get("is_scam_pattern") and report["analysis_status"] == "inconclusive":
            report["summary"] = "A fala contém sinais de pedido financeiro suspeito. A origem da voz continua inconclusiva."
            report["plain_explanation"] = report["summary"]
            report["whatsapp_share_text"] = report["summary"]
    report["media_details"] = media.details
    report["query_input"] = media.filename
    return report
