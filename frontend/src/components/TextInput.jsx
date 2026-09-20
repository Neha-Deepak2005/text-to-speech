export default function TextInput({ text, onChange, maxLength, disabled }) {
  const charCount = text.length;
  const wordCount = text.trim().length === 0 ? 0 : text.trim().split(/\s+/).length;
  const overLimit = charCount > maxLength;

  return (
    <div>
      <label htmlFor="tts-text" className="block text-sm font-medium text-slate-700 mb-1">
        Enter your text
      </label>
      <textarea
        id="tts-text"
        value={text}
        onChange={(e) => onChange(e.target.value)}
        rows={6}
        disabled={disabled}
        placeholder="Type or paste the text you want to convert to speech..."
        className={`w-full rounded-lg border p-3 text-sm shadow-sm focus:outline-none focus:ring-2 resize-y disabled:opacity-60 disabled:bg-slate-50 ${
          overLimit
            ? "border-red-400 focus:ring-red-300"
            : "border-slate-300 focus:ring-indigo-300"
        }`}
      />
      <div className="mt-1 flex flex-wrap justify-between text-xs text-slate-500">
        <span>Words: {wordCount}</span>
        <span className={overLimit ? "text-red-600 font-semibold" : ""}>
          Characters: {charCount} / {maxLength}
        </span>
      </div>
    </div>
  );
}
