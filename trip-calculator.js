const tripForm = document.getElementById('tripCalculator');

function tripNumber(id) {
  return Math.max(0, Number(document.getElementById(id).value.replace(',', '.')) || 0);
}

function formatTripNumber(value, digits = 2) {
  return value.toLocaleString('it-IT', { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

function calculateTrip(event) {
  event?.preventDefault();
  if (!tripForm.checkValidity()) return;
  const multiplier = document.getElementById('tripReturn').checked ? 2 : 1;
  const distance = tripNumber('tripKm') * multiplier;
  const liters = distance * tripNumber('tripConsumption') / 100;
  const fuelCost = liters * tripNumber('tripPrice');
  const toll = tripNumber('tripToll');
  const costPerKm = distance ? fuelCost / distance : 0;
  document.getElementById('tripFuelCost').textContent = `${formatTripNumber(fuelCost)} €`;
  document.getElementById('tripTotalKm').textContent = `${formatTripNumber(distance, distance % 1 ? 1 : 0)} km`;
  document.getElementById('tripLiters').textContent = `${formatTripNumber(liters, 1)} l`;
  document.getElementById('tripCostKm').textContent = `${formatTripNumber(costPerKm)} €/km`;
  document.getElementById('tripTotal').innerHTML = `Totale viaggio con eventuale pedaggio: <strong>${formatTripNumber(fuelCost + toll)} €</strong>`;
  if (event?.type === 'submit') {
    fetch('/api/activity', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ event: 'fuel_calculation' }),
      keepalive: true
    }).catch(() => {});
  }
}

tripForm.addEventListener('submit', calculateTrip);
tripForm.addEventListener('input', calculateTrip);
