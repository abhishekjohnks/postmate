export const money = (value) =>
  new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 2,
  }).format(Number(value || 0));
export const date = (value) =>
  value
    ? new Date(value.length === 10 ? value + 'T12:00:00' : value).toLocaleDateString('en-IN', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
      })
    : '—';
export const localToday = () =>
  new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Kolkata' });

export const receiptFilename = (customerName) => {
  const name = (customerName || 'Customer')
    .replace(/[<>:"/\\|?*\u0000-\u001f\u007f]/g, '')
    .trim()
    .replace(/\.+$/, '')
    .slice(0, 150);
  return `${name || 'Customer'} - Payment Receipt.pdf`;
};
