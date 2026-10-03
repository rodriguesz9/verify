import { SearchCheck, FileText, ExternalLink, Info, CircleAlert } from "lucide-react";
import { buildReportEvidence } from "../../utils/reportEvidence";

export default function EvidenceExplanation({result, query}) {
  const evidence = buildReportEvidence(result, query);
  const excluded = evidence.claimAssessments.flatMap((item) =>
    Array.isArray(item.excluded_evidence) ? item.excluded_evidence.filter((source) => source && typeof source === "object") : []);
  return (
    <section aria-labelledby="evidence-heading" className="report-evidence mb-8 rounded-2xl border border-[#1D3B4D] bg-[#0A1520] p-5 sm:p-8">
      <div className="flex items-start gap-3 mb-5">
        <SearchCheck className="text-[#00D4FF] shrink-0 mt-1" size={24} aria-hidden="true" />
        <div>
          <p className="text-[11px] font-mono text-[#00D4FF] uppercase tracking-widest mb-1">Evidências e raciocínio</p>
          <h3 id="evidence-heading" className="font-syne font-bold text-xl sm:text-2xl">Entenda o resultado, ponto a ponto</h3>
          <p className="mt-3 text-sm leading-6 text-[#A7BFCD]">{evidence.interpretation}</p>
        </div>
      </div>

      {result.veracity_status && <div className="mb-6 grid gap-3 sm:grid-cols-2 text-sm">
        <div className="rounded-xl border border-[#1D3B4D] p-4"><h4 className="font-bold mb-2">Veracidade da informação</h4>
          <p>{({supported: "Corroborada nas checagens", refuted: "Refutada nas checagens", mixed: "Afirmações mistas", conflicting: "Fontes em desacordo", unverified: "Não determinada"})[evidence.veracityStatus] || "Não determinada"}</p>
          {evidence.media && <p className="mt-2 text-xs text-[#8AA2B4]">Texto extraído por {evidence.contentOrigin === "ocr" ? "OCR" : "transcrição"}: pode conter erros. Isso é separado da origem da mídia.</p>}
        </div>
        <div className="rounded-xl border border-[#1D3B4D] p-4"><h4 className="font-bold mb-2">Origem/produção da mídia</h4>
          <p>{({not_applicable: "Não se aplica à análise de texto", ai_indications: "Indícios de geração por IA", manipulation_indications: "Indícios de manipulação", undetermined: "Não determinada"})[result.authenticity_status] || "Não determinada"}</p>
          <p className="mt-2 text-xs text-[#8AA2B4]">Mídia gerada por IA pode apresentar informação verdadeira; uma gravação real pode apresentar informação falsa.</p>
        </div>
      </div>}
      {evidence.media && result.content_analysis && <p className="mb-5 text-sm leading-6 text-[#A7BFCD]">Checagem do conteúdo extraído: {evidence.contentSummary}</p>}
      {excluded.length > 0 && <details className="mb-6 rounded-xl border border-[#1D3B4D] p-4">
        <summary className="cursor-pointer font-bold text-sm">Por que algumas checagens não foram usadas?</summary>
        <ul className="mt-3 space-y-2 text-sm text-[#A7BFCD]">{excluded.map((source, i) => <li key={i}>{source.publisher || "Fonte"}: {source.exclusion_reason || "Correspondência insuficiente."}</li>)}</ul>
        <p className="mt-3 text-xs text-[#8AA2B4]">Somente duas famílias editoriais distintas, com avaliação explícita e correspondência válida, permitem corroborar ou refutar. Uma paráfrase pode exigir checagem humana.</p>
      </details>}

      {evidence.checkedContent && <details className="mb-6 rounded-xl border border-[#1D3B4D] bg-[#070F17] p-4">
        <summary className="cursor-pointer font-bold text-sm">Conteúdo enviado para esta checagem</summary>
        <blockquote className="mt-3 text-sm leading-6 whitespace-pre-wrap max-h-52 overflow-y-auto pr-3">{evidence.checkedContent}</blockquote>
      </details>}
      {evidence.claims.length > 0 && <div className="mb-6">
        <h4 className="font-bold mb-2">Afirmações analisadas</h4>
        <ul className="list-disc pl-5 text-sm space-y-2 text-[#A7BFCD]">{evidence.claims.map((claim, index) => <li key={index}>{claim}</li>)}</ul>
      </div>}

      <h4 className="flex items-center gap-2 font-bold mb-3"><CircleAlert size={16} aria-hidden="true" /> O que foi observado nesta análise</h4>
      {evidence.findings.length > 0 ? <ol className="space-y-3 mb-6">
        {evidence.findings.map((finding, index) => <li key={finding.id} className="rounded-xl border border-[#1D3B4D] bg-[#070F17] p-4">
          <h5 className="font-bold text-sm mb-2"><span className="text-[#00D4FF] mr-2">{String(index + 1).padStart(2, "0")}</span>{finding.title}</h5>
          {finding.quote && <blockquote className="border-l-2 border-[#FFCB55] pl-3 py-1 my-3 text-sm text-[#FFCB55]">“{finding.quote}”</blockquote>}
          <p className="text-sm leading-6 text-[#CDE8F0]">{finding.detail}</p>
          <p className="mt-3 font-mono text-[11px] text-[#8AA2B4]">{finding.origin}</p>
        </li>)}
      </ol> : <p className="mb-6 p-4 rounded-xl bg-[#070F17] text-sm leading-6 text-[#A7BFCD]">
        Nenhuma evidência específica de falsidade foi registrada. Não seria correto inventar uma justificativa para classificar o conteúdo como falso.
      </p>}
      {evidence.positives.length > 0 && <div className="mb-6">
        <h4 className="font-bold mb-2">Sinais favoráveis registrados</h4>
        <ul className="list-disc pl-5 text-sm leading-6 space-y-2 text-[#A7BFCD]">{evidence.positives.map((signal, index) => <li key={index}>{signal}</li>)}</ul>
        <p className="text-xs text-[#8AA2B4] mt-2">Sinais favoráveis também precisam de confirmação; não são um certificado de autenticidade.</p>
      </div>}

      <div className="border-t border-[#1D3B4D] pt-5">
        <h4 className="flex items-center gap-2 font-bold mb-3"><FileText size={16} aria-hidden="true" /> Fontes e checagens encontradas</h4>
        {evidence.sources.length > 0 ? <>
          <p className="text-sm leading-6 text-[#A7BFCD] mb-4">Compare a afirmação, a data e o contexto. Uma notícia relacionada não confirma automaticamente o conteúdo enviado.</p>
          <div className="space-y-3">{evidence.sources.map((source) => <article key={source.id} className="p-4 rounded-xl bg-[#070F17] border border-[#1D3B4D]">
            <p className="text-xs text-[#8AA2B4] mb-2">{source.kind} · {source.publisher}{source.date ? ` · ${source.date}` : ""}</p>
            <p className="text-sm font-bold leading-6">{source.title}</p>
            {source.note && <p className="mt-2 text-sm text-[#A7BFCD]">Não usada como evidência: {source.note}</p>}
            {source.rating && <p className="text-sm text-[#FFCB55] mt-2">Avaliação da fonte para essa afirmação: {source.rating}</p>}
            {source.url && <a href={source.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 mt-3 text-sm text-[#00D4FF] underline underline-offset-4">
              Abrir fonte original <ExternalLink size={13} aria-hidden="true" />
            </a>}
          </article>)}</div>
        </> : <p className="text-sm leading-6 text-[#A7BFCD]">Nenhuma referência externa de checagem foi retornada neste relatório. Isso não prova falsidade e não significa que todas as fontes existentes foram consultadas.</p>}
      </div>

      {evidence.guidance.length > 0 && <div className="mt-5 p-4 rounded-xl border border-[#00D4FF]/25 bg-[#00D4FF]/5">
        <h4 className="font-bold text-sm mb-2">Orientação oficial para você conferir</h4>
        <p className="text-xs leading-5 text-[#8AA2B4] mb-3">Referências de segurança cadastradas no Verify. Não são uma checagem automática desta mensagem específica.</p>
        <ul className="space-y-3">{evidence.guidance.map((item, index) => <li key={index}>
          <a href={item.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 text-sm text-[#00D4FF] underline underline-offset-4">
            {item.title} <ExternalLink size={13} className="shrink-0" aria-hidden="true" />
          </a>
        </li>)}</ul>
      </div>}

      {evidence.sampledFrames !== null && <div className="mt-5 p-4 rounded-xl border border-[#1D3B4D] text-sm leading-6">
        <h4 className="font-bold mb-2">Qual parte do vídeo foi analisada?</h4>
        <p>{evidence.sampledFrames} quadros amostrados{evidence.timestamps.length ? `, nos tempos ${evidence.timestamps.map((time) => `${time.toFixed(1)} s`).join(", ")}` : ""}. Não é uma inspeção de todos os quadros nem da sincronização labial. A faixa de áudio, quando disponível, tem análise separada.</p>
      </div>}
      {evidence.transcription && <details className="mt-5 p-4 rounded-xl border border-[#1D3B4D]">
        <summary className="cursor-pointer font-bold text-sm">Transcrição disponível · não comprova origem da voz</summary>
        <p className="mt-3 text-sm leading-6 whitespace-pre-wrap max-h-64 overflow-y-auto pr-3">{evidence.transcription}</p>
      </details>}
      {evidence.missing.length > 0 && <div className="mt-5 p-4 rounded-xl border border-[#FFCB55]/25 bg-[#FFCB55]/5">
        <h4 className="font-bold text-sm text-[#FFCB55] flex items-center gap-2"><Info size={16} aria-hidden="true" /> O que ficou sem confirmação</h4>
        <ul className="list-disc pl-5 mt-3 text-sm space-y-2 text-[#A7BFCD]">{evidence.missing.map((item, index) => <li key={index}>{item}</li>)}</ul>
      </div>}
      <p className="mt-5 text-sm leading-6 text-[#A7BFCD]"><strong className="text-[#CDE8F0]">Como conferir por conta própria:</strong> busque a publicação original, confirme a data e compare com uma fonte independente. Em pedidos de dinheiro ou dados, fale com a pessoa ou instituição por um canal que você já conhece.</p>
      {result.policy_version && <p className="mt-3 font-mono text-[11px] text-[#8AA2B4]">Política da análise: {result.policy_version}</p>}
    </section>
  );
}
