const OPTIONS = [
  { value: "MALE", label: "Male", symbol: "♂" },
  { value: "FEMALE", label: "Female", symbol: "♀" },
];

export default function GenderSelector({ value, onChange }) {
  return (
    <fieldset className="gender-fieldset">
      <legend>Gender <span aria-hidden="true">*</span></legend>
      <div className="gender-options">
        {OPTIONS.map((option) => (
          <label className={`gender-option${value === option.value ? " selected" : ""}`} key={option.value}>
            <input
              type="radio"
              name="gender"
              value={option.value}
              checked={value === option.value}
              onChange={() => onChange(option.value)}
              required
            />
            <span className="gender-symbol" aria-hidden="true">{option.symbol}</span>
            <span>{option.label}</span>
            <span className="gender-check" aria-hidden="true">{value === option.value ? "✓" : ""}</span>
          </label>
        ))}
      </div>
      <small className="gender-help">Choose the option that best describes you.</small>
    </fieldset>
  );
}
