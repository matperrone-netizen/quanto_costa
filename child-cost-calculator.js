const childForm = document.getElementById('childCostCalculator');

function childValue(id) {
  return Math.max(0, Number(document.getElementById(id).value.replace(',', '.')) || 0);
}

function childEuro(value) {
  return value.toLocaleString('it-IT', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 });
}

function calculateChildCost(event) {
  event?.preventDefault();
  const initial = childValue('childInitial');
  const monthly = childValue('childFood') + childValue('childCare') + childValue('childHealth') + childValue('childOther');
  const annual = monthly * 12;
  document.getElementById('childMonthly').textContent = childEuro(monthly);
  document.getElementById('childMonthlySummary').textContent = childEuro(monthly);
  document.getElementById('childAnnual').textContent = childEuro(annual);
  document.getElementById('childFirstYear').textContent = childEuro(initial + annual);
  document.getElementById('childInitialResult').textContent = childEuro(initial);
  document.getElementById('childExplanation').textContent = `Questa è una proiezione basata solo sulle voci che hai inserito: ${childEuro(monthly)} al mese, più ${childEuro(initial)} una tantum. Aggiorna i campi quando un costo è confermato.`;
  if (event?.type === 'submit') {
    fetch('/api/activity', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ event: 'child_cost_calculation' }), keepalive: true }).catch(() => {});
  }
}

childForm.addEventListener('submit', calculateChildCost);
childForm.addEventListener('input', calculateChildCost);
calculateChildCost();
