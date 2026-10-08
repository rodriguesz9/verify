const strings = (value) => Array.isArray(value)
  ? value.filter((item) => typeof item === "string" && item.trim()) : [];

export function normalizeScore(value) {
  return typeof value === "number" && Number.isFinite(value)
    ? Math.min(100, Math.max(0, value)) : null;
}

export function visibleDetectorScore(layer, field = "ai_score") {
  if (layer?.voting_eligible === false || layer?.decision_role === "experimental_signal") return null;
  const score = layer?.[field];
  return typeof score === "number" && Number.isFinite(score) && score >= 0 && score <= 1 ? score : null;
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

// Read only known public states. Provider details can contain internal job
// identifiers or upload locations and must never become presentation text.
export function transcriptionPresentation(result = {}) {
  if (result.content_type === "video" && result.media_details?.has_audio === false) {
    return {status: "no_track", pending: false, notice: false, text: "", message: "", detail: "", coverageLabel: "", contentMessage: ""};
  }
  const text = [result.transcription, result.forensics?.audio?.transcription,
    result.audio_analysis?.transcription, result.audio_analysis?.forensics?.audio?.transcription]
    .find((value) => typeof value === "string" && value.trim()) || "";
  const states = [result.transcription_detail?.status, result.forensics?.audio?.transcription_detail?.status,
    result.audio_analysis?.transcription_detail?.status,
    result.audio_analysis?.forensics?.audio?.transcription_detail?.status,
    result.provider_coverage?.transcription?.status,
    result.audio_analysis?.provider_coverage?.transcription?.status,
    result.transcription_status];
  const known = ["pending", "in_progress", "blocked_uncertain", "blocked_expired", "capacity_exceeded", "success", "no_speech", "timeout",
    "error", "not_configured", "disabled", "rate_limited", "unavailable"];
  const status = text ? "success" : states.find((value) => typeof value === "string" && known.includes(value)) || "unavailable";
  const pending = ["pending", "in_progress", "blocked_uncertain"].includes(status);
  const notice = pending || ["blocked_expired", "capacity_exceeded"].includes(status);
  return {status, pending, notice, text,
    message: status === "blocked_expired" ? "A janela de acompanhamento da transcrição terminou"
      : status === "capacity_exceeded" ? "O serviço de transcrição está ocupado"
      : status === "blocked_uncertain" ? "Não foi possível confirmar o processamento da transcrição"
      : pending ? "A transcrição ainda está sendo processada" : "",
    detail: status === "blocked_expired"
      ? "Nenhuma transcrição concluída ficou disponível neste relatório. O estado do pedido remoto não foi confirmado. Não há retomada automática nem garantia de consulta ou conclusão. Evite reenviar o mesmo áudio para não criar solicitações duplicadas; isso não determina a origem da voz nem a veracidade do conteúdo."
      : status === "capacity_exceeded"
        ? "A capacidade de processamento foi atingida. Nenhum novo pedido de transcrição foi criado nesta tentativa. A fala não foi conferida; isso não indica ausência de fala nem determina a origem da voz ou a veracidade do conteúdo."
      : !pending ? "" : status === "blocked_uncertain"
      ? "Não foi possível confirmar o estado do processamento. Evite reenviar o mesmo áudio para não criar solicitações duplicadas. Este relatório não é atualizado automaticamente; isso não determina a origem da voz nem a veracidade do conteúdo."
      : "A fala ainda não está disponível para conferência. Este relatório não é atualizado automaticamente; isso não indica ausência de fala nem determina a origem da voz ou a veracidade do conteúdo.",
    coverageLabel: status === "blocked_expired" ? "janela de acompanhamento encerrada"
      : status === "capacity_exceeded" ? "serviço ocupado; nenhum novo pedido criado"
      : status === "blocked_uncertain" ? "estado da transcrição não confirmado"
      : pending ? "transcrição em processamento" : "",
    contentMessage: status === "blocked_expired" ? "O conteúdo da fala não foi conferido: a janela de acompanhamento da transcrição terminou."
      : status === "capacity_exceeded" ? "O conteúdo da fala não foi conferido: o serviço de transcrição está ocupado."
      : status === "blocked_uncertain" ? "O conteúdo da fala não foi conferido: o estado da transcrição não foi confirmado."
      : pending ? "O conteúdo da fala ainda não pôde ser conferido, pois a transcrição está pendente." : "",
  };
}

export function providerCoveragePresentation(name, layer = {}, result = {}) {
  const labels = {success: "Respondeu", partial: "Cobertura parcial", no_results: "Consulta sem resultados",
    no_text: "Sem texto legível", no_speech: "Sem fala transcritível"};
  const regular = {label: typeof layer?.status === "string" && Object.hasOwn(labels, layer.status) ? labels[layer.status] : "Não disponível",
    detail: typeof layer?.reason === "string" ? layer.reason : "", notice: false};
  if (!["transcription", "áudio/transcription"].includes(name) && layer?.decision_role !== "transcription_only") return regular;
  const reportState = transcriptionPresentation(result);
  if (reportState.status === "no_track") return {label: "Sem faixa de áudio", detail: "Nenhuma fala foi analisada ou transcrita.", notice: false};
  if (reportState.text && ["pending", "in_progress", "blocked_uncertain", "blocked_expired", "capacity_exceeded"].includes(layer?.status)) {
    return {label: "Respondeu", detail: "Transcrição disponível para conferência. A leitura não determina a origem da voz nem a veracidade do conteúdo.", notice: false};
  }
  const state = reportState.notice || reportState.text ? reportState
    : transcriptionPresentation({transcription_detail: {status: layer?.status}});
  if (!state.notice) return regular;
  const transcriptionLabels = {pending: "Em processamento", in_progress: "Em processamento",
    blocked_uncertain: "Estado não confirmado", blocked_expired: "Acompanhamento encerrado",
    capacity_exceeded: "Serviço ocupado"};
  return {label: transcriptionLabels[state.status], detail: state.detail, notice: true};
}

// Operational diagnostics stay available on explicit request, not mixed with
// the evidence a person needs to decide whether to share or act on a message.
export function isTechnicalReportText(value) {
  return typeof value === "string" && /\bHTTP\s*\d{3}\b|\b[A-Z][A-Z0-9_]*_(?:API|SECRET|MEDIA|ENDPOINT|MODEL|KEY|TIMEOUT|ENABLED)[A-Z0-9_]*\b|\b(?:sightengine|hugging\s?face|hive(?:_deepfake)?|gemini_vision|openrouter)\s*:|\b(?:gemini-[\w.-]+|[^\s]+\/[^\s]+:free)\b|não calibrado|\bEXIF\b|detectores experimentais/i.test(value);
}

export function publicCoveragePresentation(result = {}) {
  const coverage = [result.provider_coverage, result.content_analysis?.provider_coverage,
    result.content_type === "video" && result.media_details?.has_audio !== false
      ? result.audio_analysis?.provider_coverage : null];
  const layers = coverage.flatMap((value) => value && typeof value === "object" && !Array.isArray(value)
    ? Object.values(value).filter((layer) => layer && typeof layer === "object" && !Array.isArray(layer)
      && layer.decision_role !== "experimental_signal" && layer.voting_eligible !== false) : []);
  const failed = layers.some((layer) => !["success", "partial", "no_results", "no_text", "no_speech", "disabled"].includes(layer.status));
  const partial = layers.some((layer) => layer.status === "partial");
  const media = ["image", "audio", "video"].includes(result.content_type);
  const inconclusive = result.analysis_status === "inconclusive";
  const title = inconclusive ? "Não foi possível chegar a uma conclusão"
    : failed ? "Algumas etapas não foram concluídas"
    : partial ? "Análise com alcance limitado" : "Como usar este resultado";
  const detail = inconclusive
    ? media ? "As evidências disponíveis não bastam para confirmar a origem do arquivo ou a informação. Isso não significa que o conteúdo seja falso ou verdadeiro."
      : "As evidências disponíveis não bastam para confirmar nem refutar a informação. Isso não significa que o conteúdo seja falso ou verdadeiro."
    : failed ? "Parte da análise não ficou disponível. Considere apenas as observações descritas neste relatório e confirme a informação por outra fonte."
    : media ? "A análise da produção do arquivo é separada da verdade da mensagem. Indícios de inteligência artificial não comprovam uma informação falsa; ausência de indícios não certifica uma mídia autêntica."
    : "Compare a afirmação, a data e o contexto com as fontes citadas. Notícias relacionadas ou ausência de checagens não comprovam verdade nem falsidade.";
  const limitations = [];
  if (inconclusive) limitations.push(media ? "A origem do arquivo não foi confirmada." : "A informação não foi confirmada nem refutada pelas evidências disponíveis.");
  if (failed) limitations.push("Não foi possível concluir todas as etapas desta análise.");
  if (partial) limitations.push("A análise abrange apenas parte das observações disponíveis, não todo o arquivo.");
  if (result.detector_disagreement === true || result.visual_detector_disagreement === true
      || result.audio_analysis?.detector_disagreement === true) limitations.push("Os sinais obtidos ficaram em desacordo. É necessária uma conferência humana.");
  return {title, detail, limitations, incomplete: inconclusive || failed || partial};
}

function publicEvidenceFindings(findings, coverage, result) {
  const publicFindings = [];
  const technicalFindings = [];
  for (const finding of findings) {
    if (/^(?:pattern-|claim-|speech-)/.test(finding.id) || ["url", "page-extraction"].includes(finding.id)
        || finding.id.startsWith("retrieval-")) {
      publicFindings.push(finding);
      continue;
    }
    if (finding.id.startsWith("flag-") && !isTechnicalReportText(finding.detail)) {
      publicFindings.push(finding);
      continue;
    }
    const layer = finding.id.startsWith("helper-") ? coverage[finding.id.slice(7)] : null;
    if (layer && ["ocr_only", "transcription_only"].includes(layer.decision_role)) {
      publicFindings.push({...finding, detail: layer.status === "success"
        ? "Foi possível obter texto para conferência. Compare a leitura com o arquivo original, principalmente negações, valores e datas. Essa leitura não comprova a origem do arquivo nem a verdade da informação."
        : finding.detail});
      continue;
    }
    technicalFindings.push(finding);
  }
  if (result.analysis_status === "partial" && ["ai_indications", "manipulation_indications"].includes(result.authenticity_status)) {
    publicFindings.push({id: "media-production", title: result.authenticity_status === "ai_indications"
      ? "Indícios sobre a produção do arquivo" : "Indícios de possível alteração",
    detail: result.content_type === "video"
      ? "Foram registrados indícios nas partes analisadas. Confira a separação entre imagens e áudio acima: o resultado não se aplica automaticamente ao vídeo inteiro e não comprova que a mensagem seja falsa."
      : result.content_type === "audio"
        ? "Foram registrados indícios de possível fala sintética. Isso não identifica quem falou, não comprova clonagem e não determina a verdade da mensagem."
        : "Foram registrados indícios sobre a produção ou edição da imagem. Isso não comprova intenção de enganar nem determina a verdade da informação retratada.",
    origin: "Observação sobre o arquivo · distinta da checagem da informação"});
  }
  return {publicFindings, technicalFindings};
}

function videoOriginEvidence(result) {
  const hasAudio = typeof result.media_details?.has_audio === "boolean" ? result.media_details.has_audio : null;
  const visualStatus = result.visual_authenticity_status;
  const visualAnalysis = result.visual_analysis_status;
  const visualSeparated = ["ai_indications", "manipulation_indications", "undetermined"].includes(visualStatus)
    && typeof visualAnalysis === "string" && Boolean(visualAnalysis.trim());
  const visualState = !visualSeparated ? "not_separated" : visualAnalysis !== "partial" ? "undetermined" : visualStatus;
  const visualLabels = {
    not_separated: "Origem visual não separada neste relatório",
    undetermined: "Origem das imagens não determinada",
    ai_indications: "Indícios de IA em quadros amostrados",
    manipulation_indications: "Indícios de manipulação em quadros amostrados",
  };
  const visualDisagreement = visualSeparated && typeof result.visual_detector_disagreement === "boolean"
    ? result.visual_detector_disagreement : null;
  const visual = {
    status: visualState,
    label: visualLabels[visualState],
    analysisStatus: visualSeparated ? visualAnalysis : null,
    detectorDisagreement: visualDisagreement,
    explanation: visualState === "not_separated"
      ? "Este relatório não traz uma conclusão separada para as imagens. O resultado geral pode incluir o áudio; não podemos usá-lo para dizer como as imagens foram produzidas."
      : "O resultado visual se refere apenas aos quadros selecionados. Isso não verifica todas as imagens, a identidade da pessoa ou a sincronização entre boca e voz.",
  };
  if (visualDisagreement === true) visual.explanation += " Detectores discordaram em pelo menos um quadro; confira os resultados por tempo.";

  const track = result.audio_analysis && typeof result.audio_analysis === "object" && !Array.isArray(result.audio_analysis)
    ? result.audio_analysis : {};
  const audioHasUsableStatus = ["partial", "inconclusive"].includes(track.analysis_status)
    && ["ai_indications", "undetermined"].includes(track.authenticity_status);
  const audioState = hasAudio === false ? "no_track"
    : audioHasUsableStatus && track.analysis_status !== "inconclusive" ? track.authenticity_status : "undetermined";
  const audio = {
    status: audioState,
    label: audioState === "no_track" ? "Vídeo sem faixa de áudio"
      : audioState === "ai_indications" ? "Indícios de possível fala sintética no áudio" : "Origem da voz não determinada",
    analysisStatus: hasAudio !== false && audioHasUsableStatus ? track.analysis_status : null,
    detectorDisagreement: hasAudio !== false && typeof track.detector_disagreement === "boolean"
      ? track.detector_disagreement : null,
    explanation: audioState === "no_track"
      ? "Não existe faixa de áudio neste arquivo. Nenhuma voz foi analisada ou transcrita."
      : audioState === "ai_indications"
        ? "Os indícios são da faixa de áudio, não das imagens. Não comprovam clonagem, identidade da pessoa nem que toda a gravação seja sintética."
        : hasAudio === true
          ? "Existe uma faixa de áudio, mas a origem da voz ficou indeterminada. Transcrição disponível não comprova voz humana nem clonagem."
          : "O relatório não informa a presença de uma faixa de áudio. Não podemos deduzir origem humana ou voz clonada do resultado geral.",
  };
  if (audio.detectorDisagreement === true) audio.explanation += " Detectores da voz discordaram; revisão humana necessária.";
  const visualFlag = ["ai_indications", "manipulation_indications"].includes(visual.status);
  const audioFlag = audio.status === "ai_indications";
  const interpretation = audioFlag && !visualFlag
    ? `Há indícios de possível fala sintética na faixa de áudio. ${visual.status === "not_separated" ? "A origem visual não está separada neste relatório." : "A origem das imagens continua não determinada."} Isso não significa que todo o vídeo foi gerado por IA nem que a informação falada seja falsa.`
    : visualFlag
      ? `Há indícios de ${visual.status === "manipulation_indications" ? "manipulação" : "geração por IA"} em quadros amostrados${audioFlag ? " e indícios de possível fala sintética no áudio" : ""}. Essas observações não verificam o vídeo inteiro nem demonstram que a informação retratada seja falsa.`
      : visual.status === "not_separated"
        ? "Este relatório não separa a conclusão visual do resultado geral. Não podemos atribuir um sinal do áudio às imagens nem confirmar a origem do vídeo inteiro."
        : "A origem das imagens não foi determinada nos quadros amostrados. O áudio é avaliado separadamente; ausência de sinal ou falha de um serviço não comprova autenticidade nem falsidade.";
  return {visual, audio, hasAudio, interpretation};
}

export function reportMediaHeadline(result = {}) {
  if (result.content_type === "video") {
    const origins = videoOriginEvidence(result);
    const visualFlag = ["ai_indications", "manipulation_indications"].includes(origins.visual.status);
    const audioFlag = origins.audio.status === "ai_indications";
    const title = audioFlag && !visualFlag ? "INDÍCIOS DE FALA SINTÉTICA"
      : visualFlag && audioFlag ? origins.visual.status === "manipulation_indications"
        ? "INDÍCIOS VISUAIS E DE FALA SINTÉTICA" : "INDÍCIOS DE IA NAS IMAGENS E NO ÁUDIO"
      : visualFlag ? origins.visual.status === "manipulation_indications"
        ? "INDÍCIOS DE MANIPULAÇÃO EM QUADROS" : "INDÍCIOS DE IA EM QUADROS AMOSTRADOS"
      : "ORIGEM DO VÍDEO NÃO DETERMINADA";
    return {title, headline: origins.interpretation};
  }
  if (result.content_type === "audio") {
    if (result.authenticity_status === "ai_indications" && result.analysis_status === "partial") {
      return {title: "INDÍCIOS DE FALA SINTÉTICA", headline: "Há indícios de possível fala sintética no áudio. Isso não comprova clonagem, identidade da pessoa, origem de toda a gravação ou veracidade da informação falada."};
    }
    if (result.analysis_status === "inconclusive" || ["AI_Generated", "Manipulated"].includes(result.verdict)) {
      return {title: "ORIGEM DA VOZ NÃO DETERMINADA", headline: "Não há uma conclusão utilizável sobre a origem da voz. Transcrição, sinal isolado ou resultado geral não comprovam voz humana, clonagem nem a verdade da informação falada."};
    }
  }
  return null;
}

export function buildReportEvidence(result = {}, query = "") {
  const media = ["image", "audio", "video"].includes(result.content_type);
  const video = result.content_type === "video";
  const videoOrigins = video ? videoOriginEvidence(result) : null;
  const transcriptionState = transcriptionPresentation(result);
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
  if (["static_html", "plain_text"].includes(result.source_extraction?.method)) {
    findings.push({id: "page-extraction", title: "Leitura do conteúdo da página",
      detail: `${result.source_extraction.method === "plain_text" ? "Resposta de texto simples, sem interpretar marcações como HTML." : "Leitura estática do texto principal, sem executar JavaScript nem resolver toda a visibilidade por CSS."} ${result.source_extraction.truncated === true ? "Apenas os primeiros 5.000 caracteres extraídos foram analisados; o restante não foi checado." : "Isso não certifica a legitimidade do site nem a veracidade de todo o seu conteúdo."}`,
      origin: "Extração de texto · não é uma evidência de verdade ou falsidade"});
  }
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
  if (video && videoOrigins.hasAudio !== false && result.audio_analysis?.provider_coverage) {
    for (const [name, layer] of Object.entries(result.audio_analysis.provider_coverage)) {
      coverage[`áudio/${name}`] = layer;
    }
  }
  const missing = [];
  const content = result.content_analysis && typeof result.content_analysis === "object" ? result.content_analysis : result;
  if (content !== result && content.provider_coverage && typeof content.provider_coverage === "object") {
    for (const [name, layer] of Object.entries(content.provider_coverage)) coverage[`conteúdo/${name}`] = layer;
  }
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
  if (result.content_type === "audio" && !transcriptionState.text && !transcriptionState.notice && transcriptionState.status !== "no_speech") {
    missing.push("A transcrição do áudio não ficou disponível; a fala não pôde ser conferida.");
  }
  for (const [provider, layer] of Object.entries(coverage)) {
    if (!layer || typeof layer !== "object") continue;
    if (transcriptionState.notice && (layer.decision_role === "transcription_only"
        || ["transcription", "áudio/transcription"].includes(provider))) continue;
    if (provider === "google_fact_check" || provider === "conteúdo/google_fact_check") {
      const queries = Array.isArray(layer.queries) ? layer.queries : [];
      const failedQueries = queries.filter((item) => item && !["success", "no_results"].includes(item.status));
      if (["success", "no_results"].includes(layer.status)) {
        findings.push({id: `retrieval-${provider}`, title: "Consulta de checagens publicadas",
          detail: layer.status === "no_results"
            ? "A consulta respondeu, mas não trouxe checagens para esta busca. Isso não significa que a informação seja falsa nem que todas as fontes existentes foram consultadas."
            : "Foram recuperadas checagens publicadas. Apenas as que correspondem à afirmação, ao contexto e à política editorial podem fundamentar uma conclusão.",
          origin: `${queries.length} consultas registradas · recuperação, não confirmação automática`});
        if (failedQueries.length) missing.push(`${provider}: ${failedQueries.length} consultas não concluídas; a recuperação foi parcial.`);
      } else {
        missing.push(`Consulta de checagens: ${typeof layer.reason === "string" ? layer.reason : "indisponível nesta análise"} Isso não determina verdade ou falsidade.`);
      }
      continue;
    }
    if (layer.decision_role === "experimental_signal" || layer.voting_eligible === false) {
      if (layer.status === "success") findings.push({id: `experimental-${provider}`, title: `Detector experimental · ${provider}`,
        detail: "Este modelo respondeu, mas sua precisão ainda não foi validada para os conteúdos analisados. O sinal não participa do veredito e não comprova autenticidade nem falsidade.",
        origin: typeof layer.model_used === "string" ? layer.model_used : "Camada experimental · excluída da decisão"});
      else missing.push(`${provider}: detector experimental indisponível; não participa do veredito.`);
      continue;
    }
    if (["ocr_only", "inspection_only", "transcription_only"].includes(layer.decision_role)) {
      const labels = {ocr_only: "Leitura de texto da imagem", inspection_only: "Inspeção visual auxiliar", transcription_only: "Transcrição da fala"};
      if (["no_text", "no_speech"].includes(layer.status)) findings.push({id: `helper-${provider}`, title: labels[layer.decision_role],
        detail: layer.status === "no_text" ? "A camada não encontrou texto legível. Nenhuma palavra foi acrescentada para preencher a ausência de texto."
          : "A camada não obteve fala transcritível. Silêncio ou sinal fraco não comprovam origem humana nem voz clonada.",
        origin: "Sem conteúdo extraído · não é veredito de falsidade"});
      else if (layer.status === "success") findings.push({id: `helper-${provider}`, title: labels[layer.decision_role],
        detail: `Camada concluída${typeof layer.provider === "string" ? ` por ${layer.provider}` : ""}. Não certifica identidade, origem da mídia ou veracidade da informação.`,
        origin: "Auxílio à leitura · não é detector de autenticidade"});
      else missing.push(`${labels[layer.decision_role]}: ${layer.status === "not_configured" ? "serviço não configurado" : layer.status === "disabled" ? "serviço desativado" : "indisponível"}${typeof layer.reason === "string" ? ` (${layer.reason})` : ""}.`);
      continue;
    }
    if (["search_hints_only", "context_only"].includes(layer.decision_role)) {
      if (layer.status === "success") {
        findings.push({id: `helper-${provider}`, title: `Auxílio de pesquisa · ${provider}`,
          detail: layer.decision_role === "search_hints_only"
            ? `A IA ajudou a selecionar trechos para busca${typeof layer.model_used === "string" ? ` (${layer.model_used})` : ""}. Não decidiu o veredito nem forneceu prova de verdade ou falsidade.`
            : "Foram recuperadas notícias relacionadas. Notícias relacionadas não confirmam automaticamente a afirmação.",
          origin: "Camada auxiliar · não participa da decisão de veracidade"});
      } else {
        missing.push(`${provider}: auxílio de pesquisa ${layer.status === "no_results" ? "sem resultados" : "indisponível"}; isso não determina verdade ou falsidade.`);
      }
      continue;
    }
    const available = ["success", "partial"].includes(layer.status);
    if (!available) {
      missing.push(`${provider}: não retornou evidência utilizável nesta análise${typeof layer.reason === "string" && layer.reason.trim() ? ` (${layer.reason})` : ""}.`);
      continue;
    }
    if (layer.status === "partial") {
      const validCounts = Number.isInteger(layer.analyzed_frames) && Number.isInteger(layer.sampled_frames)
        && layer.sampled_frames > 0 && layer.analyzed_frames >= 0 && layer.analyzed_frames <= layer.sampled_frames;
      const reasons = strings(layer.failure_reasons).slice(0, 3);
      missing.push(`${provider}: apenas parte das observações foi obtida${validCounts ? ` (${layer.analyzed_frames} de ${layer.sampled_frames} quadros amostrados)` : ""}; confira a cobertura.${reasons.length ? ` Motivos: ${reasons.join(" ")}` : ""}`);
    }
    const voiceLayer = result.content_type === "audio" || (video && provider.startsWith("áudio/"));
    const scores = [
      [voiceLayer ? "geração de fala por IA" : "geração por IA", layer.ai_score],
      ["manipulação facial", voiceLayer ? null : layer.deepfake_score],
    ].filter(([, score]) => typeof score === "number" && Number.isFinite(score) && score >= 0 && score <= 1);
    for (const [kind, score] of scores) {
      findings.push({
        id: `${provider}-${kind}`, title: `Sinal de ${kind} · ${provider}`,
        detail: `O detector retornou ${(score * 100).toFixed(1)}%. É a pontuação do serviço, não uma probabilidade calibrada de falsidade. Compressão, edição e o tipo de conteúdo podem afetar esse sinal.${voiceLayer ? " O sinal é sobre a fala/áudio, não sobre imagens, identidade ou toda a gravação." : video ? " O sinal descreve quadros amostrados, não todas as imagens do vídeo." : ""}`,
        origin: layer.status === "partial" ? "Cobertura parcial do detector" : "Resposta do detector",
      });
    }
  }
  const audioForensics = video ? videoOrigins.hasAudio === false ? null : result.audio_analysis?.forensics : result.forensics;
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
  const acceptedUrls = new Set(claimAssessments.flatMap((claim) => Array.isArray(claim.evidence)
    ? claim.evidence.map((source) => safeSourceUrl(source?.url)).filter(Boolean) : []));
  const excludedReasons = new Map();
  for (const claim of claimAssessments) {
    for (const source of Array.isArray(claim.excluded_evidence) ? claim.excluded_evidence : []) {
      const url = safeSourceUrl(source?.url);
      if (url && typeof source?.exclusion_reason === "string") excludedReasons.set(url, source.exclusion_reason);
    }
  }
  const sources = [
    ...factChecks.filter((item) => item && typeof item === "object").map((item, index) => ({
      id: `fact-${index}`, kind: claimAssessments.length
        ? acceptedUrls.has(safeSourceUrl(item.url)) ? "Checagem correspondente à afirmação" : "Resultado da busca · não usado na decisão"
        : "Checagem encontrada · confira a correspondência",
      note: claimAssessments.length && !acceptedUrls.has(safeSourceUrl(item.url))
        ? excludedReasons.get(safeSourceUrl(item.url)) || "Não há correspondência validada com uma afirmação enviada. Não fundamenta este veredito." : "",
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
  const videoForensics = result.forensics?.video;
  const sampledFrames = typeof videoForensics?.sampled_frames === "number" ? videoForensics.sampled_frames : null;
  const timestamps = Array.isArray(videoForensics?.timestamps_seconds)
    ? videoForensics.timestamps_seconds.filter((value) => typeof value === "number" && Number.isFinite(value)) : [];
  const ocrText = typeof result.forensics?.ocr?.text === "string" ? result.forensics.ocr.text.trim() : "";
  const speechText = transcriptionState.text;
  const origin = ["ocr", "transcription"].includes(content.origin) ? content.origin : null;
  const contentText = typeof content.query_input === "string" ? content.query_input.trim() : "";
  const extractionMethod = ocrText ? "OCR" : speechText ? "transcrição"
    : contentText && origin ? origin === "ocr" ? "OCR" : "transcrição" : null;
  const publicPresentation = publicCoveragePresentation(result);
  const {publicFindings, technicalFindings} = publicEvidenceFindings(findings, coverage, result);
  return {
    media, video, inconclusive, findings, sources, guidance, missing, checkedContent, claimAssessments,
    publicFindings, technicalFindings, publicMissing: publicPresentation.limitations, publicPresentation,
    veracityStatus: typeof content.veracity_status === "string" ? content.veracity_status : "unverified",
    contentSummary: typeof content.summary === "string" ? content.summary : "",
    contentOrigin: content.origin || "text",
    extractionMethod,
    extractedText: ocrText || speechText || (origin ? contentText : ""),
    extractionProvider: coverage.ocr?.provider || coverage.transcription?.provider || null,
    claims: strings(content.claims), positives: strings(result.positive_signals || result.positives),
    limitations: strings(result.limitations), sampledFrames, timestamps,
    audioTrackPresent: videoOrigins?.hasAudio ?? null,
    visualOrigin: videoOrigins?.visual ?? null,
    audioOrigin: videoOrigins?.audio ?? null,
    transcription: speechText,
    transcriptionState,
    interpretation: video ? videoOrigins.interpretation : inconclusive
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
