export default function LanguageSelector({ languages, groups, value, onChange, disabled }) {
  const languageEntries = Object.entries(languages || {});
  const hasGroups = groups && Object.keys(groups).length > 0;

  return (
    <div>
      <label htmlFor="language-select" className="block text-sm font-medium text-slate-700 mb-1">
        Language
      </label>
      <select
        id="language-select"
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-lg border border-slate-300 p-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-300 disabled:opacity-50"
      >
        {languageEntries.length === 0 && <option value="">Loading languages...</option>}

        {hasGroups
          ? Object.entries(groups).map(([groupName, codes]) => (
              <optgroup key={groupName} label={groupName}>
                {codes
                  .filter((code) => languages[code])
                  .map((code) => (
                    <option key={code} value={code}>
                      {languages[code]}
                    </option>
                  ))}
              </optgroup>
            ))
          : languageEntries.map(([code, name]) => (
              <option key={code} value={code}>
                {name}
              </option>
            ))}
      </select>
    </div>
  );
}
