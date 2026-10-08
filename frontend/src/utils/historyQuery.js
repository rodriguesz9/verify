// One cancellable, debounced load. Late responses from replaced/unmounted
// queries must never replace the visible page, error or loading state.
export function averageScoreLabel(stats) {
  return Number.isInteger(stats?.avg_score_count) && stats.avg_score_count > 0
    && typeof stats.avg_score === "number" && Number.isFinite(stats.avg_score) && stats.avg_score >= 0 && stats.avg_score <= 100
    ? `${stats.avg_score}/100` : "Não determinado";
}

export function scheduleHistoryLoad({
  query, loadHistory, loadStats, onStart, onSuccess, onError, onFinish,
  delay = 300, schedule = setTimeout, cancel = clearTimeout,
}) {
  const controller = new AbortController();
  let active = true;
  onStart();
  const timer = schedule(async () => {
    if (!active) return;
    try {
      const [history, stats] = await Promise.all([
        loadHistory(query.page, {
          search: query.search.trim(), contentType: query.contentType,
          verdict: query.verdict, signal: controller.signal,
        }),
        loadStats(),
      ]);
      if (active) onSuccess(history, stats);
    } catch (error) {
      if (active && error?.code !== "ERR_CANCELED" && error?.name !== "AbortError") onError(error);
    } finally {
      if (active) onFinish();
    }
  }, delay);
  return () => {
    active = false;
    cancel(timer);
    controller.abort();
  };
}
