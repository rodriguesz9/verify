import { useEffect, useRef, useState } from "react";

export default function Reveal({ as: Tag = "div", children, className = "", delay = 0, ...props }) {
  const ref = useRef(null);
  const [entered, setEntered] = useState(false);
  useEffect(() => {
    if (!window.IntersectionObserver || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const observer = new IntersectionObserver(([entry]) => {
      if (!entry.isIntersecting) return;
      setEntered(true);
      observer.disconnect();
    }, { threshold: 0.08 });
    observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);
  return <Tag ref={ref} className={`reveal-block ${entered ? "is-revealed" : ""} ${className}`} style={{ "--reveal-delay": `${delay}ms` }} {...props}>{children}</Tag>;
}
