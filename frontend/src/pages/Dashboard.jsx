import { useEffect, useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowUpRight, FileSearch, Image, Link2, Mic, Plus,
  ScanSearch, Filter, ChevronLeft, ChevronRight, Search, Inbox,
} from "lucide-react";
import Footer from "../components/Footer";
import { getHistory, getStats } from "../services/api";

const VERDICT_COLORS = {
  Authentic: "#00FF87", AI_Generated: "#00D4FF", Manipulated: "#FF3B5C",
  Out_Of_Context: "#FFB830", Suspicious: "#8AA2B4", Scam: "#FF3B5C", False: "#FF3B5C",
};
const TYPES = {
  Text: FileSearch, text: FileSearch, Url: Link2, url: Link2,
  Image, image: Image, Audio: Mic, audio: Mic,
};
const TYPE_FILTERS = [
  { value: "all", label: "Todos", icon: Inbox },
  { value: "Text", label: "Texto", icon: FileSearch },
  { value: "Url", label: "Link", icon: Link2 },
  { value: "Image", label: "Imagem", icon: Image },
  { value: "Audio", label: "Áudio", icon: Mic },
];
const VERDICT_FILTERS = [
  { value: "all", label: "Todos" },
  { value: "Authentic", label: "Verdadeiro" },
  { value: "False", label: "Refutado" },
  { value: "Suspicious", label: "Suspeito" },
  { value: "Scam", label: "Golpe" },
  { value: "AI_Generated", label: "IA" },
  { value: "Manipulated", label: "Manipulado" },
  { value: "Out_Of_Context", label: "Fora de contexto" },
];
const LIMIT = 15;

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

  useEffect(() => {
    setLoading(true);
    Promise.all([getHistory(page), getStats()])
      .then(([history, metrics]) => {
        setItems(history.items || []);
        setTotal(history.total || 0);
        setStats(metrics);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [page]);

  const pages = Math.max(1, Math.ceil(total / LIMIT));

  const filteredItems = useMemo(() => {
    return items.filter((item) => {
      if (typeFilter !== "all" && item.content_type !== typeFilter) return false;
      if (verdictFilter !== "all" && item.verdict_label !== verdictFilter) return false;
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        const input = (item.query_input || "").toLowerCase();
        const summary = (item.ai_summary || "").toLowerCase();
        if (!input.includes(q) && !summary.includes(q)) return false;
      }
      return true;
    });
  }, [items, typeFilter, verdictFilter, searchQuery]);

  const metrics = [
    ["Total", stats?.total ?? 0],
    ["Índice médio · não é precisão", `${stats?.avg_score ?? 0}/100`],
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
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Buscar no conteúdo ou resumo..."
              className="w-full rounded-lg border border-[#132435] bg-[#04080C] py-2.5 pl-9 pr-4 font-mono text-xs text-[#CDE8F0] placeholder-[#3A6070] focus:border-[#00D4FF] focus:outline-none transition-colors"
            />
          </div>

          {/* Type filters */}
          <div className="flex flex-wrap gap-2 mb-2">
            {TYPE_FILTERS.map(({ value, label, icon: Icon }) => (
              <button
                key={value}
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
            <span className="font-mono text-[10px] text-[#8AA2B4]">{filteredItems.length} de {total}</span>
          </div>

          {loading ? (
            <p className="p-10 text-center font-mono text-xs text-[#8AA2B4]">Carregando atividade...</p>
          ) : filteredItems.length === 0 ? (
            <p className="p-10 text-center font-mono text-xs text-[#8AA2B4]">
              {items.length === 0
                ? "Ainda não há verificações. Faça a primeira agora."
                : "Nenhum resultado para os filtros selecionados."}
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-left">
                <thead className="border-b border-[#132435] bg-[#070F17] font-mono text-[10px] uppercase tracking-wider text-[#8AA2B4]">
                  <tr>
                    <th className="px-5 py-3 font-medium">Tipo</th>
                    <th className="px-5 py-3 font-medium">Consulta</th>
                    <th className="px-5 py-3 font-medium">Resultado</th>
                    <th className="px-5 py-3 font-medium">Índice · não é precisão</th>
                    <th className="px-5 py-3 font-medium">Data</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {filteredItems.map((item) => {
                    const Icon = TYPES[item.content_type] || FileSearch;
                    const color = VERDICT_COLORS[item.verdict_label] || "#8AA2B4";
                    return (
                      <tr
                        key={item.id}
                        onClick={() => navigate(`/report/${item.id}`)}
                        className="cursor-pointer border-b border-[#132435] last:border-0 hover:bg-[#0F1E2E] transition-colors"
                      >
                        <td className="px-5 py-4">
                          <Icon size={17} className="text-[#00D4FF]" />
                        </td>
                        <td className="max-w-[340px] truncate px-5 py-4 font-mono text-xs">
                          {item.query_input || "Conteúdo enviado"}
                        </td>
                        <td className="px-5 py-4">
                          <span
                            className="whitespace-nowrap font-mono text-[10px] font-bold uppercase tracking-wider"
                            style={{ color }}
                          >
                            {item.verdict_label || "Em análise"}
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
                          <ArrowUpRight size={16} className="text-[#8AA2B4]" />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination */}
          {pages > 1 && (
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
