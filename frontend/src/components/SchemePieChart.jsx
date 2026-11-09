import { useEffect, useId, useState } from 'react';
import { Empty } from './UI';
import { money } from '../utils/format';
import './SchemePieChart.css';

const palette = [
  '#C62828',
  '#FBC02D',
  '#628A73',
  '#DC8065',
  '#627DAB',
  '#A67958',
  '#9B77A6',
  '#408D91',
  '#C78E2D',
  '#8B9C50',
];
const point = (angle) => [120 + 102 * Math.cos(angle), 120 + 102 * Math.sin(angle)];
const percent = (share) => (share < 0.001 ? '<0.1%' : `${(share * 100).toFixed(1)}%`);

export default function SchemePieChart({ items = [], currency = false }) {
  const titleId = useId();
  const [selected, setSelected] = useState(null);
  useEffect(() => setSelected(null), [items, currency]);
  const rows = items
    .map((item) => ({ ...item, value: Number(item.value) }))
    .filter((item) => Number.isFinite(item.value) && item.value > 0);
  const total = rows.reduce((sum, item) => sum + item.value, 0);
  if (!total)
    return (
      <Empty
        text={
          currency
            ? 'Record collections to see your scheme portfolio.'
            : 'Add scheme accounts to see your portfolio.'
        }
      />
    );

  let angle = -Math.PI / 2;
  const slices = rows.map((item, index) => {
    const share = item.value / total;
    const start = point(angle);
    angle += share * Math.PI * 2;
    const end = point(angle);
    return {
      ...item,
      share,
      color: palette[index % palette.length],
      path: `M 120 120 L ${start[0]} ${start[1]} A 102 102 0 ${share > 0.5 ? 1 : 0} 1 ${end[0]} ${end[1]} Z`,
    };
  });
  const valueLabel = (value) =>
    currency ? money(value) : `${value.toLocaleString('en-IN')} account${value === 1 ? '' : 's'}`;
  const focused = slices[selected];

  return (
    <figure className="scheme-pie">
      <div className="scheme-pie-graphic">
        <svg viewBox="0 0 240 240" role="img" aria-labelledby={titleId}>
          <title id={titleId}>
            Scheme portfolio by {currency ? 'collections' : 'account count'}:{' '}
            {slices
              .map((item) => `${item.name}, ${valueLabel(item.value)}, ${percent(item.share)}`)
              .join('; ')}
          </title>
          {slices.map((item, index) => {
            const props = {
              fill: item.color,
              stroke: '#FFFFFF',
              strokeWidth: 2.5,
              opacity: selected === null || selected === index ? 1 : 0.35,
              onMouseEnter: () => setSelected(index),
              onMouseLeave: () => setSelected(null),
            };
            return rows.length === 1 ? (
              <circle key={index} cx={120} cy={120} r={102} {...props}>
                <title>
                  {item.name}: {valueLabel(item.value)} ({percent(item.share)})
                </title>
              </circle>
            ) : (
              <path key={index} d={item.path} {...props}>
                <title>
                  {item.name}: {valueLabel(item.value)} ({percent(item.share)})
                </title>
              </path>
            );
          })}
        </svg>
      </div>
      <figcaption className="scheme-pie-summary" aria-live="polite">
        <strong>{focused ? valueLabel(focused.value) : valueLabel(total)}</strong>
        <span>
          {focused
            ? `${focused.name} · ${percent(focused.share)}`
            : `Across ${rows.length} scheme${rows.length === 1 ? '' : 's'}`}
        </span>
      </figcaption>
      <ul className="scheme-pie-legend">
        {slices.map((item, index) => (
          <li key={index}>
            <button
              type="button"
              className={selected === index ? 'selected' : ''}
              aria-label={`${item.name}: ${valueLabel(item.value)}, ${percent(item.share)}`}
              onMouseEnter={() => setSelected(index)}
              onMouseLeave={() => setSelected(null)}
              onFocus={() => setSelected(index)}
              onBlur={() => setSelected(null)}
              onClick={() => setSelected(selected === index ? null : index)}
            >
              <span className="scheme-pie-dot" style={{ background: item.color }} />
              <span className="scheme-pie-name">
                {item.name}
                <small>{valueLabel(item.value)}</small>
              </span>
              <strong>{percent(item.share)}</strong>
            </button>
          </li>
        ))}
      </ul>
    </figure>
  );
}
