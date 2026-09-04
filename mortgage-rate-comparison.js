let rateCatalog;

function moneyInputValue(id) {
  return Number(document.getElementById(id).value.replace(/\./g, '').replace(',', '.')) || 0;
}

function formatDate(value) {
  return value.split('-').reverse().join('/');
}

function renderRateComparison() {
  const message = document.getElementById('rateComparisonText');
  const list = document.getElementById('rateComparisonOffers');
  if (!rateCatalog) return;
  const amount = moneyInputValue('mortgageAmount');
  const propertyValue = moneyInputValue('mortgagePropertyValue');
  const years = Number(document.getElementById('mortgageYears').value) || 0;
  const enteredTan = Number(document.getElementById('mortgageRate').value.replace(',', '.')) || 0;
  const energy = document.getElementById('mortgageEnergyClass').value;
  list.innerHTML = '';
  if (!amount || !propertyValue || !years || !enteredTan || !energy) {
    message.textContent = 'Inserisci valore immobile e classe energetica per confrontare i requisiti pubblici.';
    return;
  }
  const ltv = amount / propertyValue * 100;
  const matches = rateCatalog.offers.filter(offer => offer.tan < enteredTan && years >= offer.minYears && years <= offer.maxYears && ltv <= offer.maxLtv && (!offer.energyClasses.length || offer.energyClasses.includes(energy)));
  if (!matches.length) {
    message.textContent = `Nessun TAN più basso risulta compatibile nel catalogo verificato il ${formatDate(rateCatalog.updatedAt)}. Questo non esclude offerte personalizzate: chiedi sempre un confronto scritto.`;
    return;
  }
  message.textContent = `Hai inserito TAN ${enteredTan.toLocaleString('it-IT')}%. Nel catalogo ci sono ${matches.length} offerte pubbliche con TAN più basso e requisiti compatibili.`;
  matches.forEach(offer => {
    const item = document.createElement('article');
    item.innerHTML = `<h3>${offer.bank}</h3><p><strong>TAN ${offer.tan.toLocaleString('it-IT')}% · TAEG ${offer.taeg.toLocaleString('it-IT')}%</strong></p><p>${offer.product}. ${offer.conditions}</p><a href="${offer.sourceUrl}" target="_blank" rel="noopener noreferrer">Fonte ufficiale</a>`;
    list.append(item);
  });
}

fetch('/mortgage-rate-catalog.json', { cache: 'no-store' })
  .then(response => response.ok ? response.json() : Promise.reject())
  .then(data => { rateCatalog = data; renderRateComparison(); })
  .catch(() => { document.getElementById('rateComparisonText').textContent = 'Catalogo tassi temporaneamente non disponibile.'; });

['mortgageAmount', 'mortgagePropertyValue', 'mortgageYears', 'mortgageRate', 'mortgageEnergyClass'].forEach(id => document.getElementById(id).addEventListener('input', renderRateComparison));
