import { useEffect, useRef, useState } from 'react';
import { CalendarDays } from 'lucide-react';
import './DateInput.css';

const display = (value) => (value ? value.split('-').reverse().join('/') : '');

// Keep API values ISO, while presenting an explicit day/month/year text input.
export default function DateInput({ value = '', onChange, min, max, ...props }) {
  const [text, setText] = useState(display(value));
  const textInput = useRef(null);
  useEffect(() => setText(display(value)), [value]);
  function change(event) {
    const input = event.target;
    const next = input.value;
    setText(next);
    let iso = '';
    let error = '';
    if (next) {
      const match = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(next);
      if (match) {
        iso = `${match[3]}-${match[2]}-${match[1]}`;
        const parsed = new Date(`${iso}T00:00:00Z`);
        if (
          match[3] === '0000' ||
          !Number.isFinite(parsed.getTime()) ||
          parsed.toISOString().slice(0, 10) !== iso
        )
          error = 'Enter a valid date as dd/mm/yyyy.';
        else if ((min && iso < min) || (max && iso > max))
          error = `Enter a date${min ? ` on or after ${display(min)}` : ''}${max ? ` on or before ${display(max)}` : ''}.`;
      } else error = 'Enter a valid date as dd/mm/yyyy.';
    }
    textInput.current?.setCustomValidity(error);
    if (!error) onChange?.({ target: { value: iso, name: props.name } });
  }
  return (
    <span className="postmate-date-input">
      <input
        ref={textInput}
        {...props}
        type="text"
        placeholder="dd/mm/yyyy"
        maxLength={10}
        value={text}
        onChange={change}
        onBlur={(e) => e.target.reportValidity()}
      />
      <span className="postmate-date-picker">
        <CalendarDays size={18} aria-hidden="true" />
        <input
          type="date"
          aria-label="Choose date from calendar"
          value={value}
          min={min}
          max={max}
          disabled={props.disabled}
          onChange={(e) => change({ target: { value: display(e.target.value) } })}
        />
      </span>
    </span>
  );
}
