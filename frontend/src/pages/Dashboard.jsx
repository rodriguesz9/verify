import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ArrowUpRight, FileSearch, Image, Link2, Mic, Plus,
  ScanSearch, Filter, ChevronLeft, ChevronRight, Search, Inbox, Video,
} from "lucide-react";
import Footer from "../components/Footer";
import { getHistory, getStats } from "../services/api";
import { scheduleHistoryLoad, averageScoreLabel } from "../utils/historyQuery";

const VERDICT_COLORS = {
  Authentic: "#00FF87", AI_Generated: "#00D4FF", Manipulated: "#FF3B5C",
  Out_Of_Context: "#FFB830", Suspicious: "#8AA2B4", Scam: "#FF3B5C", False: "#FF3B5C",
};
const TYPES = {
  Text: FileSearch, text: FileSearch, Url: Link2, url: Link2,
  Image, image: Image, Audio: Mic, audio: Mic, Video, video: Video,
};
const TYPE_FILTERS = [
  { value: "all", label: "Todos", icon: Inbox },
  { value: "Text", label: "Texto", icon: FileSearch },
  { value: "Url", label: "Link", icon: Link2 },
  { value: "Image", label: "Imagem", icon: Image },
  { value: "Audio", label: "Áudio", icon: Mic },
  { value: "Video", label: "Vídeo", icon: Video },
];
const VERDICT_FILTERS = [
  { value: "all", label: "Todos" },
  { value: "Authentic", label: "Corroborado" },
  { value: "False", label: "Refutado" },
  { value: "Suspicious", label: "Suspeito" },
  { value: "Scam", label: "Golpe" },
  { value: "AI_Generated", label: "IA" },
  { value: "Manipulated", label: "Manipulado" },
  { value: "Out_Of_Context", label: "Fora de contexto" },
];
const LIMIT = 20;
const VERDICT_LABELS = {
  Authentic: "Corroborado", False: "Refutado", Suspicious: "Revisar",
  Scam: "Sinais de golpe", AI_Generated: "Indícios de IA",
  Manipulated: "Indícios de manipulação", Out_Of_Context: "Fora de contexto",
};

export default function Dashboard() {
  const navigate = useNavigate();
  const [items, setItems] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [typeFilter, setTypeFilter] = useState("all");
  const [verdictFilter, setVerdictFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);

  useEffect(() => scheduleHistoryLoad({
    query: { page, search: searchQuery, contentType: typeFilter, verdict: verdictFilter },
    loadHistory: getHistory,
    loadStats: getStats,
    onStart: () => { setLoading(true); setError(""); },
    onSuccess: (history, metrics) => {
        const lastPage = Math.max(1, Math.ceil((history.total || 0) / LIMIT));
        if (page > lastPage) { setPage(lastPage); return; }
        setItems(history.items || []);
        setTotal(history.total || 0);
        setStats(metrics);
    },
    onError: () => setError("Não foi possível carregar seu histórico. Verifique a conexão e tente novamente."),
    onFinish: () => setLoading(false),
  }), [page, typeFilter, verdictFilter, searchQuery, retry]);

  const pages = Math.max(1, Math.ceil(total / LIMIT));
  const hasFilters = typeFilter !== "all" || verdictFilter !== "all" || Boolean(searchQuery.trim());

  const metrics = [
    ["Total", stats?.total ?? 0],
    ["Índice médio disponível · não é precisão", averageScoreLabel(stats)],
    ["Hoje", stats?.daily_used ?? 0],
    ["Limite diário", stats?.daily_limit ?? "—"],
  ];

  return (
    <div className="min-h-screen bg-[#04080C] pb-16 text-[#CDE8F0]">
      <main className="mx-auto max-w-7xl px-5 pt-28 sm:px-8">

        {/* Header */}
        <header className="mb-8 flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
          <div>
            <span className="font-mono text-[10px] font-bold uppercase tracking-[3px] text-[#00D4FF]">
              Visão geral
            </span>
            <h1 className="mt-2 font-syne text-3xl font-black">Painel</h1>
            <p className="mt-2 font-mono text-xs text-[#8AA2B4]">
              Métricas, filtros e histórico completo das suas verificações.
            </p>
          </div>
          <button
            onClick={() => navigate("/app")}
            className="flex items-center justify-center gap-2 rounded-lg bg-[#00D4FF] px-4 py-3 font-mono text-xs font-bold uppercase tracking-wider text-[#04080C] hover:bg-[#00D4FF]/80 transition-colors"
          >
            <Plus size={16} /> Nova checagem
          </button>
        </header>

        {/* Metrics */}
        <section className="grid grid-cols-2 border border-[#132435] bg-[#0A1520] md:grid-cols-4">
          {metrics.map(([label, value]) => (
            <div key={label} className="border-b border-r border-[#132435] p-5 last:border-r-0 md:border-b-0">
              <span className="font-mono text-[10px] uppercase tracking-wider text-[#8AA2B4]">{label}</span>
              <strong className="mt-2 block font-syne text-2xl">{value}</strong>
            </div>
          ))}
        </section>

        {/* Filters */}
        <section className="mt-6 rounded-xl border border-[#132435] bg-[#0A1520] p-4">
          <div className="flex items-center gap-2 mb-3">
            <Filter size={14} className="text-[#00D4FF]" />
            <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-[#8AA2B4]">Filtros</span>
          </div>

          {/* Search */}
          <div className="relative mb-3">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#3A6070]" />
            <label htmlFor="history-search" className="sr-only">Buscar em todo o seu histórico</label>
            <input
              id="history-search"
              type="text"
              value={searchQuery}
              maxLength={200}
              onChange={(e) => { setSearchQuery(e.target.value); setPage(1); }}
              placeholder="Buscar no conteúdo ou resumo..."
              className="w-full rounded-lg border border-[#132435] bg-[#04080C] py-2.5 pl-9 pr-4 font-mono text-xs text-[#CDE8F0] placeholder-[#3A6070] focus:border-[#00D4FF] focus:outline-none transition-colors"
            />
          </div>

          {/* Type filters */}
          <div className="flex flex-wrap gap-2 mb-2">
            {TYPE_FILTERS.map(({ value, label, icon: Icon }) => (
              <button
                key={value}
                type="button"
                aria-pressed={typeFilter === value}
                onClick={() => { setTypeFilter(value); setPage(1); }}
                className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 font-mono text-[10px] font-bold uppercase tracking-wider transition-all ${
                  typeFilter === value
                    ? "bg-[#00D4FF] text-[#04080C]"
                    : "bg-[#060D14] text-[#8AA2B4] border border-[#132435] hover:border-[#00D4FF]/50"
                }`}
              >
                <Icon size={12} /> {label}
              </button>
            ))}
          </div>

          {/* Verdict filters */}
          <div className="flex flex-wrap gap-2">
            {VERDICT_FILTERS.map(({ value, label }) => (
              <button
                key={value}
                type="button"
                aria-pressed={verdictFilter === value}
                onClick={() => { setVerdictFilter(value); setPage(1); }}
                className={`rounded-lg px-3 py-1.5 font-mono text-[10px] font-bold uppercase tracking-wider transition-all ${
                  verdictFilter === value
                    ? "bg-[#00FF87] text-[#04080C]"
                    : "bg-[#060D14] text-[#8AA2B4] border border-[#132435] hover:border-[#00FF87]/50"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </section>

        {/* Table */}
        <section className="mt-6 overflow-hidden rounded-xl border border-[#132435] bg-[#0A1520]">
          <div className="flex items-center justify-between border-b border-[#132435] px-5 py-4">
            <div className="flex items-center gap-2 font-mono text-xs font-bold uppercase tracking-wider">
              <ScanSearch size={15} className="text-[#00D4FF]" /> Registros
            </div>
            <span className="font-mono text-[10px] text-[#8AA2B4]" aria-live="polite">{loading || error ? "—" : `${items.length} nesta página · ${total} encontrados`}</span>
          </div>

          {loading ? (
            <p className="p-10 text-center font-mono text-xs text-[#8AA2B4]" role="status">Carregando atividade...</p>
          ) : error ? (
            <div className="p-8 text-center" role="alert">
              <p className="font-mono text-sm text-[#FFCB55]">{error}</p>
              <button type="button" onClick={() => setRetry((value) => value + 1)} className="mt-4 rounded-lg border border-[#00D4FF] px-4 py-3 font-mono text-xs text-[#00D4FF] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4">Tentar novamente</button>
            </div>
          ) : items.length === 0 ? (
            <p className="p-10 text-center font-mono text-xs text-[#8AA2B4]">
              {hasFilters ? "Nenhum resultado para a busca e os filtros selecionados." : "Ainda não há verificações. Faça a primeira agora."}
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-left">
                <caption className="sr-only">Seu histórico de verificações; abra uma consulta para ler o relatório.</caption>
                <thead className="border-b border-[#132435] bg-[#070F17] font-mono text-[10px] uppercase tracking-wider text-[#8AA2B4]">
                  <tr>
                    <th className="px-5 py-3 font-medium">Tipo</th>
                    <th className="px-5 py-3 font-medium">Consulta</th>
                    <th className="px-5 py-3 font-medium">Resultado</th>
                    <th className="px-5 py-3 font-medium">Índice · não é precisão</th>
                    <th className="px-5 py-3 font-medium">Data</th>
                    <th className="px-5 py-3 font-medium"><span className="sr-only">Abrir relatório</span></th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => {
                    const Icon = TYPES[item.content_type] || FileSearch;
                    const color = VERDICT_COLORS[item.verdict_label] || "#8AA2B4";
                    return (
                      <tr
                        key={item.id}
                        className="border-b border-[#132435] last:border-0 hover:bg-[#0F1E2E] transition-colors"
                      >
                        <td className="px-5 py-4">
                          <Icon size={17} className="text-[#00D4FF]" />
                        </td>
                        <td className="max-w-[340px] truncate px-5 py-4 font-mono text-xs">
                          <Link to={`/report/${item.id}`} className="block truncate hover:text-[#00D4FF] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#00D4FF] focus-visible:outline-offset-2">{item.query_input || "Conteúdo enviado"}</Link>
                        </td>
                        <td className="px-5 py-4">
                          <span
                            className="whitespace-nowrap font-mono text-[10px] font-bold uppercase tracking-wider"
                            style={{ color }}
                          >
                            {item.analysis_status === "inconclusive" ? "Inconclusivo" : VERDICT_LABELS[item.verdict_label] || "Revisar"}
                          </span>
                        </td>
                        <td className="px-5 py-4 font-mono text-xs" style={{ color }}>
                          {item.verdict_score == null ? "Não determinado" : `${item.verdict_score}/100`}
                        </td>
                        <td className="whitespace-nowrap px-5 py-4 font-mono text-[11px] text-[#8AA2B4]">
                          {item.created_at
                            ? new Date(item.created_at).toLocaleDateString("pt-BR")
                            : "—"}
                        </td>
                        <td className="px-5 py-4">
                          <Link to={`/report/${item.id}`} aria-label={`Abrir relatório: ${item.query_input || "conteúdo enviado"}`} className="inline-flex min-h-10 min-w-10 items-center justify-center rounded-lg text-[#8AA2B4] hover:text-[#00D4FF] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#00D4FF] focus-visible:outline-offset-2"><ArrowUpRight size={16} aria-hidden="true" /></Link>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination */}
          {!error && !loading && pages > 1 && (
            <div className="flex items-center justify-between border-t border-[#132435] px-5 py-3">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
                className="flex items-center gap-1 rounded-lg px-3 py-1.5 font-mono text-[10px] font-bold uppercase tracking-wider text-[#8AA2B4] hover:text-[#00D4FF] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronLeft size={14} /> Anterior
              </button>
              <span className="font-mono text-[10px] text-[#8AA2B4]">
                Página {page} de {pages}
              </span>
              <button
                disabled={page >= pages}
                onClick={() => setPage((p) => p + 1)}
                className="flex items-center gap-1 rounded-lg px-3 py-1.5 font-mono text-[10px] font-bold uppercase tracking-wider text-[#8AA2B4] hover:text-[#00D4FF] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                Próxima <ChevronRight size={14} />
              </button>
            </div>
          )}
        </section>
      </main>
      <Footer />
    </div>
  );
}
