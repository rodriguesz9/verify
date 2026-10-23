import asyncio
from app.core.gemini_client import gemini_timeout_seconds
from datetime import datetime, timezone
import re
import os
from app.core.gemini_analyzer import extract_claims_with_ai, generate_final_report
from app.core.fact_checker import query_fact_check_api
from app.core.domain_checker import check_domain_reputation
from app.core.gptzero_client import detect_ai_text
from app.core.serper_client import search_news, search_web, NewsSearch, MAX_NEWS_QUERY_CHARS
from app.core.scam_detector import analyze_scam_indicators
from app.core.openrouter_service import analyze_with_openrouter
from app.services.claim_policy import text_report, input_claims
from app.services.news_relevance import filter_context_news
from app.services.factual_queries import build_fact_check_queries
from app.services.source_attribution import collect_source_attribution, primary_reference_leads, collect_official_copom_record
from app.services.source_corroboration import corroborate_sources
from app.services.source_corroboration import select_comparison_documents, usable_source_families
from app.services.source_corroboration import document_selection_audit
from app.services.source_corroboration import claims_needing_research
from app.services.source_decision import apply_source_decision
from app.services.report_explanation import enrich_grounded_report
from app.services.source_queries import neutral_source_query, primary_source_query, primary_source_filter, editorial_source_query
from app.services.source_research import plan_source_research, research_enabled

SOURCE_SITE_FILTER = "(site:royal.uk OR site:brasilescola.uol.com.br OR site:mundoeducacao.uol.com.br OR site:nasa.gov OR site:cnnbrasil.com.br OR site:aosfatos.org OR site:bbc.com OR site:theguardian.com OR site:time.com OR site:axios.com)"
PRIMARY_SITE_FILTER = "(site:royal.uk OR site:nasa.gov OR site:ibge.gov.br OR site:bcb.gov.br OR site:who.int OR site:planalto.gov.br OR site:copernicus.eu)"
EDITORIAL_SITE_FILTER = "(site:bbc.com OR site:reuters.com OR site:apnews.com OR site:ebc.com.br OR site:cnnbrasil.com.br OR site:theguardian.com OR site:g1.globo.com OR site:brasilescola.uol.com.br OR site:aosfatos.org)"
EXPLAINER_SITE_FILTER = "(site:brasilescola.uol.com.br OR site:mundoeducacao.uol.com.br OR site:cnnbrasil.com.br OR site:g1.globo.com OR site:aosfatos.org)"
PIPELINE_BUDGET_SECONDS = 330
INITIAL_QUERY_BUDGET_SECONDS = 110


def _task_failed(task):
    return task.cancelled() or task.exception() is not None


async def _await_pipeline_tasks(tasks, timeout):
    """Preserve completed work; cancel/join unfinished I/O, never detach it."""
    try:
        if timeout > 0:
            await asyncio.wait(tasks, timeout=timeout)
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


def _source_recovery_query(query):
    """Neutral identity/event leads, NEVER a rewritten assertion or truth vote.

    Literal search comes first. A wrong date can rank coverage of that date
    above an event biography. Only narrow named-event aliases may broaden the
    second query; the untouched original statement still receives every guard.
    Unknown constructions keep the complete literal recovery query.
    """
    identity = re.search(r"\b[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][a-záàâãéêíóôõúç]{2,}\s+(?:[IVXLCDM]{1,6}|[1-9]\d?)\b", query)
    events = [(r"\b(?:morreu|faleceu|falecimento|morte|death|died)\b", "morte OR falecimento OR morreu OR death OR died"),
              (r"\b(?:nasceu|nascimento|birth|born)\b", "nascimento OR nasceu OR birth OR born"),
              (r"\b(?:lançada|lançado|lançou|lançamento|launched|launch)\b", "lançamento OR lançada OR launched OR launch")]
    matched = [aliases for pattern, aliases in events if re.search(pattern, query, re.I)]
    if identity and len(matched) == 1:
        return f'"{identity[0]}" ({matched[0]}) {SOURCE_SITE_FILTER}', "literal_identity_event_anchors"
    return f"{query} {SOURCE_SITE_FILTER}", "whole_literal_claim_curated_sites"


def _source_recovery_queries(query, limit):
    combined, method = _source_recovery_query(query)
    if limit < 3:
        return [(combined, method)]
    if method != "literal_identity_event_anchors":
        # Previously only named birth/death/launch events could use the third
        # configured search. Other subjects got one narrow, predominantly
        # editorial filter, excluding primary bodies already in our curated
        # source policy. Partition the ORIGINAL assertion, not an LLM rewrite.
        # Dates, quantities and negation remain intact; results are still only
        # retrieval leads and must pass the unchanged evidence guards.
        neutral = neutral_source_query(query)
        if neutral:
            primary = primary_source_query(query) or neutral
            editorial, language = editorial_source_query(query)
            return [((primary + " " + primary_source_filter(query)).strip(), "literal_topic_anchors_primary_sources"),
                    (f"{editorial or neutral} {EDITORIAL_SITE_FILTER}",
                     "literal_topic_anchors_bilingual_editorial_sources" if language == "en" else "literal_topic_anchors_editorial_sources")]
        return [((query + " " + primary_source_filter(query)).strip(), "whole_literal_claim_primary_sources"),
                (f"{query} {SOURCE_SITE_FILTER}", method)]
    identity = re.search(r'"[^"\n]+"', combined)[0]
    editorial_filter = EXPLAINER_SITE_FILTER
    editorial_method = "literal_identity_event_editorial_explainers"
    if re.search(r"\b(?:morreu|faleceu|falecimento|morte|death|died)\b", query, re.I):
        primary, editorial, genre = "death OR died", "morte OR falecimento OR morreu", ""
    elif re.search(r"\b(?:nasceu|nascimento|birth|born)\b", query, re.I):
        primary, editorial, genre = "birth OR born", "nascimento OR nasceu", ""
    else:
        primary, editorial, genre = "launched OR launch", "lançamento OR lançada OR launch OR launched", "mission"
        # Launch reporting is not confined to Portuguese school explainers.
        # The old filter excluded independent contemporary reporting already
        # allowed by source policy. Keep the exact named identity, no alleged
        # date or generated answer, and the same bounded search count.
        editorial_filter = EDITORIAL_SITE_FILTER
        editorial_method = "literal_identity_event_editorial_sources"
    return [((f"{identity} ({primary}) {genre} " + primary_source_filter(query)).replace("  ", " ").strip(), "literal_identity_event_primary_sources"),
            (f"{identity} ({editorial}) {editorial_filter}", editorial_method)]


def _verdicts_agree(v1: str, v2: str) -> bool:
    """Check if two verdicts point to the same direction."""
    a = v1.lower().strip() if v1 else ""
    b = v2.lower().strip() if v2 else ""
    positive = {"authentic", "true", "verdadeiro"}
    negative = {"ai_generated", "manipulated", "suspicious", "scam", "fake", "falso", "enganoso"}
    a_pos = a in positive
    a_neg = a in negative
    b_pos = b in positive
    b_neg = b in negative
    if a_pos and b_pos:
        return True
    if a_neg and b_neg:
        return True
    return False


def _merge_verdicts(gemini_result: dict, openrouter_result: dict) -> dict:
    """Merge Gemini and OpenRouter results using consensus."""
    if not openrouter_result or openrouter_result.get("error") or gemini_result.get("analysis_status") == "inconclusive":
        return gemini_result

    g_verdict = gemini_result.get("verdict", "Suspicious").lower()
    o_verdict = openrouter_result.get("verdict", "Suspicious").lower()
    g_score = float(gemini_result.get("score", 50))
    o_score = float(openrouter_result.get("score", 50))
    agree = _verdicts_agree(g_verdict, o_verdict)

    if agree:
        final_score = int(g_score)
        note = "Modelos concordam; concordância não comprova a alegação nem aumenta a precisão medida."
    else:
        final_score = int(g_score)
        note = "Modelos divergentes. Aplicação com Gemini (primário). Revise manualmente."

    merged = dict(gemini_result)
    merged["score"] = final_score
    merged["divergent"] = not agree
    merged["agreement_note"] = note
    merged["model_used"] = f"gemini+openrouter ({gemini_result.get('model_used', 'gemini')}/{openrouter_result.get('model_used', 'openrouter')})" if agree else f"gemini (openrouter divergente)"
    merged["openrouter_summary"] = openrouter_result.get("summary", "")
    merged["openrouter_explanation"] = openrouter_result.get("plain_explanation", "")

    return merged


async def _run_openrouter_check(text: str) -> dict | None:
    """Free auxiliary extraction, not a second opinion on truth."""
    try:
        return await asyncio.wait_for(analyze_with_openrouter(text), timeout=27.0)
    except Exception:
        return {"available": False, "status": "timeout", "claims": [],
                "reason": "Extração auxiliar OpenRouter indisponível.", "decision_role": "search_hints_only", "free_only": True}


async def _run_gemini_check(text: str, context: dict) -> dict:
    """Run Gemini final report."""
    return await generate_final_report(text, context)


def _research_query_text(query, group, original_text=None):
    # An institution must be named in the user's input, not invented by the
    # planner. Unknown topics stay open instead of reading unrelated agencies.
    suffix = primary_source_filter(original_text or query) if group == "primary" else EDITORIAL_SITE_FILTER if group == "editorial" else ""
    return (query + " " + suffix).strip()


def _research_scope_plan(text, planned_queries, previous_queries):
    """Reserve editorial discovery, not an extra vote or an extra request.

    At most two operations. A model's second primary/open search can use the
    editorial filter instead; its neutral words remain untouched. Deterministic
    gaps reuse only the original input. Previously executed exact queries are
    not repeated, even under a different provenance label.
    """
    def key(query):
        return " ".join(query.casefold().split())

    seen = {key(query) for query in previous_queries if isinstance(query, str)}
    operations, duplicates = [], 0
    for item in planned_queries[:2] if isinstance(planned_queries, list) else []:
        if (not isinstance(item, dict) or not isinstance(item.get("query"), str)
                or not 20 <= len(item["query"].strip()) <= 180
                or item.get("source_group") not in {"primary", "editorial", "any"}
                or re.search(r"https?://|www\.|\bsite\s*:|[\x00-\x1f\x7f]", item["query"], re.I)):
            continue
        operations.append({"query": item["query"].strip(), "source_group": item["source_group"],
            "requested_source_group": item["source_group"], "query_origin": "ai_validated_query",
            "scope_change_reason": None})
    if len(operations) == 2 and not any(item["source_group"] == "editorial" for item in operations):
        operations[1].update(source_group="editorial", scope_change_reason="independent_family_gap")

    selected = []
    for operation in operations:
        final = _research_query_text(operation["query"], operation["source_group"], text)
        if len(final) > 500:
            continue
        if key(final) in seen:
            duplicates += 1
            continue
        selected.append(operation)
        seen.add(key(final))

    # No new query is needed when an already valid editorial plan exists.
    # Otherwise use only one still-free slot; this never plans a third search.
    if len(selected) < 2 and not any(item["source_group"] == "editorial" for item in selected):
        neutral = neutral_source_query(text, preserve_period=True)
        if (neutral and 20 <= len(neutral) <= 240
                and not re.search(r"https?://|www\.|\bsite\s*:|[\x00-\x1f\x7f]", neutral, re.I)):
            desired = _research_query_text(neutral, "editorial")
            group, reason = "editorial", "original_neutral_editorial_gap"
            if key(desired) in seen:
                duplicates += 1
                # The same editorial discovery already ran in the base wave.
                # Preserve a novel unfiltered read instead of paying twice for
                # an identical query or adding a cosmetic search modifier.
                group, reason = "any", "duplicate_editorial_query_already_executed"
            final = _research_query_text(neutral, group)
            if len(final) <= 500 and key(final) not in seen:
                selected.append({"query": neutral, "source_group": group,
                    "requested_source_group": None, "query_origin": "deterministic_original_neutral",
                    "scope_change_reason": reason})
            elif key(final) in seen:
                duplicates += 1
    return selected[:2], {"skipped_duplicate_query_count": duplicates,
        "scope_diversified_query_planned_count": sum(item["query_origin"] == "ai_validated_query"
            and item["requested_source_group"] != item["source_group"] for item in selected),
        "deterministic_gap_query_count": sum(item["query_origin"] == "deterministic_original_neutral" for item in selected)}


def _unread_primary_reference_leads(text, documents, source_url, fetched_cache, selected_leads):
    """Two direct links total, only from search-origin bodies; never crawl.

    Cache keys are attempted URLs (including failures); final URLs also exclude
    known redirect aliases. A followed reference cannot become a discovery
    parent, even when a later wave happens to include it among search results.
    """
    remaining = max(0, 2 - len(selected_leads))
    if not remaining:
        return []
    targets = {lead["link"] for lead in selected_leads}
    attempted = set(fetched_cache)
    for requested, result in fetched_cache.items():
        if isinstance(result, dict) and isinstance(result.get("url"), str):
            attempted.add(result["url"])
            if requested in targets:
                targets.add(result["url"])
    origins = [document for document in documents if isinstance(document, dict)
               and document.get("url") not in targets] if isinstance(documents, list) else []
    return primary_reference_leads(text, origins, source_url, excluded_urls=attempted)[:remaining]


async def _retrieve_source_attribution(text: str, queries: list[str], source_url: str | None,
                                      *, use_source_crosscheck: bool = True) -> dict:
    """One base search, optionally one qualified search, and bounded retrieval.

    Source attribution cannot vote on the factual decision. Search snippets
    remain leads; only a complete sentence in a retrieved document can match.
    """
    crosscheck_enabled = use_source_crosscheck and os.getenv("SOURCE_CROSSCHECK_ENABLED", "true").strip().lower() == "true"
    ai_research = crosscheck_enabled and research_enabled()
    deadline = 105 if ai_research else 45 if crosscheck_enabled else 20
    started = asyncio.get_running_loop().time()
    attribution, plan, cited_leads = None, [], []
    fetched_cache, reference_waves = {}, []
    official_record_recovery = {"status": "not_requested", "decision_role": "official_record_retrieval_only"}
    research = {"status": "not_requested", "decision_role": "online_research_planning_only"}

    async def follow_primary_references(stage):
        nonlocal attribution, leads
        if len(fetched_cache) >= 10:
            return False
        fresh = _unread_primary_reference_leads(text, attribution.get("_documents", []), source_url,
                                              fetched_cache, cited_leads)
        if not fresh:
            return False
        cited_leads.extend(fresh)
        reference_waves.append({"stage": stage, "selected_lead_count": len(fresh), "status": "reading"})
        direct_reads = NewsSearch([*fresh, *[{"link": url} for url in fetched_cache]], status="success")
        leads = NewsSearch([*fresh, *leads], status=getattr(leads, "status", "success"))
        attribution = await collect_source_attribution(text, queries, source_url, search_results=direct_reads,
            include_documents=True, max_sources=min(10, len(fetched_cache) + len(fresh)), fetched_cache=fetched_cache)
        reference_waves[-1]["status"] = "completed"
        return True

    try:
        async with asyncio.timeout(deadline):
            query = next((query for query in queries if 20 <= len(query.strip()) <= 500), None)
            previous_queries = [query] if query else []
            leads = (await search_web(query) if query else NewsSearch(
                status="no_results", reason="Nenhuma frase completa cabe no limite da busca; nenhum texto foi cortado."))
            plan = [{"method": "whole_literal_claim", "status": getattr(leads, "status", "success" if leads else "no_results")}] if query else []
            if crosscheck_enabled:
                official_record_recovery = await collect_official_copom_record(text, fetched_cache, max_sources=3)
                # Keep charged official resources inside the ordinary handoff.
                # The index is a locator only; the detail body is independent
                # of whether a search engine also happened to return its URL.
                if fetched_cache:
                    leads = NewsSearch([*leads, *[{"link": url} for url in fetched_cache]],
                                       status=getattr(leads, "status", "success"))
            attribution = await collect_source_attribution(text, queries, source_url, search_results=leads,
                include_documents=crosscheck_enabled, fetched_cache=fetched_cache)
            families = usable_source_families(text, attribution.get("_documents", []), source_url) if crosscheck_enabled else set()
            configured = os.getenv("SOURCE_CROSSCHECK_SEARCH_LIMIT", "3").strip()
            limit = (int(configured) if configured in {"1", "2", "3"} else 3) if crosscheck_enabled else 1
            if (crosscheck_enabled and limit >= 2 and query
                    and len(families) < 2
                    and getattr(leads, "status", "success" if leads else "no_results") in {"success", "no_results"}):
                for qualified, recovery_method in _source_recovery_queries(query, limit):
                    if not 20 <= len(qualified) <= 500:
                        continue
                    # The same existing slot may use a declared English
                    # locale; never add a second request or retry a quota.
                    language = "en" if recovery_method == "literal_topic_anchors_bilingual_editorial_sources" else "pt-br"
                    extra = await search_web(qualified, language="en") if language == "en" else await search_web(qualified)
                    previous_queries.append(qualified)
                    extra_status = getattr(extra, "status", "success" if extra else "no_results")
                    plan.append({"method": recovery_method, "status": extra_status,
                                 "search_language": language,
                                 "decision_role": "retrieval_only_original_claim_unchanged"})
                    # Qualified recovery leads get their own reading chance.
                    # Already attempted URLs remain in the cumulative budget;
                    # this order never retries or refunds a failed request.
                    leads = NewsSearch([*extra, *leads], status="success" if leads or extra else extra_status)
                    if extra_status not in {"success", "no_results"}:
                        break  # Never work around a quota/credential failure.
                # Follow only primary documents actually cited inline by a
                # first-wave article, with a literal named-topic match. These
                # are retrieval leads, not evidence, extra searches or votes.
                # The shared cache still charges every attempt against six;
                # no recursive crawling or failure refunds are introduced.
                cited_leads = _unread_primary_reference_leads(text, attribution.get("_documents", []), source_url,
                                                            fetched_cache, cited_leads)
                if cited_leads:
                    reference_waves.append({"stage": "base_recovery", "selected_lead_count": len(cited_leads), "status": "reading"})
                    leads = NewsSearch([*cited_leads, *leads], status=getattr(leads, "status", "success"))
                attribution = await collect_source_attribution(text, queries, source_url, search_results=leads,
                    include_documents=True, max_sources=6, fetched_cache=fetched_cache)
                if reference_waves:
                    reference_waves[-1]["status"] = "completed"
                families = usable_source_families(text, attribution.get("_documents", []), source_url)
            missing_claims = claims_needing_research(text, attribution.get("_documents", []), source_url) if ai_research else []
            if (ai_research and missing_claims and len(fetched_cache) < 10
                    and all(item["status"] in {"success", "no_results"} for item in plan)):
                if await follow_primary_references("late_reference"):
                    # Spend only the already-authorized remaining read slots,
                    # before asking a model for another plan. Keep all known
                    # candidates for later research, but this wave follows
                    # only the direct links and retains previous attempts.
                    families = usable_source_families(text, attribution.get("_documents", []), source_url)
                    missing_claims = claims_needing_research(text, attribution.get("_documents", []), source_url)
            if ai_research and missing_claims and all(item["status"] in {"success", "no_results"} for item in plan):
                # Give the model a real bounded search tool. Returned queries
                # and known lead IDs can guide retrieval, never the verdict.
                # Failure/empty plans preserve the complete deterministic read.
                audit = document_selection_audit(text, attribution.get("_documents", []), source_url)
                audit["claims_needing_more_evidence"] = missing_claims
                unread = [item for item in leads if isinstance(item, dict)
                          and (item.get("link") or item.get("url")) not in fetched_cache]
                # Do not let a slow planner consume the entire retrieval
                # deadline. Preserve time for real search and page reads.
                planning_budget = min(45, max(0, deadline - (asyncio.get_running_loop().time() - started) - 20))
                try:
                    if planning_budget <= 0:
                        raise TimeoutError
                    requested = await asyncio.wait_for(plan_source_research(
                        text, unread, attribution.get("_documents", []), audit, source_url), planning_budget)
                except TimeoutError:
                    requested = {"queries": [], "leads": [], "coverage": {
                        "status": "timeout" if planning_budget > 0 else "not_requested",
                        "decision_role": "online_research_planning_only",
                        "planned_query_count": 0, "selected_lead_count": 0,
                        "provider_coverage": {}, "provider_attempt_details_available": planning_budget <= 0,
                        "reason": ("Planejamento interrompido pelo orçamento de recuperação; detalhes individuais das tentativas não foram recuperados."
                                   if planning_budget > 0 else "Sem orçamento restante para iniciar o planejador; leituras concluídas foram preservadas.")}}
                research = requested["coverage"]
                research["planning_budget_seconds"] = round(planning_budget, 3)
                additions = [{**item, "retrieval_method": "ai_selected_candidate_reference"} for item in requested["leads"]]
                searches, scope_audit = _research_scope_plan(text, requested["queries"], previous_queries)
                research.update(scope_audit, executed_query_count=0, deterministic_gap_query_executed_count=0,
                                scope_diversified_query_executed_count=0)
                for search in searches:
                    query_text = _research_query_text(search["query"], search["source_group"], text)
                    if len(query_text) > 500:
                        continue
                    extra = await search_web(query_text)
                    extra_status = getattr(extra, "status", "success" if extra else "no_results")
                    deterministic_gap_query = search["query_origin"] == "deterministic_original_neutral"
                    plan.append({"method": "deterministic_research_gap_recovery" if deterministic_gap_query else "ai_directed_online_research", "status": extra_status,
                                 "decision_role": "retrieval_only_original_claim_unchanged", "query_origin": search["query_origin"],
                                 "requested_source_group": search["requested_source_group"], "executed_source_group": search["source_group"],
                                 "scope_change_reason": search["scope_change_reason"]})
                    research["deterministic_gap_query_executed_count" if deterministic_gap_query else "executed_query_count"] += 1
                    research["scope_diversified_query_executed_count"] += int(not deterministic_gap_query
                        and search["requested_source_group"] != search["source_group"])
                    additions.extend(extra)
                    if extra_status not in {"success", "no_results"}:
                        break  # A real quota failure is not retried or bypassed.
                if additions:
                    leads = NewsSearch([*additions, *leads], status="success")
                    # A newly found article may contain the useful original
                    # reference. Reserve the remaining direct-link slots before
                    # spending all ten reads on search results; if no useful
                    # link exists, release those slots back to the same queue.
                    can_follow = all(item["status"] in {"success", "no_results"} for item in plan)
                    reserve = max(0, 2 - len(cited_leads)) if can_follow else 0
                    attribution = await collect_source_attribution(text, queries, source_url, search_results=leads,
                        include_documents=True, max_sources=max(len(fetched_cache), 10 - reserve), fetched_cache=fetched_cache)
                    if can_follow and claims_needing_research(text, attribution.get("_documents", []), source_url):
                        await follow_primary_references("research_reference")
                    if (len(fetched_cache) < 10
                            and claims_needing_research(text, attribution.get("_documents", []), source_url)):
                        attribution = await collect_source_attribution(text, queries, source_url, search_results=leads,
                            include_documents=True, max_sources=10, fetched_cache=fetched_cache)
                    families = usable_source_families(text, attribution.get("_documents", []), source_url)
            if crosscheck_enabled:
                attribution["selection_audit"] = document_selection_audit(text, attribution.get("_documents", []), source_url)
                attribution["_documents"] = select_comparison_documents(text, attribution.get("_documents", []), source_url)
            attribution.setdefault("coverage", {})["search_queries"] = plan
            attribution["coverage"]["max_search_queries"] = limit + (2 if ai_research else 0)
            attribution["coverage"]["retrieval_deadline_seconds"] = deadline
            attribution["coverage"]["usable_source_family_count"] = len(families)
            attribution["coverage"]["max_comparison_documents"] = 3
            attribution["coverage"]["cited_primary_reference_lead_count"] = len(cited_leads)
            attribution["coverage"]["direct_reference_recovery"] = {
                "max_leads": 2, "max_depth": 1, "selected_lead_count": len(cited_leads),
                "waves": reference_waves, "decision_role": "retrieval_only_no_truth_vote"}
            attribution["coverage"]["online_research"] = research
            attribution["coverage"]["official_record_recovery"] = official_record_recovery
            return attribution
    except Exception:
        if isinstance(attribution, dict):
            # Preserve successfully read first-wave evidence if recovery fails;
            # never hide the missing wave or treat it as additional support.
            documents = attribution.get("_documents", [])
            if crosscheck_enabled:
                attribution["selection_audit"] = document_selection_audit(text, documents, source_url)
                attribution["_documents"] = select_comparison_documents(text, documents, source_url)
            attribution.setdefault("coverage", {}).update(
                search_queries=plan, retrieval_deadline_seconds=deadline,
                online_research={**research, "incomplete": True},
                cumulative_fetch_attempt_count=len(fetched_cache),
                official_record_recovery=official_record_recovery,
                direct_reference_recovery={"max_leads": 2, "max_depth": 1, "selected_lead_count": len(cited_leads),
                    "waves": [{**wave, "status": "incomplete" if wave["status"] == "reading" else wave["status"]}
                              for wave in reference_waves], "decision_role": "retrieval_only_no_truth_vote"},
                cited_primary_reference_lead_count=len(cited_leads),
                recovery_status="timeout_or_error", usable_source_family_count=len(usable_source_families(text, documents, source_url)))
            attribution.setdefault("limitations", []).append("A recuperação adicional não terminou; somente as coletas concluídas foram preservadas. Tentativas interrompidas não fornecem evidência adicional.")
            return attribution
        return {"status": "error", "decision_role": "source_attribution_only", "matches": [],
                "reason": "A leitura das referências não foi concluída no prazo ou com segurança.",
                "limitations": ["Referências não confirmam automaticamente verdade, falsidade ou a página inteira."],
                "coverage": {"status": "error", "decision_role": "source_attribution_only",
                    "cumulative_fetch_attempt_count": len(fetched_cache),
                    "official_record_recovery": official_record_recovery}}


def extract_dates_from_text(text: str) -> list[str]:
    patterns = [
        r"\b(\d{2}[/\-.]\d{2}[/\-.]\d{2,4})\b",
        r"\b(\d{4}[/\-.]\d{2}[/\-.]\d{2})\b",
        r"\b(\d{1,2}\s+(?:janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro))\b",
        r"\b(hoje|ontem|há\s+\d+\s*[d-hm]|na\s+semana)\b",
        r"\b(\d{2}\s+(?:de\s+)?(?:janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro))\b",
    ]
    found = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        found.extend(matches)
    return found


def extract_source_from_url(url: str) -> dict:
    if not url:
        return {"source_name": "Nenhuma", "is_trusted": False, "score": 50}
    from urllib.parse import urlparse
    try:
        hostname = urlparse(url).hostname or ""
    except Exception:
        hostname = url.lower()

    trusted_domains = [
        "globo.com", "bbc.com", "bbc.co.uk", "cnn.com", "cnnbrasil.com.br", "uol.com.br",
        "reuters.com", "ebc.com.br", "estadao.com.br", "correiobraziliense.com.br", "exame.com",
        "gov.br", "wikipedia.org",
    ]
    hostname = hostname.lower().rstrip(".")
    is_trusted = any(hostname == t or hostname.endswith("." + t) for t in trusted_domains)
    
    if is_trusted:
        return {"source_name": hostname, "is_trusted": True, "score": 88}
    
    return {"source_name": hostname, "is_trusted": False, "score": 50}


def analyze_temporal_context(serper_news: list, scrape_date: str = None) -> dict:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    dates_found = []
    
    for item in serper_news:
        date_str = item.get("date", "")
        if date_str:
            dates_found.append(date_str)
    
    if not dates_found and scrape_date:
        dates_found.append(scrape_date)
    
    is_recent = False
    max_age_hours = 24
    
    if dates_found:
        try:
            first_date_str = dates_found[0]
            for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%Y %H:%M", "%B %d, %Y"]:
                try:
                    parsed = datetime.strptime(first_date_str[:len("2024-12-31T23:59:59")], fmt)
                    age = now - parsed
                    max_age_hours = min(max_age_hours, abs(age.total_seconds()) / 3600)
                    is_recent = age.total_seconds() < 7 * 24 * 3600
                    break
                except (ValueError, TypeError):
                    continue
        except Exception:
            pass
    
    return {
        "is_recent": is_recent,
        "max_age_hours": round(max_age_hours, 1),
        "dates_found": dates_found[:3],
        "news_count": len(serper_news),
    }


async def run_pipeline(text: str, url: str | None = None, *, use_ai_extraction: bool = True,
                       use_source_crosscheck: bool = True, use_detailed_report: bool = False) -> dict:
    deadline = asyncio.get_running_loop().time() + PIPELINE_BUDGET_SECONDS
    source_url = url
    analysis_text = text

    scam_info = analyze_scam_indicators(analysis_text, source_url)

    openrouter_result = {"available": False, "status": "not_configured", "claims": [],
                         "decision_role": "search_hints_only", "free_only": True}
    gemini_coverage = None
    literal_input = analysis_text.strip()
    skip_literal_extraction = (use_ai_extraction and 0 < len(literal_input) <= MAX_NEWS_QUERY_CHARS
                               and input_claims(literal_input) == [literal_input])
    if skip_literal_extraction:
        # The complete sentence already fits both literal search paths. Another
        # model cannot select a different sentence, so reserve its free budget
        # for source research/comparison and preserve every original qualifier.
        openrouter_result.update(status="not_requested", reason="literal_single_sentence_no_extra_extraction")
        gemini_coverage = {"available": False, "status": "not_requested", "decision_role": "search_hints_only",
                           "reason": "literal_single_sentence_no_extra_extraction"}
    if (use_ai_extraction and not skip_literal_extraction and os.getenv("OPENROUTER_API_KEY", "").strip()
            and os.getenv("OPENROUTER_ENABLED", "true").lower() == "true"):
        openrouter_result = await _run_openrouter_check(analysis_text)
    if openrouter_result.get("available"):
        claims = openrouter_result["claims"]
    elif use_ai_extraction and not skip_literal_extraction:
        try:
            claims = await asyncio.wait_for(extract_claims_with_ai(analysis_text), gemini_timeout_seconds() + 2)
            gemini_coverage = getattr(claims, "coverage", {"status": "success", "decision_role": "search_hints_only"})
            claims = list(claims)
        except asyncio.TimeoutError:
            claims = []
            gemini_coverage = {"available": False, "status": "timeout", "decision_role": "search_hints_only",
                               "reason": "Extração Gemini não concluída no prazo; a consulta literal foi preservada."}
        except Exception:
            claims = []
            gemini_coverage = {"available": False, "status": "error", "decision_role": "search_hints_only",
                               "reason": "Extração Gemini indisponível; a consulta literal foi preservada."}
    else:
        # Short single sentences need no selection; OCR/transcription may also
        # explicitly disable extraction. Neither spends another LLM request.
        claims = []
    # Retrieve literal input as well as extraction. Model paraphrases are search
    # hints only: they cannot change the statement that receives the verdict.
    fact_check_queries, query_plan = build_fact_check_queries(analysis_text, claims, limit=5)
    ai_task = asyncio.create_task(detect_ai_text(analysis_text))
    domain_task = (asyncio.create_task(asyncio.to_thread(check_domain_reputation, source_url)) if source_url else None)
    fact_tasks = [
        asyncio.create_task(query_fact_check_api(query))
        for query in fact_check_queries
    ]

    serper_news_queries, news_query_plan = build_fact_check_queries(
        analysis_text, claims, limit=3, max_query_chars=MAX_NEWS_QUERY_CHARS)
    serper_news_tasks = [
        asyncio.create_task(search_news(query))
        for query in serper_news_queries
    ]
    attribution_task = asyncio.create_task(_retrieve_source_attribution(
        analysis_text, fact_check_queries, source_url, use_source_crosscheck=use_source_crosscheck))
    tasks = [*fact_tasks, *serper_news_tasks, ai_task, attribution_task]
    if domain_task:
        tasks.append(domain_task)
    
    await _await_pipeline_tasks(tasks, min(INITIAL_QUERY_BUDGET_SECONDS,
        max(0, deadline - asyncio.get_running_loop().time())))
    
    fact_checks = []
    seen_fact_checks: set[tuple[str, str | None]] = set()
    for task in fact_tasks:
        if _task_failed(task):
            continue
        for fact_check in task.result():
            key = (fact_check.claim_text.casefold(), fact_check.url)
            if key in seen_fact_checks:
                continue
            seen_fact_checks.add(key)
            fact_checks.append(fact_check)
    fact_checks = fact_checks[:30]

    ai_forensics = ai_task.result() if not _task_failed(ai_task) else {"ai_probability": None}
    domain_info = domain_task.result() if domain_task and not _task_failed(domain_task) else { "score": None, "note": "Domínio não analisado" }

    serper_news_results = []
    raw_news_count = 0
    seen_links: set[str] = set()
    for task in serper_news_tasks:
        if _task_failed(task):
            continue
        for item in task.result():
            raw_news_count += 1
            link = item.get("link")
            if link and link in seen_links:
                continue
            if link:
                seen_links.add(link)
            serper_news_results.append(item)

    unique_news_count = len(serper_news_results)
    serper_news_results, news_relevance = filter_context_news(analysis_text, serper_news_results)

    dates_in_text = extract_dates_from_text(analysis_text)
    source_info = extract_source_from_url(source_url) if source_url else {"source_name": "Nenhuma", "is_trusted": False, "score": 50}
    temporal_info = analyze_temporal_context(serper_news_results)

    context = {
        "scam_analysis": scam_info,
        "gptzero": ai_forensics,
        "domain": domain_info,
        "claims": claims,
        "fact_checks": [fc.model_dump() for fc in fact_checks],
        "serper_news": serper_news_results,
        "source_url": source_url,
        "temporal_context": temporal_info,
        "dates_in_content": dates_in_text,
        "source_info": source_info,
    }

    # Preserve Juan's explicit text/link report opt-in, not the historical
    # model-only classifier. The final decision still requires valid evidence.
    ai = text_report(analysis_text, context["fact_checks"], scam_info)
    ai["search_claims"] = claims
    ai["search_claims_decision_role"] = "search_hints_only"
    ai["scam_analysis"] = scam_info
    ai["serper_news"] = serper_news_results
    source_attribution = (dict(attribution_task.result()) if not _task_failed(attribution_task) else {
        "status": "timeout" if attribution_task.cancelled() else "error", "matches": [], "coverage": {},
        "reason": "A leitura das fontes não foi concluída; somente consultas concluídas foram preservadas."})
    source_documents = source_attribution.pop("_documents", [])
    source_comparison = None
    if use_source_crosscheck and ai.get("veracity_status") == "unverified" and not scam_info["is_scam"]:
        try:
            remaining = max(0, deadline - asyncio.get_running_loop().time())
            source_comparison = await corroborate_sources(analysis_text, source_documents, source_url,
                                                         timeout_seconds=remaining)
            if not isinstance(source_comparison, dict):
                raise ValueError("Invalid comparison envelope")
        except Exception:
            source_comparison = {"version": "source_corroboration_v1", "status": "error", "state": "insufficient",
                "decision_role": "grounded_source_comparison", "claims": [], "coverage": {},
                "reason": "Não foi possível concluir a comparação das fontes; nenhuma conclusão foi acrescentada.",
                "limitations": ["Falha de comparação não comprova verdade ou falsidade."]}
        ai = apply_source_decision(analysis_text, ai, source_comparison)
        ai["source_corroboration"] = source_comparison
    ai["source_attribution"] = source_attribution
    queries = [{"status": "timeout" if task.cancelled() else "error" if _task_failed(task) else getattr(task.result(), "status", "success" if task.result() else "no_results"),
                "reason": "Consulta não concluída." if _task_failed(task) else getattr(task.result(), "reason", None)} for task in fact_tasks]
    status = ("success" if fact_checks else "no_results" if any(q["status"] in {"success", "no_results"} for q in queries)
              else "not_configured" if all(q["status"] == "not_configured" for q in queries) else "error")
    ai["provider_coverage"] = {"google_fact_check": {
        "status": status, "queries": queries, "query_plan": query_plan, "matches_returned": len(fact_checks),
        "reason": "Consulta concluída sem checagens correspondentes." if status == "no_results" else
                  next((q["reason"] for q in queries if q["reason"]), None)}}
    ai["provider_coverage"]["web_references"] = {
        **source_attribution.get("coverage", {}),
        "status": "success" if source_attribution["status"] == "found" else source_attribution["status"],
        "decision_role": "source_attribution_only", "matches_returned": len(source_attribution.get("matches", [])),
        "reason": source_attribution.get("reason"),
    }
    if source_comparison is not None:
        ai["provider_coverage"]["source_crosscheck"] = {
            "status": source_comparison.get("status", "error"),
            "decision_role": "grounded_source_comparison",
            "reason": source_comparison.get("reason"),
            "coverage": source_comparison.get("coverage", {}),
        }
    if use_ai_extraction:
        ai["provider_coverage"]["openrouter"] = {key: value for key, value in openrouter_result.items()
            if key in {"available", "status", "reason", "model_used", "decision_role", "free_only", "response_issue"}}
        if gemini_coverage is not None:
            ai["provider_coverage"]["gemini"] = gemini_coverage
    ai["provider_coverage"]["analysis_budget"] = {
        "status": "partial" if any(task.cancelled() for task in tasks) else "success",
        "total_seconds": PIPELINE_BUDGET_SECONDS, "parallel_queries_seconds": INITIAL_QUERY_BUDGET_SECONDS,
        "incomplete_query_count": sum(task.cancelled() for task in tasks),
        "elapsed_seconds": round(max(0, PIPELINE_BUDGET_SECONDS - (deadline - asyncio.get_running_loop().time())), 3),
        "decision_role": "execution_coverage_only"}
    news_queries = [{"status": "timeout" if task.cancelled() else "error" if _task_failed(task) else getattr(task.result(), "status", "success" if task.result() else "no_results"),
                     "reason": "Busca de contexto não concluída." if _task_failed(task) else getattr(task.result(), "reason", None)}
                    for task in serper_news_tasks]
    news_status = ("not_requested" if not news_queries else "success" if serper_news_results else "no_results" if any(q["status"] in {"success", "no_results"} for q in news_queries)
                   else "not_configured" if all(q["status"] == "not_configured" for q in news_queries) else "error")
    ai["provider_coverage"]["serper"] = {"status": news_status, "queries": news_queries, "decision_role": "context_only",
                                          "query_plan": news_query_plan,
                                          "matches_returned": len(serper_news_results),
                                          "raw_matches_returned": raw_news_count, "unique_matches_returned": unique_news_count,
                                          "relevance_filter": news_relevance,
                                          "reason": "Busca omitida: nenhuma frase completa cabe no limite de 500 caracteres; nenhum texto foi cortado." if news_status == "not_requested" else
                                                    "Busca concluída sem notícias com correspondência lexical utilizável; isso não prova falsidade." if news_status == "no_results" else next((q["reason"] for q in news_queries if q["reason"]), None)}

    if scam_info["is_scam"]:
        ai["verdict"] = "Scam"
        ai["analysis_status"] = "partial"
        ai["summary"] = "Há padrões conhecidos de possível golpe nesta mensagem. Não pague taxas nem envie dados sem confirmar pelo canal oficial."
        ai["plain_explanation"] = "Foram encontrados sinais no conteúdo da mensagem, não uma comprovação da identidade do remetente ou uma investigação concluída."
        ai["whatsapp_share_text"] = "⚠️ O Verify identificou sinais de possível golpe. Não envie dinheiro nem dados antes de confirmar por um canal oficial."
        ai["score"] = min(ai.get("score", 10), 15)
        for pattern in scam_info["detected_patterns"]:
            red_flag = f"Alerta de Golpe: {pattern['category']} - {pattern['description']}"
            if "red_flags" in ai and red_flag not in ai["red_flags"]:
                ai["red_flags"].append(red_flag)
        if scam_info.get("suspicious_url") and scam_info.get("suspicious_url_reason"):
            ai.setdefault("red_flags", []).append(f"Link Suspeito: {scam_info['suspicious_url_reason']}")

    # Explanations are rendered after every decision/coverage layer. No extra
    # model call, new evidence, classification, probability or quota is added.
    if use_detailed_report:
        ai = enrich_grounded_report(ai)

    return {
        "report": ai,
        "claims": claims,
        "metrics": {
            "text_ai_probability": ai_forensics.get("ai_probability"),
            "fact_checks_count": len(fact_checks),
            "serper_news_count": len(serper_news_results),
            "domain_score": domain_info.get("score"),
            "earliest_known_date": (temporal_info.get("dates_found") or [None])[0],
            "temporal_info": temporal_info,
            "source_info": source_info,
            "openrouter_available": bool(openrouter_result.get("available")),
            "divergent": ai.get("divergent", False),
            "agreement_note": ai.get("agreement_note", ""),
            "model_used": ai.get("model_used", "gemini"),
        },
        "fact_checks": fact_checks,
        "serper_news": serper_news_results,
        "domain_info": domain_info,
        "scam_analysis": scam_info,
        "temporal_context": temporal_info,
        "source_info": source_info,
    }
