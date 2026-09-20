export default function TranslateToggle({ checked, onChange, disabled }) {
  return (
    <label className="flex items-start gap-2 text-sm text-slate-700">
      <input
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
        className="mt-0.5 h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-300 disabled:opacity-50"
      />
      <span>
        Translate my text into the selected language before generating speech
        <span className="block text-xs text-slate-400">
          Useful if you typed in one language but want the audio spoken in another.
        </span>
      </span>
    </label>
  );
}
