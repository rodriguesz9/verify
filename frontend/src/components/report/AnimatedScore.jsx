import { useEffect, useId, useState } from "react";
import { animatedScoreAt, normalizeScore } from "../../utils/reportEvidence";
import { useAccessibility } from "../../hooks/useAccessibility";

export default function AnimatedScore({value, color = "#00D4FF", label = "Índice heurístico · não é certeza", unavailableText = "Não determinado", compact = false}) {
  const target = normalizeScore(value);
  const { easyMode } = useAccessibility();
  const [display, setDisplay] = useState(0);
  const labelId = useId();

  useEffect(() => {
    setDisplay(0);
    if (target === null) return;
    const preference = window.matchMedia("(prefers-reduced-motion: reduce)");
    let frame;
    let start;
    const finish = () => {
      cancelAnimationFrame(frame);
      setDisplay(target);
    };
    const onPreferenceChange = (event) => { if (event.matches) finish(); };
    preference.addEventListener("change", onPreferenceChange);
    if (preference.matches || easyMode) {
      finish();
    } else {
      const tick = (timestamp) => {
        start ??= timestamp;
        const progress = Math.min(1, (timestamp - start) / 1200);
        setDisplay(animatedScoreAt(target, progress));
        if (progress < 1) frame = requestAnimationFrame(tick);
      };
      frame = requestAnimationFrame(tick);
    }
    return () => {
      cancelAnimationFrame(frame);
      preference.removeEventListener("change", onPreferenceChange);
    };
  }, [target, easyMode]);

  return (
    <div className={compact ? "report-score min-w-0 w-full max-w-full" : "report-score min-w-0 w-full max-w-full rounded-xl bg-[#04080C88] p-4 border border-white/10"}>
      <div className="report-score-header flex items-start justify-between gap-3 mb-3">
        <span id={labelId} className="text-[11px] font-mono leading-5 text-[#8AA2B4]">{label}</span>
        {target !== null && <span className={compact ? "font-mono text-sm font-bold shrink-0" : "font-syne text-3xl font-black tabular-nums shrink-0"} style={{color}}>
          <span aria-hidden="true">{Math.round(display)}<span className="text-sm">/100</span></span>
          <span className="sr-only">{target} de 100</span>
        </span>}
      </div>
      {target === null ? <p className="report-score-empty font-bold text-base sm:text-lg leading-snug" style={{color}}>{unavailableText}</p> : (
        <div role="progressbar" aria-labelledby={labelId} aria-valuemin={0} aria-valuemax={100}
          aria-valuenow={target} aria-valuetext={`${target} de 100, índice não calibrado`}
          className="h-2.5 rounded-full overflow-hidden bg-[#132435]">
          <div data-score-fill className="h-full w-full rounded-full origin-left"
            style={{transform: `scaleX(${display / 100})`, backgroundColor: color}} />
        </div>
      )}
    </div>
  );
}
