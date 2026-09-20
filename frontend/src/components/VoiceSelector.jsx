export default function VoiceSelector({ voices, value, onChange, disabled }) {
  const list = voices || [];

  return (
    <div>
      <label htmlFor="voice-select" className="block text-sm font-medium text-slate-700 mb-1">
        Voice
      </label>
      <select
        id="voice-select"
        value={value}
        disabled={disabled || list.length === 0}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-lg border border-slate-300 p-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-300 disabled:opacity-50"
      >
        {list.length === 0 && <option value="">No voices available</option>}
        {list.map((v) => (
          <option key={v.id} value={v.id}>
            {v.label}
          </option>
        ))}
      </select>
    </div>
  );
}
