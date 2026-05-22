import { useRef, useState } from "react";

export default function Dropzone({ onFile }) {
  const inputRef  = useRef(null);
  const [drag, setDrag]       = useState(false);
  const [preview, setPreview] = useState(null);
  const [fileName, setFileName] = useState("");
  const [fileType, setFileType] = useState("");

  const accept = "image/*,video/*,audio/*";

  const handleFile = (file) => {
    if (!file) return;
    setFileName(file.name);
    setFileType(file.type);
    
    if (file.type.startsWith("image/")) {
      const reader = new FileReader();
      reader.onload = (e) => setPreview(e.target.result);
      reader.readAsDataURL(file);
    } else {
      setPreview(null);
    }
    
    onFile(file);
  };

  const onDrop = (e) => {
    e.preventDefault();
    setDrag(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  };

  return (
    <div
      onClick={() => inputRef.current?.click()}
      onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
      onDragLeave={() => setDrag(false)}
      onDrop={onDrop}
      className="rounded-xl border transition-all cursor-pointer flex flex-col items-center justify-center gap-3 p-8 relative overflow-hidden"
      style={{
        borderColor:  drag ? "#00D4FF" : "#132435",
        borderStyle:  "dashed",
        background:   drag ? "rgba(0,212,255,.06)" : "#0A1520",
        minHeight:    160,
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => handleFile(e.target.files[0])}
      />

      {preview ? (
        <img
          src={preview}
          alt="preview"
          className="max-h-32 rounded-lg object-contain opacity-80"
        />
      ) : fileType ? (
        <div className="flex flex-col items-center gap-2">
          <span className="text-3xl" style={{ color: "#00D4FF" }}>
            {fileType.startsWith("video/") ? "🎬" : "🎵"}
          </span>
          <span className="font-mono text-[11px] text-text">{fileName}</span>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-2 text-center">
          <span className="text-3xl" style={{ color: "#1A3A50" }}>⬡</span>
          <span className="font-mono text-[11px] tracking-widest text-muted">
            ENVIAR IMAGEM, VÍDEO OU ÁUDIO
          </span>
          <span className="font-mono text-[10px]" style={{ color: "#1A3A50" }}>
            JPG · PNG · MP4 · MP3 · WAV · etc
          </span>
        </div>
      )}
    </div>
  );
}
