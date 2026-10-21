const strings = (value) => Array.isArray(value)
  ? value.filter((item) => typeof item === "string" && item.trim()) : [];

export function batchResultLabel(result = {}) {
  if (result.verdict === "Scam") return "Sinais de possível golpe";
  if (result.analysis_status === "inconclusive") return "Análise inconclusiva";
  if (result.veracity_status === "supported") return "Verificada como verdadeira nas fontes consultadas";
  if (result.veracity_status === "refuted") return "Verificada como falsa nas fontes consultadas";
  if (result.veracity_status === "conflicting") return "Fontes em desacordo";
  if (result.veracity_status === "mixed") return "Resultados diferentes por afirmação";
  return "Sem conclusão suficiente";
}

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

// The opt-in explanation cannot override a badge or introduce model citations.
// Rebuild its public prose from the canonical assessments, not arbitrary text.
export function groundedReportExplanation(result = {}) {
  const record = result.report_explanation;
  if (!["text", "url"].includes(result.content_type)
      || record?.version !== "grounded_text_explanation_v1"
      || record.decision_role !== "explanation_only" || record.new_provider_calls !== 0
      || !Array.isArray(record.claims) || record.claims.length > 5
      || !Array.isArray(result.claim_assessments)) return null;
  const labels = {supported: "verificado como verdadeiro nas fontes consultadas", refuted: "verificado como falso nas fontes consultadas",
    conflicting: "evidências em desacordo; exige conferência humana", unverified: "sem evidência correspondente suficiente para concluir"};
  const paragraphs = [];
  for (const entry of record.claims) {
    if (!entry || typeof entry.claim !== "string" || !entry.claim.trim() || entry.claim.length > 5000
        || !Object.hasOwn(labels, entry.status)) return null;
    const canonical = result.claim_assessments.find((item) => item?.claim === entry.claim && item.status === entry.status);
    if (!canonical) return null;
    paragraphs.push(`Trecho enviado: “${entry.claim}”\nResultado para este trecho: ${labels[entry.status]}.`);
    for (const reference of (Array.isArray(entry.references) ? entry.references : []).slice(0, 2)) {
      const url = safeSourceUrl(reference?.url);
      if (!url?.startsWith("https://")) continue;
      const accepted = (Array.isArray(canonical.evidence) ? canonical.evidence : []).find((source) =>
        safeSourceUrl(source?.url) === url && !source.exclusion_reason && source.source_role !== "submitted_source"
        && ["supports", "supported", "refutes", "refuted"].includes(source.relation));
      if (!accepted) continue;
      const quote = canonical.evidence_mode === "retrieved_sources" && typeof reference.excerpt === "string"
        && reference.excerpt.trim() && reference.excerpt.length <= 600 && reference.excerpt === accepted.excerpt
        ? `Trecho citado pela análise: “${reference.excerpt}”\n` : "";
      paragraphs.push(`${quote}Fonte consultada: ${url}`);
    }
  }
  return paragraphs.length ? {text: paragraphs.join("\n\n")} : null;
}

const mediaSignalStates = ["consensus_ai", "consensus_manipulation", "isolated_ai", "isolated_manipulation",
  "disagreement", "no_high_signal", "unavailable"];
const highMediaSignal = (state) => ["consensus_ai", "consensus_manipulation", "isolated_ai", "isolated_manipulation"].includes(state);

// The additive diagnosis summarizes observations. It never changes the saved
// verdict, decision index or provider records, and never exposes raw scores.
export function mediaSignalPresentation(signal, scope) {
  if (!signal || signal.version !== "1" || !["image", "audio", "sampled_video_frames"].includes(scope)
      || signal.scope !== scope || !mediaSignalStates.includes(signal.state)) return null;
  const voice = scope === "audio";
  const video = scope === "sampled_video_frames";
  const labels = {
    consensus_ai: voice ? "Indícios de possível voz sintética" : video ? "Indícios de IA em quadros amostrados" : "Indícios de geração por IA",
    consensus_manipulation: voice ? "Indícios de possível alteração do áudio" : video ? "Indícios de manipulação em quadros amostrados" : "Indícios de possível manipulação",
    isolated_ai: voice ? "Sinal de possível voz sintética" : "Sinal de possível IA — confirmação pendente",
    isolated_manipulation: voice ? "Sinal de possível alteração do áudio — confirmação pendente" : "Sinal de possível manipulação — confirmação pendente",
    disagreement: "Detectores em desacordo",
    no_high_signal: "Sem indícios fortes nas consultas feitas",
    unavailable: "Análise da origem indisponível",
  };
  const explanations = {
    consensus_ai: "Consultas de detectores independentes registraram indícios de geração por IA.",
    consensus_manipulation: "Consultas de detectores independentes registraram indícios de possível manipulação.",
    isolated_ai: "Um detector registrou um sinal forte, sem confirmação independente suficiente. A confirmação continua pendente; este sinal não conclui que o arquivo foi gerado por IA.",
    isolated_manipulation: "Um detector registrou um sinal forte de possível alteração, sem confirmação independente suficiente. A confirmação continua pendente; este sinal não conclui que o arquivo foi manipulado.",
    disagreement: "As consultas retornaram sinais incompatíveis. É necessária uma conferência humana; não há uma conclusão segura sobre a origem.",
    no_high_signal: "Nas consultas que retornaram resultados utilizáveis, não apareceram sinais fortes. Isso não prova autenticidade: alterações podem passar despercebidas, e nem todas as dimensões podem ter sido analisadas.",
    unavailable: "Nenhuma consulta sobre a origem retornou observação utilizável nesta análise. A leitura de texto e a checagem da informação, quando disponíveis, continuam úteis e são avaliadas separadamente.",
  };
  let explanation = explanations[signal.state];
  if (voice) explanation += " A observação trata da faixa de áudio: não comprova clonagem, identidade da pessoa nem a verdade da fala; não determina que toda a gravação seja sintética.";
  else if (video) {
    explanation += " A observação se limita aos quadros amostrados; não verifica o vídeo inteiro, a identidade da pessoa ou a sincronização entre boca e voz.";
    const validTime = (value) => typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= 120;
    const observations = Array.isArray(signal.observations) ? signal.observations.slice(0, 12)
      .filter((item) => item && validTime(item.timestamp_seconds) && mediaSignalStates.includes(item.state)) : [];
    const descriptions = {
      consensus_ai: "Concordância de detectores sobre IA",
      consensus_manipulation: "Concordância de detectores sobre possível manipulação",
      isolated_ai: "Sinal de IA sem confirmação independente",
      isolated_manipulation: "Sinal de alteração sem confirmação independente",
      disagreement: "Detectores em desacordo",
    };
    for (const [state, description] of Object.entries(descriptions)) {
      const times = [...new Set(observations.filter((item) => item.state === state).map((item) => item.timestamp_seconds))];
      if (times.length) explanation += ` ${description} nos tempos ${times.map((time) => `${time.toFixed(1)} s`).join(", ")}.`;
    }
    const times = Array.isArray(signal.observed_timestamps_seconds) ? signal.observed_timestamps_seconds
      .filter((value) => typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= 120).slice(0, 12) : [];
    // Older reports may lack per-frame observations. Never infer agreement at
    // every timestamp merely from the strongest aggregate state.
    if (!observations.length && times.length && !["no_high_signal", "unavailable"].includes(signal.state)) explanation += ` Sinais observados nos tempos ${times.map((time) => `${time.toFixed(1)} s`).join(", ")}; sem detalhamento de concordância por tempo.`;
  }
  else explanation += " A produção da imagem é separada da verdade da informação retratada.";
  return {state: signal.state, title: labels[signal.state], label: labels[signal.state], explanation,
    highSignal: highMediaSignal(signal.state), diagnostic: true};
}

export function sourceAttributionPresentation(result = {}) {
  const content = result.content_analysis && typeof result.content_analysis === "object" ? result.content_analysis : result;
  const record = content.source_attribution;
  if (!record || record.decision_role !== "source_attribution_only"
      || !["found", "no_results", "error", "not_configured"].includes(record.status)) return null;
  const matches = (Array.isArray(record.matches) ? record.matches : []).filter((item) => item
    && item.match_method === "literal_sentence" && ["submitted_source", "retrieved_reference"].includes(item.source_role)
    && safeSourceUrl(item.url) && typeof item.excerpt === "string" && item.excerpt.trim()
    && typeof item.claim === "string" && item.claim.trim()).slice(0, 20).map((item, index) => ({
      id: `attribution-${index}`, url: safeSourceUrl(item.url), title: typeof item.title === "string" ? item.title : "Publicação localizada",
      excerpt: item.excerpt, claim: item.claim, sourceRole: item.source_role,
    }));
  const status = record.status === "found" && !matches.length ? "error" : record.status;
  const coverage = record.coverage && typeof record.coverage === "object" ? record.coverage : {};
  const title = status === "found" ? "Trecho localizado em uma fonte"
    : status === "no_results" ? "Sem correspondência nas fontes consultadas" : "Pesquisa de fontes não concluída";
  const explanation = status === "found"
    ? "Uma fonte publica o trecho literal enviado. Isso indica onde o texto aparece; não confirma que a afirmação seja verdadeira, a autoria original ou a autenticidade de uma mídia."
    : status === "no_results"
      ? "A pesquisa não localizou uma publicação com correspondência literal nesta consulta. Isso não prova falsidade nem ausência de uma fonte original; a busca tem alcance limitado."
      : status === "not_configured"
        ? "A pesquisa de publicações não está habilitada nesta análise. Não foi possível verificar onde o trecho aparece; isso não determina verdade ou falsidade."
        : "A pesquisa de publicações não foi concluída. Não foi possível verificar onde o trecho aparece; isso não determina verdade ou falsidade.";
  const limitations = strings(record.limitations).filter((item) => !isTechnicalReportText(item)).slice(0, 8);
  if (coverage.search_status === "not_configured") limitations.push("A busca de referências não está habilitada nesta análise.");
  if (coverage.search_status === "rate_limited") limitations.push("O limite de consultas disponível foi atingido; a busca de referências ficou limitada.");
  const count = (field) => Number.isInteger(coverage[field]) && coverage[field] >= 0 ? coverage[field] : null;
  const selectedClaims = count("selected_claim_count"), selectedPages = count("selected_url_count"), fetchedPages = count("fetched_count");
  const scope = selectedClaims !== null && selectedPages !== null && fetchedPages !== null
    ? `Alcance desta pesquisa: ${selectedClaims} frases selecionadas, ${selectedPages} páginas selecionadas e ${fetchedPages} páginas com leitura concluída.` : "";
  return {status, title, explanation, matches: status === "found" ? matches : [], scope, limitations: [...new Set(limitations)]};
}

const corroborationLabels = {
  corroborated: "Verificada como verdadeira nas fontes consultadas", refuted: "Verificada como falsa nas fontes consultadas",
  conflicting: "Fontes discordam", mixed: "Conteúdo misto", insufficient: "Evidência insuficiente",
};

// Source documents are not ClaimReview ratings. Only the versioned, grounded
// record is displayed here; arbitrary LLM citations and confidence stay unused.
export function sourceCorroborationPresentation(result = {}) {
  const content = result.content_analysis && typeof result.content_analysis === "object" ? result.content_analysis : result;
  const record = content.source_corroboration;
  if (!record || record.version !== "source_corroboration_v1" || record.decision_role !== "grounded_source_comparison"
      || !Object.hasOwn(corroborationLabels, record.state)) return null;
  const claims = (Array.isArray(record.claims) ? record.claims : []).filter((item) => item
    && typeof item.claim === "string" && item.claim.trim()
    && ["corroborated", "refuted", "conflicting", "insufficient"].includes(item.state))
    .slice(0, 8).map((item, claimIndex) => {
      const evidence = (Array.isArray(item.evidence) ? item.evidence : []).filter((source) => source
        && safeSourceUrl(source.url) && ["supports", "refutes"].includes(source.relation)
        && typeof source.excerpt === "string" && source.excerpt.trim()
        && typeof source.publisher_family === "string" && source.publisher_family.trim())
        .slice(0, 20).map((source, sourceIndex) => ({
          id: `cross-source-${claimIndex}-${sourceIndex}`, url: safeSourceUrl(source.url),
          title: typeof source.title === "string" && source.title.trim() ? source.title : "Documento consultado",
          excerpt: source.excerpt, context: typeof source.context === "string" ? source.context : "", relation: source.relation,
          relationLabel: source.relation === "supports" ? "Concorda com esta afirmação" : "Mostra informação diferente desta afirmação",
          reason: typeof source.reason === "string" && !isTechnicalReportText(source.reason) ? source.reason : "",
          family: source.publisher_family, sourceRole: source.source_role,
          retrievedAt: typeof source.retrieved_at === "string" && Number.isFinite(Date.parse(source.retrieved_at))
            ? source.retrieved_at : "",
        }));
      return {id: `cross-claim-${claimIndex}`, claim: item.claim, state: item.state, title: corroborationLabels[item.state],
        explanation: typeof item.explanation === "string" && !isTechnicalReportText(item.explanation)
          ? item.explanation : "Compare os trechos, a data e o contexto das fontes consultadas.", evidence};
    });
  const coverage = record.coverage && typeof record.coverage === "object" ? record.coverage : {};
  const count = (field) => Number.isInteger(coverage[field]) && coverage[field] >= 0 ? coverage[field] : null;
  const selectedClaims = count("selected_claim_count"), totalClaims = count("literal_claim_count");
  const selectedSources = count("selected_source_count");
  const scope = selectedClaims !== null && totalClaims !== null && selectedSources !== null
    ? `Alcance do cruzamento: ${selectedClaims} de ${totalClaims} afirmações selecionadas e ${selectedSources} documentos selecionados para consulta.` : "";
  const explanations = {
    corroborated: "A informação foi verificada como verdadeira nos trechos de fontes independentes consultadas. Confira datas e contexto: a análise pode errar e não comprova a origem de uma imagem, áudio ou vídeo.",
    refuted: "A informação foi verificada como falsa nos trechos de fontes independentes consultadas. Veja abaixo o que está diferente, principalmente pessoas, datas, valores e palavras como “não”. A análise pode errar.",
    conflicting: "As fontes recuperadas apresentam informações incompatíveis. Não foi escolhida uma versão como verdadeira; confira as diferenças e a data de cada publicação.",
    mixed: "O conteúdo reúne afirmações com resultados diferentes. Confira cada uma abaixo; nenhum resultado isolado se aplica automaticamente ao texto inteiro.",
    insufficient: "A pesquisa não reuniu informações suficientes para dizer se todo o conteúdo é verdadeiro ou falso. Não encontrar uma fonte ou não conseguir ler uma página não significa que o conteúdo seja falso.",
  };
  const originalRecordOnly = content.original_record_only === true;
  if (originalRecordOnly && ["corroborated", "refuted"].includes(record.state)) {
    explanations[record.state] = "A afirmação sobre o que a instituição publicou foi comparada com o registro original. Foi consultada a publicação da própria instituição, não duas fontes independentes. Isso não comprova que o fenômeno descrito realmente ocorreu.";
  }
  const limitations = strings(record.limitations).filter((item) => !isTechnicalReportText(item)).slice(0, 10);
  if (coverage.complete_claim_coverage === false) limitations.push("O cruzamento não cobre todas as afirmações enviadas. Não é uma aprovação do conteúdo inteiro.");
  if (result.source_extraction?.truncated === true) limitations.push("A página enviada foi lida parcialmente; o restante não foi checado.");
  return {state: record.state, status: record.status, title: corroborationLabels[record.state],
    explanation: explanations[record.state], claims, scope, complete: coverage.complete_claim_coverage === true, originalRecordOnly,
    limitations: [...new Set(limitations)]};
}

export function reportFactualHeadline(result = {}) {
  if (!["text", "url"].includes(result.content_type) || result.verdict === "Scam"
      || !["retrieved_sources", "mixed_evidence"].includes(result.veracity_decision_basis)) return null;
  const cross = sourceCorroborationPresentation(result);
  if (!cross) return null;
  const globalStates = {supported: "corroborated", refuted: "refuted", conflicting: "conflicting", mixed: "mixed"};
  let state = globalStates[result.veracity_status] || "insufficient";
  if (["corroborated", "refuted"].includes(state) && (result.veracity_decision_coverage_complete !== true
      || (result.veracity_decision_basis === "retrieved_sources" && !cross.complete))) state = "insufficient";
  const scopedPage = result.source_extraction?.truncated === true && ["corroborated", "refuted"].includes(state);
  const headline = cross.originalRecordOnly && ["corroborated", "refuted"].includes(state)
    ? cross.explanation : state === "insufficient"
    ? "Há resultados para partes da mensagem, mas faltam informações para dizer se todo o conteúdo é verdadeiro ou falso. Confira as fontes e o que ficou sem confirmação."
    : state === "mixed"
      ? "Há afirmações com resultados diferentes no mesmo conteúdo. Abra os trechos das fontes para entender cada resultado; isso não significa que o texto inteiro seja verdadeiro."
      : state === "conflicting"
        ? "As fontes consultadas discordam sobre a informação. Os trechos e as diferenças estão registrados abaixo; é necessária uma conferência humana."
        : "A conclusão se baseia no cruzamento de documentos recuperados e trechos citados, não apenas em checagens já publicadas. Confira datas e contexto; isso não garante verdade nem autenticidade de mídia.";
  return {title: scopedPage ? state === "corroborated" ? "Trecho verificado como verdadeiro nas fontes consultadas" : "Trecho verificado como falso nas fontes consultadas"
    : cross.originalRecordOnly && ["corroborated", "refuted"].includes(state)
      ? state === "corroborated" ? "Verificada como verdadeira no registro original" : "Verificada como falsa no registro original"
      : corroborationLabels[state], headline: scopedPage ? `A conclusão vale somente para o trecho analisado. O restante da página não foi checado. ${headline}` : headline,
  diagnostic: true, state};
}

export function factCheckQueryPresentation(layer = {}) {
  const plan = layer.query_plan;
  if (!plan || plan.version !== "literal_sentence_queries_v1" || plan.decision_role !== "retrieval_only") return null;
  const count = (field) => Number.isInteger(plan[field]) && plan[field] >= 0 ? plan[field] : null;
  const selected = count("selected_count"), candidates = count("candidate_count"), omitted = count("omitted_count");
  const separate = count("literal_segments_queried"), notSeparate = count("literal_segments_not_queried_separately");
  const details = [];
  if (selected !== null && candidates !== null && selected <= candidates) details.push(`O plano de busca selecionou ${selected} de ${candidates} consultas candidatas${omitted !== null ? `; ${omitted} não foram selecionadas` : ""}.`);
  if (separate !== null && notSeparate !== null) details.push(`${separate} trechos tiveram consultas próprias; ${notSeparate} não tiveram consulta separada.`);
  if (plan.whole_text_queried === true) details.push("O texto integral também entrou no plano de busca; trechos sem consulta própria podem estar incluídos nessa pesquisa.");
  const methodLabels = {extracted_literal_sentence: "trechos literais selecionados na leitura", whole_literal_input: "texto integral", literal_sentence_fallback: "frases literais do conteúdo"};
  const methods = [...new Set(strings(plan.query_methods).filter((method) => Object.hasOwn(methodLabels, method)).map((method) => methodLabels[method]))];
  if (methods.length) details.push(`Tipos de busca: ${methods.join(", ")}.`);
  details.push("Esse plano descreve o alcance da pesquisa, não quantas afirmações foram confirmadas. Ausência de uma checagem publicada não prova verdade nem falsidade.");
  return {detail: details.join(" ")};
}

export function reportSourceHeadline(result = {}) {
  if (!["text", "url"].includes(result.content_type) || result.verdict !== "Suspicious"
      || (result.veracity_status != null && result.veracity_status !== "unverified")) return null;
  const attribution = sourceAttributionPresentation(result);
  if (attribution && attribution.matches.length === 0) return {title: "Análise inconclusiva",
    headline: "As informações encontradas nesta consulta não bastam para dizer se a mensagem é verdadeira ou falsa. Veja abaixo o que foi consultado e o que ficou sem confirmação. Isso não significa que o conteúdo seja falso.",
    diagnostic: true, state: "insufficient"};
  return attribution ? {title: attribution.title,
    headline: `${attribution.explanation} A veracidade da afirmação continua não determinada pelas checagens disponíveis.`, diagnostic: true} : null;
}

export function publicMediaRiskNotice(result = {}) {
  if (!["image", "audio", "video"].includes(result.content_type)) return "";
  const risks = [result.content_risk, result.forensics?.audio?.content_risk,
    result.audio_analysis?.content_risk, result.audio_analysis?.forensics?.audio?.content_risk];
  if (!risks.some((risk) => risk?.is_scam_pattern === true) && result.content_analysis?.verdict !== "Scam") return "";
  return "A leitura disponível contém sinais de pedido financeiro suspeito. Confira a fala ou o texto original e confirme por um canal oficial antes de enviar dinheiro ou dados.";
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

function literalExtractionNotNeeded(layer) {
  return layer?.status === "not_requested" && layer.decision_role === "search_hints_only"
    && layer.reason === "literal_single_sentence_no_extra_extraction";
}

export function providerCoveragePresentation(name, layer = {}, result = {}) {
  if (literalExtractionNotNeeded(layer)) return {label: "Extração dispensada",
    detail: "A frase completa foi usada na pesquisa, sem precisar extrair outros trechos. Isso não confirma se ela é verdadeira ou falsa.", notice: false};
  const labels = {success: "Respondeu", partial: "Cobertura parcial", no_results: "Consulta sem resultados",
    no_text: "Sem texto legível", no_speech: "Sem fala transcritível", not_requested: "Consulta não realizada"};
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
  const failed = layers.some((layer) => !["success", "partial", "no_results", "no_text", "no_speech", "disabled", "not_requested"].includes(layer.status));
  const skipped = layers.some((layer) => layer.status === "not_requested" && !literalExtractionNotNeeded(layer));
  const partial = layers.some((layer) => layer.status === "partial");
  const media = ["image", "audio", "video"].includes(result.content_type);
  const inconclusive = result.analysis_status === "inconclusive";
  const signal = mediaSignalPresentation(result.media_signal, result.content_type === "video" ? "sampled_video_frames" : result.content_type);
  const voiceSignal = result.content_type === "video" && result.media_details?.has_audio !== false
    ? mediaSignalPresentation(result.audio_analysis?.media_signal, "audio") : null;
  const attribution = sourceAttributionPresentation(result);
  const cross = sourceCorroborationPresentation(result);
  const factualHeadline = reportFactualHeadline(result);
  const diagnosisAvailable = Boolean(signal || voiceSignal || attribution || cross);
  const title = diagnosisAvailable ? "O alcance deste resultado" : inconclusive ? "Não foi possível chegar a uma conclusão"
    : failed ? "Algumas etapas não foram concluídas"
    : partial || skipped ? "Análise com alcance limitado" : "Como usar este resultado";
  const detail = factualHeadline ? factualHeadline.headline : cross && !media ? cross.explanation : diagnosisAvailable
    ? media ? "As observações sobre a origem aparecem separadas da leitura e da checagem da informação. Cada resultado vale apenas para as consultas e partes do arquivo descritas; não é uma certificação de autenticidade ou verdade."
      : "A pesquisa de fontes indica onde um trecho aparece. Checagens publicadas avaliam afirmações; encontrar o mesmo texto em uma publicação não confirma sua verdade. Confira as correspondências e o alcance da pesquisa abaixo."
    : inconclusive
    ? media ? "As evidências disponíveis não bastam para confirmar a origem do arquivo ou a informação. Isso não significa que o conteúdo seja falso ou verdadeiro."
      : "As informações encontradas não bastam para dizer se a mensagem é verdadeira ou falsa. Isso não significa que o conteúdo seja falso ou verdadeiro."
    : failed ? "Parte da análise não ficou disponível. Considere apenas as observações descritas neste relatório e confirme a informação por outra fonte."
    : media ? "A análise da produção do arquivo é separada da verdade da mensagem. Indícios de inteligência artificial não comprovam uma informação falsa; ausência de indícios não certifica uma mídia autêntica."
    : "Compare a afirmação, a data e o contexto com as fontes citadas. Notícias relacionadas ou ausência de checagens não comprovam verdade nem falsidade.";
  const limitations = [];
  if (inconclusive) limitations.push(media ? "A origem do arquivo não foi confirmada." : "Não foi possível verificar se a informação é verdadeira ou falsa com as fontes disponíveis.");
  if (failed) limitations.push("Não foi possível concluir todas as etapas desta análise.");
  if (skipped) limitations.push("Algumas consultas não foram realizadas; a cobertura ficou limitada.");
  if (layers.some((layer) => layer.status === "not_configured")) limitations.push("Algumas consultas não estão habilitadas nesta análise; a cobertura ficou limitada.");
  if (layers.some((layer) => ["budget_exhausted", "rate_limited"].includes(layer.status))) limitations.push("O limite de consultas disponível foi atingido; parte da análise não pôde ser feita.");
  if (layers.some((layer) => layer.status === "timeout")) limitations.push("Algumas consultas não terminaram dentro do tempo disponível.");
  if (partial) limitations.push("A análise abrange apenas parte das observações disponíveis, não todo o arquivo.");
  if (result.detector_disagreement === true || result.visual_detector_disagreement === true
      || result.audio_analysis?.detector_disagreement === true) limitations.push("Os sinais obtidos ficaram em desacordo. É necessária uma conferência humana.");
  return {title, detail, limitations, incomplete: inconclusive || failed || partial || skipped};
}

function publicEvidenceFindings(findings, coverage, result) {
  const publicFindings = [];
  const technicalFindings = [];
  const ocrText = typeof result.forensics?.ocr?.text === "string" ? result.forensics.ocr.text.trim() : "";
  const ocrLength = Array.from(ocrText).length;
  for (const finding of findings) {
    if (/^(?:pattern-|claim-|speech-|attribution-)/.test(finding.id) || ["url", "page-extraction"].includes(finding.id)
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
        ? layer.decision_role === "ocr_only" && ocrLength > 0 && ocrLength < 10
          ? "A leitura retornou apenas um trecho curto; confira com a imagem. Não há texto suficiente para checar uma afirmação."
          : "Foi possível obter texto para conferência. Compare a leitura com o arquivo original, principalmente negações, valores e datas. Essa leitura não comprova a origem do arquivo nem a verdade da informação."
        : finding.detail});
      continue;
    }
    technicalFindings.push(finding);
  }
  const signal = mediaSignalPresentation(result.media_signal, result.content_type === "video" ? "sampled_video_frames" : result.content_type);
  const voiceSignal = result.content_type === "video" && result.media_details?.has_audio !== false
    ? mediaSignalPresentation(result.audio_analysis?.media_signal, "audio") : null;
  if (signal || voiceSignal) {
    if (signal) publicFindings.push({id: "media-diagnosis", title: signal.title, detail: signal.explanation,
      origin: result.content_type === "video" ? "Observação dos quadros amostrados · separada do áudio e da informação" : "Observação sobre o arquivo · separada da informação"});
    if (voiceSignal) publicFindings.push({id: "audio-diagnosis", title: `Áudio do vídeo: ${voiceSignal.title}`, detail: voiceSignal.explanation,
      origin: "Observação da faixa de áudio · separada das imagens e da informação"});
  } else if (result.analysis_status === "partial" && ["ai_indications", "manipulation_indications"].includes(result.authenticity_status)) {
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
  const visualSignal = mediaSignalPresentation(result.media_signal, "sampled_video_frames");
  if (visualSignal) Object.assign(visual, {label: visualSignal.label, explanation: visualSignal.explanation, signal: visualSignal});
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
  const audioSignal = hasAudio === false ? null : mediaSignalPresentation(track.media_signal, "audio");
  if (audioSignal) Object.assign(audio, {label: audioSignal.label, explanation: audioSignal.explanation, signal: audioSignal});
  if (audio.detectorDisagreement === true) audio.explanation += " Detectores da voz discordaram; revisão humana necessária.";
  const visualFlag = ["ai_indications", "manipulation_indications"].includes(visual.status);
  const audioFlag = audio.status === "ai_indications";
  const interpretation = visualSignal || audioSignal
    ? `Imagens do vídeo: ${visual.label}. ${visual.explanation} Áudio do vídeo: ${audio.label}. ${audio.explanation}`
    : audioFlag && !visualFlag
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
    const visualSignal = origins.visual.signal;
    const audioSignal = origins.audio.signal;
    if (visualSignal || audioSignal) {
      const rank = {disagreement: 6, consensus_manipulation: 5, consensus_ai: 5, isolated_manipulation: 4,
        isolated_ai: 4, no_high_signal: 1, unavailable: 0};
      const primary = audioSignal && (!visualSignal || rank[audioSignal.state] > rank[visualSignal.state]) ? audioSignal : visualSignal;
      const title = visualSignal?.highSignal && audioSignal?.highSignal
        ? `Imagens: ${visualSignal.title} · Áudio: ${audioSignal.title}`
        : primary === audioSignal ? `Áudio do vídeo: ${primary.title}` : `Imagens do vídeo: ${primary.title}`;
      return {title, headline: origins.interpretation, diagnostic: true};
    }
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
  const signal = mediaSignalPresentation(result.media_signal, result.content_type);
  if (signal) return {title: signal.title, headline: signal.explanation, diagnostic: true};
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
  const sourceAttribution = sourceAttributionPresentation(result);
  const sourceCorroboration = sourceCorroborationPresentation(result);
  if (content !== result && content.provider_coverage && typeof content.provider_coverage === "object") {
    for (const [name, layer] of Object.entries(content.provider_coverage)) coverage[`conteúdo/${name}`] = layer;
  }
  const claimAssessments = Array.isArray(content.claim_assessments) ? content.claim_assessments.filter((item) =>
    item && typeof item.claim === "string" && typeof item.status === "string") : [];
  const claimLabels = {supported: "Verificada como verdadeira nas fontes consultadas", refuted: "Verificada como falsa nas fontes consultadas", conflicting: "Fontes em desacordo", unverified: "Não verificada"};
  for (const [index, item] of claimAssessments.entries()) {
    // Grounded documents have separate cards with actual body excerpts. They
    // must not be presented as editorial ClaimReview ratings.
    if (item.evidence_mode === "retrieved_sources" && sourceCorroboration) continue;
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
    if (literalExtractionNotNeeded(layer)) continue;
    if (transcriptionState.notice && (layer.decision_role === "transcription_only"
        || ["transcription", "áudio/transcription"].includes(provider))) continue;
    if (provider === "google_fact_check" || provider === "conteúdo/google_fact_check") {
      const queries = Array.isArray(layer.queries) ? layer.queries : [];
      const failedQueries = queries.filter((item) => item && !["success", "no_results"].includes(item.status));
      const queryScope = factCheckQueryPresentation(layer);
      if (["success", "no_results"].includes(layer.status)) {
        findings.push({id: `retrieval-${provider}`, title: "Consulta de checagens publicadas",
          detail: (layer.status === "no_results"
            ? "A consulta respondeu, mas não trouxe checagens para esta busca. Isso não significa que a informação seja falsa nem que todas as fontes existentes foram consultadas."
            : "Foram recuperadas checagens publicadas. Apenas as que correspondem à afirmação, ao contexto e à política editorial podem fundamentar uma conclusão.") + (queryScope ? ` ${queryScope.detail}` : ""),
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
        missing.push(`${provider}: auxílio de pesquisa ${layer.status === "no_results" ? "sem resultados" : layer.status === "not_requested" ? "não realizado" : "indisponível"}; isso não determina verdade ou falsidade.`);
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
  const visualSignal = mediaSignalPresentation(result.media_signal, "sampled_video_frames");
  const sampledFramesValue = visualSignal ? result.media_signal.sampled_frames ?? videoForensics?.sampled_frames : videoForensics?.sampled_frames;
  const sampledFrames = Number.isInteger(sampledFramesValue) && sampledFramesValue >= 0 ? sampledFramesValue : null;
  const videoObservations = visualSignal && Array.isArray(result.media_signal.observations) ? result.media_signal.observations
    .filter((item) => item && mediaSignalStates.includes(item.state) && typeof item.timestamp_seconds === "number"
      && Number.isFinite(item.timestamp_seconds) && item.timestamp_seconds >= 0 && item.timestamp_seconds <= 120)
    .slice(0, 12).map((item) => ({timestamp: item.timestamp_seconds,
      label: mediaSignalPresentation({version: "1", scope: "sampled_video_frames", state: item.state}, "sampled_video_frames").label})) : [];
  const timestampValues = Array.isArray(videoForensics?.timestamps_seconds) ? videoForensics.timestamps_seconds
    : videoObservations.map((item) => item.timestamp);
  const timestamps = Array.isArray(timestampValues)
    ? timestampValues.filter((value) => typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= 120) : [];
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
    publicFindings, technicalFindings, publicMissing: publicPresentation.limitations, publicPresentation, sourceAttribution, sourceCorroboration,
    mediaDiagnosis: mediaSignalPresentation(result.media_signal, result.content_type),
    veracityStatus: typeof content.veracity_status === "string" ? content.veracity_status : "unverified",
    veracityLabel: sourceCorroboration && ["retrieved_sources", "mixed_evidence"].includes(content.veracity_decision_basis)
      ? corroborationLabels[({supported: "corroborated", refuted: "refuted", conflicting: "conflicting", mixed: "mixed"})[content.veracity_status] || "insufficient"] : null,
    contentSummary: typeof content.summary === "string" ? content.summary : "",
    contentOrigin: content.origin || "text",
    extractionMethod,
    extractedText: ocrText || speechText || (origin ? contentText : ""),
    extractionProvider: coverage.ocr?.provider || coverage.transcription?.provider || null,
    claims: strings(content.claims), positives: strings(result.positive_signals || result.positives),
    limitations: strings(result.limitations), sampledFrames, timestamps, videoObservations,
    audioTrackPresent: videoOrigins?.hasAudio ?? null,
    visualOrigin: videoOrigins?.visual ?? null,
    audioOrigin: videoOrigins?.audio ?? null,
    transcription: speechText,
    transcriptionState,
    interpretation: video ? videoOrigins.interpretation : mediaSignalPresentation(result.media_signal, result.content_type)?.explanation
      || (!media && result.verdict === "Scam" ? "A mensagem apresenta sinais associados a golpes. Eles justificam cautela, mas não comprovam quem enviou a mensagem nem tornam toda afirmação dela falsa." : null)
      || (result.verdict !== "Scam" && sourceCorroboration ? reportFactualHeadline(result)?.headline || sourceCorroboration.explanation : null)
      || (!media && reportSourceHeadline(result) ? sourceAttribution.explanation : null) || (inconclusive
      ? "Não foi possível determinar a origem ou confirmar a informação com as evidências disponíveis. Ausência de resposta não é prova de conteúdo falso."
      : result.verdict === "Scam"
        ? "A mensagem apresenta sinais associados a golpes. Eles justificam cautela, mas não comprovam quem enviou a mensagem nem tornam toda afirmação dela falsa."
        : ["AI_Generated", "Manipulated"].includes(result.verdict)
          ? "Há sinais sobre a produção ou edição da mídia. Isso não demonstra, por si só, que a informação retratada seja falsa."
          : result.verdict === "False"
            ? "As checagens correspondentes refutam a afirmação. A conclusão é atribuída às fontes consultadas: abra seus argumentos e confira a data e o contexto."
          : result.verdict === "Authentic"
            ? "A análise aponta apoio à informação. Confira se as fontes tratam da mesma afirmação, data e contexto; o indicador não é garantia de veracidade."
            : "Os sinais precisam ser confrontados com o original e fontes independentes. O relatório não substitui uma checagem humana."),
  };
}
