const strings = (value) => Array.isArray(value)
  ? value.filter((item) => typeof item === "string" && item.trim()) : [];

export function normalizeScore(value) {
  return typeof value === "number" && Number.isFinite(value)
    ? Math.min(100, Math.max(0, value)) : null;
}

export function animatedScoreAt(target, progress) {
  const score = normalizeScore(target);
  if (score === null) return 0;
  const fraction = Math.min(1, Math.max(0, progress));
  return score * (1 - (1 - fraction) ** 3);
}

export function safeSourceUrl(value) {
  if (typeof value !== "string") return null;
  try {
    const url = new URL(value);
    return ["http:", "https:"].includes(url.protocol) && !url.username && !url.password
      ? url.href : null;
  } catch {
    return null;
  }
}

export function buildReportEvidence(result = {}, query = "") {
  const media = ["image", "audio", "video"].includes(result.content_type);
  const inconclusive = result.analysis_status === "inconclusive";
  const scam = result.scam_analysis || {};
  const patterns = Array.isArray(scam.detected_patterns)
    ? scam.detected_patterns.filter((item) => item && typeof item === "object") : [];
  const findings = patterns.filter((item) => item && typeof item === "object").map((item, index) => ({
    id: `pattern-${index}`,
    title: typeof item.category === "string" ? item.category : "Padrão de risco",
    detail: typeof item.description === "string" ? item.description : "Um padrão de risco foi identificado no conteúdo.",
    quote: typeof item.matched_excerpt === "string" ? item.matched_excerpt : "",
    origin: "Regra de triagem do texto · indício, não comprovação",
  }));
  if (scam.suspicious_url && typeof scam.suspicious_url_reason === "string") {
    findings.push({
      id: "url", title: "Sinal no endereço do link", detail: scam.suspicious_url_reason,
      origin: "Triagem do endereço · um domínio suspeito não prova falsidade",
    });
  }
  const seen = new Set(findings.map((item) => item.detail));
  for (const [index, flag] of strings(result.red_flags).entries()) {
    if (seen.has(flag) || patterns.some((item) => item.description && flag.includes(item.description))) continue;
    findings.push({id: `flag-${index}`, title: "Alerta registrado na análise", detail: flag, origin: "Análise automática · requer confirmação"});
    seen.add(flag);
  }
  const coverage = {...(result.provider_coverage && typeof result.provider_coverage === "object"
    ? result.provider_coverage : {})};
  if (result.content_type === "video" && result.audio_analysis?.provider_coverage) {
    for (const [name, layer] of Object.entries(result.audio_analysis.provider_coverage)) {
      coverage[`áudio/${name}`] = layer;
    }
  }
  const missing = [];
  const content = result.content_analysis && typeof result.content_analysis === "object" ? result.content_analysis : result;
  const claimAssessments = Array.isArray(content.claim_assessments) ? content.claim_assessments.filter((item) =>
    item && typeof item.claim === "string" && typeof item.status === "string") : [];
  const claimLabels = {supported: "Corroborada nas checagens", refuted: "Refutada nas checagens", conflicting: "Fontes em desacordo", unverified: "Não verificada"};
  for (const [index, item] of claimAssessments.entries()) {
    const accepted = Array.isArray(item.evidence) ? item.evidence : [];
    findings.push({id: `claim-${index}`, title: claimLabels[item.status] || "Revisão necessária",
      quote: item.claim, detail: typeof item.explanation === "string" ? item.explanation : "Confira as checagens correspondentes.",
      origin: `${accepted.length} avaliações correspondentes · comparação conservadora da afirmação`});
  }
  for (const [index, indicator] of strings(result.content_risk?.indicators).entries()) {
    findings.push({
      id: `speech-${index}`, title: "Sinal no conteúdo da fala",
      detail: indicator, origin: "Triagem da transcrição · não detecta clonagem de voz",
    });
  }
  if (result.content_type === "audio" && !result.transcription) {
    missing.push("A transcrição do áudio não ficou disponível; a fala não pôde ser conferida.");
  }
  for (const [provider, layer] of Object.entries(coverage)) {
    if (!layer || typeof layer !== "object") continue;
    const available = ["success", "partial"].includes(layer.status);
    if (!available) {
      missing.push(`${provider}: não retornou evidência utilizável nesta análise.`);
      continue;
    }
    if (layer.status === "partial") missing.push(`${provider}: apenas parte das observações foi obtida; confira a cobertura.`);
    const scores = [
      ["geração por IA", layer.ai_score],
      ["manipulação facial", layer.deepfake_score],
    ].filter(([, score]) => typeof score === "number" && Number.isFinite(score) && score >= 0 && score <= 1);
    for (const [kind, score] of scores) {
      findings.push({
        id: `${provider}-${kind}`, title: `Sinal de ${kind} · ${provider}`,
        detail: `O detector retornou ${(score * 100).toFixed(1)}%. É a pontuação do serviço, não uma probabilidade calibrada de falsidade. Compressão, edição e o tipo de conteúdo podem afetar esse sinal.`,
        origin: layer.status === "partial" ? "Cobertura parcial do detector" : "Resposta do detector",
      });
    }
  }
  const audioForensics = result.content_type === "video" ? result.audio_analysis?.forensics : result.forensics;
  const segments = Array.isArray(audioForensics?.hive?.segments) ? audioForensics.hive.segments : [];
  for (const [index, segment] of segments.slice(0, 50).entries()) {
    if (!segment || ![segment.start_seconds, segment.end_seconds, segment.ai_generated_score].every((n) => typeof n === "number" && Number.isFinite(n))
        || segment.start_seconds < 0 || segment.end_seconds < segment.start_seconds || segment.end_seconds > 120
        || segment.ai_generated_score < 0 || segment.ai_generated_score > 1) continue;
    findings.push({id: `audio-segment-${index}`, title: `Áudio: ${segment.start_seconds.toFixed(1)}–${segment.end_seconds.toFixed(1)} s`,
      detail: `Hive retornou ${(segment.ai_generated_score * 100).toFixed(1)}% neste trecho. É um sinal do detector, não uma certificação do trecho ou de toda a gravação.`,
      origin: "Observação temporal do detector · não verifica identidade ou veracidade da fala"});
  }
  // Only use references returned by retrieval, never citations invented by an LLM.
  const factChecks = [...(Array.isArray(result.fact_checks) ? result.fact_checks : []),
    ...(content !== result && Array.isArray(content.fact_checks) ? content.fact_checks : [])];
  const news = Array.isArray(result.serper_news) ? result.serper_news : [];
  const sources = [
    ...factChecks.filter((item) => item && typeof item === "object").map((item, index) => ({
      id: `fact-${index}`, kind: "Checagem encontrada",
      title: typeof item.claim_text === "string" ? item.claim_text : "Afirmação consultada",
      publisher: typeof item.publisher === "string" ? item.publisher : "Fonte de checagem",
      rating: typeof item.rating === "string" ? item.rating : "",
      date: typeof item.review_date === "string" ? item.review_date : "",
      url: safeSourceUrl(item.url),
    })),
    ...news.filter((item) => item && typeof item === "object").map((item, index) => ({
      id: `news-${index}`, kind: "Notícia encontrada · não é confirmação automática",
      title: typeof item.title === "string" ? item.title : "Notícia relacionada",
      publisher: typeof item.source === "string" ? item.source : "Fonte consultada",
      date: typeof item.date === "string" ? item.date : "",
      url: safeSourceUrl(item.link),
    })),
  ];
  const guidance = patterns.flatMap((pattern) => {
    if (!Array.isArray(pattern?.guidance)) return [];
    return pattern.guidance.filter((item) => item && typeof item.title === "string" && safeSourceUrl(item.url))
      .map((item) => ({title: item.title, url: safeSourceUrl(item.url)}));
  });
  const input = result.query_input || query;
  const checkedContent = !media && typeof input === "string" ? input : "";
  const video = result.forensics?.video;
  const sampledFrames = typeof video?.sampled_frames === "number" ? video.sampled_frames : null;
  const timestamps = Array.isArray(video?.timestamps_seconds)
    ? video.timestamps_seconds.filter((value) => typeof value === "number" && Number.isFinite(value)) : [];
  return {
    media, inconclusive, findings, sources, guidance, missing, checkedContent, claimAssessments,
    veracityStatus: typeof content.veracity_status === "string" ? content.veracity_status : "unverified",
    contentSummary: typeof content.summary === "string" ? content.summary : "",
    contentOrigin: content.origin || "text",
    claims: strings(content.claims), positives: strings(result.positive_signals || result.positives),
    limitations: strings(result.limitations), sampledFrames, timestamps,
    transcription: typeof result.transcription === "string" ? result.transcription : "",
    interpretation: inconclusive
      ? "Não foi possível determinar a origem ou confirmar a informação com as evidências disponíveis. Ausência de resposta não é prova de conteúdo falso."
      : result.verdict === "Scam"
        ? "A mensagem apresenta sinais associados a golpes. Eles justificam cautela, mas não comprovam quem enviou a mensagem nem tornam toda afirmação dela falsa."
        : ["AI_Generated", "Manipulated"].includes(result.verdict)
          ? "Há sinais sobre a produção ou edição da mídia. Isso não demonstra, por si só, que a informação retratada seja falsa."
          : result.verdict === "False"
            ? "As checagens correspondentes refutam a afirmação. A conclusão é atribuída às fontes consultadas: abra seus argumentos e confira a data e o contexto."
          : result.verdict === "Authentic"
            ? "A análise aponta apoio à informação. Confira se as fontes tratam da mesma afirmação, data e contexto; o indicador não é garantia de veracidade."
            : "Os sinais precisam ser confrontados com o original e fontes independentes. O relatório não substitui uma checagem humana.",
  };
}
