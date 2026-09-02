const mortgageForm = document.getElementById('mortgageCalculator');

function mortgageValue(id) {
  const raw = document.getElementById(id).value.trim();
  const normalized = raw.includes(',') ? raw.replace(/\./g, '').replace(',', '.') : raw.replace(/\./g, '');
  return Math.max(0, Number(normalized) || 0);
}

function euro(value) {
  return value.toLocaleString('it-IT', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 });
}

function calculateMortgage(event) {
  event?.preventDefault();
  const amount = mortgageValue('mortgageAmount');
  const years = mortgageValue('mortgageYears');
  const annualRate = mortgageValue('mortgageRate');
  const error = document.getElementById('mortgageError');
  if (!amount || !years) {
    error.textContent = 'Inserisci importo e durata del mutuo.';
    error.classList.remove('hidden');
    return;
  }
  error.classList.add('hidden');
  const months = years * 12;
  const monthlyRate = annualRate / 100 / 12;
  const monthly = monthlyRate ? amount * monthlyRate / (1 - Math.pow(1 + monthlyRate, -months)) : amount / months;
  const installments = monthly * months;
  const interest = installments - amount;
  const upfront = mortgageValue('mortgageDownPayment') + mortgageValue('mortgageFees');
  document.getElementById('mortgageMonthly').textContent = euro(monthly);
  document.getElementById('mortgageInterest').textContent = euro(interest);
  document.getElementById('mortgageInstallments').textContent = euro(installments);
  document.getElementById('mortgageUpfront').textContent = euro(upfront);
  document.getElementById('mortgageFirstYear').textContent = euro(upfront + monthly * Math.min(12, months));
  document.getElementById('mortgageExplanation').textContent = `Su ${euro(amount)} in ${years} anni al TAN del ${annualRate.toLocaleString('it-IT', { maximumFractionDigits: 2 })}%, gli interessi stimati sono ${euro(interest)}. Verifica sempre il piano di ammortamento e le condizioni dell'offerta.`;
  if (event?.type === 'submit') {
    fetch('/api/activity', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ event: 'mortgage_calculation' }), keepalive: true }).catch(() => {});
  }
}

mortgageForm.addEventListener('submit', calculateMortgage);
mortgageForm.addEventListener('input', calculateMortgage);
function formatMortgageThousands(input) {
  const digits = input.value.replace(/\D/g, '');
  input.value = digits ? digits.replace(/\B(?=(\d{3})+(?!\d))/g, '.') : '';
}
['mortgageAmount', 'mortgageDownPayment', 'mortgageFees'].forEach(id => {
  const input = document.getElementById(id);
  input.addEventListener('input', () => formatMortgageThousands(input));
  input.addEventListener('blur', () => formatMortgageThousands(input));
  formatMortgageThousands(input);
});
calculateMortgage();
