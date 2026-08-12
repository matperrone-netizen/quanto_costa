function money(value) {
  return `${Math.round(value).toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.')} €`;
}

const estimates = {
  city: { insurance: 700, tax: 150, maintenance: 260, tires: 110, petrol: 5.5, diesel: 4.5, hybrid: 4.2, electric: 15.5 },
  compact: { insurance: 800, tax: 190, maintenance: 340, tires: 150, petrol: 5.8, diesel: 4.6, hybrid: 4.4, electric: 17.5 },
  suv: { insurance: 950, tax: 270, maintenance: 450, tires: 210, petrol: 6.2, diesel: 5.1, hybrid: 5.1, electric: 19.5 },
  large: { insurance: 1200, tax: 380, maintenance: 650, tires: 290, petrol: 8.2, diesel: 6.7, hybrid: 6.4, electric: 22 }
};
const energyPrice = { petrol: 1.82, diesel: 1.72, hybrid: 1.78, electric: 0.33 };
const label = { insurance: 'Assicurazione', tax: 'Bollo', maintenance: 'Manutenzione', tires: 'Gomme', fuel: 'Carburante / ricarica', parking: 'Parcheggio', payment: 'Rata o canone' };
let comparisonOffers = null;
let comparisonNames = { a: 'Offerta A', b: 'Offerta B' };
let lastShareText = '';
let lastChecklistText = '';

function trackActivity(eventName) {
  fetch('/api/activity', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ event: eventName }),
    keepalive: true
  }).catch(() => {});
}

let staticOffers = [];
const offersReady = fetch('offers.json', { cache: 'no-cache' })
  .then(response => response.ok ? response.json() : [])
  .then(catalog => {
    staticOffers = Array.isArray(catalog) ? catalog : (Array.isArray(catalog.offers) ? catalog.offers : []);
    populateModelSuggestions();
  })
  .catch(() => { staticOffers = []; });

function value(id) {
  const raw = document.getElementById(id).value;
  return Math.max(0, Number(String(raw).replace(/\./g, '').replace(',', '.')) || 0);
}
function proposalType() { return document.querySelector('input[name="proposalType"]:checked').value; }
function selectedCosts(selector) { return [...document.querySelectorAll(`${selector} input:checked`)].map(input => input.value); }
function normalizeCatalogText(value) {
  return String(value || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^a-z0-9]+/g, ' ').trim();
}
function offerSearchTerms(offer) {
  return [...(offer.aliases || []), `${offer.brand || ''} ${offer.model || ''}`, ...(offer.match || [])]
    .map(normalizeCatalogText)
    .filter(term => term.length > 1);
}
function populateModelSuggestions() {
  const list = document.getElementById('catalogModels');
  const models = [...new Set(staticOffers.map(offer => `${offer.brand || ''} ${offer.model || ''}`.trim()).filter(Boolean))].sort();
  list.replaceChildren(...models.map(model => {
    const option = document.createElement('option');
    option.value = model;
    return option;
  }));
}
function findStaticOffers(carModel, contractKm = null) {
  const normalized = normalizeCatalogText(carModel);
  if (!normalized) return [];
  return staticOffers
    .filter(offer => (!contractKm || offer.contractKm === contractKm) && offerSearchTerms(offer).some(term => normalized.includes(term)))
    .sort((first, second) => {
      const firstScore = Math.max(...offerSearchTerms(first).filter(term => normalized.includes(term)).map(term => term.length));
      const secondScore = Math.max(...offerSearchTerms(second).filter(term => normalized.includes(term)).map(term => term.length));
      return secondScore - firstScore || String(second.checkedAtISO).localeCompare(String(first.checkedAtISO));
    });
}
function findStaticOffer(carModel, contractKm = null) {
  return findStaticOffers(carModel, contractKm)[0] || null;
}

function estimateOffer({ type, payment, months, downPayment, finalPayment, included, endChoice = 'undecided' }, profile) {
  const base = estimates[profile.segment];
  const fuelMonthly = (profile.km / 100 * base[profile.fuel] * energyPrice[profile.fuel]) / 12;
  const costs = { payment, fuel: fuelMonthly, parking: profile.parking };
  ['insurance', 'tax', 'maintenance', 'tires'].forEach(item => {
    if (type === 'finance' || !included.includes(item)) costs[item] = base[item] / 12;
  });
  const monthlyTotal = Object.values(costs).reduce((sum, item) => sum + item, 0);
  const baseContractTotal = payment * months + downPayment;
  const finalIncluded = type !== 'finance' || endChoice !== 'return';
  const contractTotal = baseContractTotal + (finalIncluded ? finalPayment : 0);
  const totalOutlay = contractTotal + (monthlyTotal - payment) * months;
  return { type, payment, months, downPayment, finalPayment, endChoice, finalIncluded, baseContractTotal, costs, monthlyTotal, contractTotal, totalOutlay, fuelMonthly, fuelConsumption: base[profile.fuel], fuelPrice: energyPrice[profile.fuel], fuel: profile.fuel, km: profile.km };
}

function getOfferA(profile) {
  const type = proposalType();
  return estimateOffer({
    type, payment: value('monthlyPayment'), months: Math.max(1, value('duration')),
    downPayment: value('downPayment'), finalPayment: type === 'finance' ? value('finalPayment') : 0,
    endChoice: type === 'finance' ? document.querySelector('input[name="endChoice"]:checked').value : 'return',
    included: selectedCosts('#includedCosts')
  }, profile);
}

function getOfferB(profile) {
  const type = document.getElementById('proposalTypeB').value;
  return estimateOffer({
    type, payment: value('monthlyPaymentB'), months: Math.max(1, value('durationB')),
    downPayment: value('downPaymentB'), finalPayment: type === 'finance' ? value('finalPaymentB') : 0,
    endChoice: type === 'finance' ? document.querySelector('input[name="endChoiceB"]:checked').value : 'return',
    included: selectedCosts('#includedCostsB')
  }, profile);
}

function renderComparison(a, b, staticOffer = null) {
  comparisonOffers = { a, b };
  comparisonNames = { a: 'Offerta A', b: staticOffer ? staticOffer.title : 'Offerta B' };
  document.getElementById('compareBLabel').innerHTML = `${staticOffer ? 'Alternativa trovata' : 'Offerta B'} <b>Apri dettagli</b>`;
  const source = document.getElementById('catalogSource');
  if (staticOffer) {
    source.innerHTML = `Alternativa dal catalogo statico: <a href="${staticOffer.sourceUrl}" target="_blank" rel="noreferrer">${staticOffer.sourceName}</a>, consultata il ${staticOffer.checkedAt}. ${staticOffer.conditions}`;
    source.classList.remove('hidden');
  } else {
    source.classList.add('hidden');
  }
  const priority = document.getElementById('priority').value;
  const setup = {
    monthly: { title: 'costo mensile di guida', key: 'monthlyTotal', suffix: 'al mese' },
    upfront: { title: 'anticipo richiesto', key: 'downPayment', suffix: 'subito' },
    total: { title: 'esborso totale previsto', key: 'totalOutlay', suffix: 'nel periodo' }
  }[priority];
  const aMetric = a[setup.key];
  const bMetric = b[setup.key];
  document.getElementById('compareA').textContent = `${money(aMetric)} ${setup.suffix}`;
  document.getElementById('compareB').textContent = `${money(bMetric)} ${setup.suffix}`;
  document.getElementById('compareADetail').textContent = `${a.type === 'finance' ? 'Anticipo' : 'Versamento iniziale'} ${money(a.downPayment)} · pagamenti contratto ${money(a.contractTotal)}`;
  document.getElementById('compareBDetail').textContent = `${b.type === 'finance' ? 'Anticipo' : 'Versamento iniziale'} ${money(b.downPayment)} · pagamenti contratto ${money(b.contractTotal)}`;
  const difference = Math.abs(aMetric - bMetric);
  const verdict = document.getElementById('comparisonVerdict');
  if (difference < 1) {
    verdict.textContent = `Con la priorità scelta, le due offerte sono equivalenti. Per decidere guarda i servizi inclusi, i km contrattuali e la maxi rata.`;
  } else {
    const winner = aMetric < bMetric ? 'A' : 'B';
    verdict.innerHTML = `Se per te conta <strong>${setup.title}</strong>, l’offerta <strong>${winner}</strong> richiede ${money(difference)} in meno ${setup.suffix}.`;
  }
  const metricWinner = (key) => a[key] === b[key] ? null : (a[key] < b[key] ? 'A' : 'B');
  const monthlyWinner = metricWinner('monthlyTotal');
  const upfrontWinner = metricWinner('downPayment');
  const totalWinner = metricWinner('totalOutlay');
  const tradeoff = document.getElementById('comparisonTradeoff');
  if (!monthlyWinner && !upfrontWinner && !totalWinner) {
    tradeoff.innerHTML = `<strong>Le due offerte sono molto simili:</strong> guarda i servizi inclusi e le condizioni finali per scegliere.`;
  } else if (monthlyWinner && monthlyWinner === upfrontWinner && monthlyWinner === totalWinner) {
    tradeoff.innerHTML = `<strong>L’offerta ${monthlyWinner} è più leggera su tutti i fronti:</strong> mese per mese, liquidità iniziale ed esborso stimato.`;
  } else {
    const parts = [];
    if (monthlyWinner) parts.push(`l’offerta <strong>${monthlyWinner}</strong> pesa meno ogni mese`);
    if (upfrontWinner) parts.push(`l’offerta <strong>${upfrontWinner}</strong> richiede meno liquidità subito`);
    if (totalWinner) parts.push(`l’offerta <strong>${totalWinner}</strong> ha l’esborso stimato minore`);
    tradeoff.innerHTML = `<strong>Il compromesso reale:</strong> ${parts.join('; ')}.`;
  }
}

function showOfferDetails(which) {
  if (!comparisonOffers) return;
  const offer = comparisonOffers[which];
  const details = document.getElementById('offerDetails');
  if (details.dataset.open === which) {
    details.classList.add('hidden');
    details.dataset.open = '';
    document.querySelectorAll('.compare-card').forEach(card => card.classList.remove('active'));
    return;
  }
  const name = comparisonNames[which];
  const rows = [
    ['Rata o canone', money(offer.payment) + '/mese'],
    ['Numero di rate', String(offer.months)],
    [offer.type === 'finance' ? 'Anticipo' : 'Versamento iniziale', offer.downPayment ? money(offer.downPayment) : 'Nessuno'],
    ['Maxi rata finale', offer.finalPayment ? money(offer.finalPayment) : 'Nessuna'],
    ['Costo mensile di guida', money(offer.monthlyTotal)],
    ['Pagamenti considerati nel confronto', money(offer.contractTotal)]
  ];
  const composition = Object.entries(offer.costs)
    .filter(([, amount]) => amount > 0)
    .sort((a, b) => b[1] - a[1]);
  details.innerHTML = `<h4>${name}: dettaglio dell'impegno</h4>${rows.map(([title, amount]) => `<div class="offer-detail-row"><span>${title}</span><strong>${amount}</strong></div>`).join('')}<h4>Da cosa è composto</h4>${composition.map(([key, amount]) => `<div class="offer-detail-row"><span>${label[key]}</span><strong>${money(amount)}/mese</strong></div>`).join('')}<p>${offer.type === 'finance' ? 'Se riscatti l’auto, valuta anche quanto potrebbe valere alla fine del contratto.' : 'Nel noleggio verifica sempre km inclusi, franchigie e condizioni di restituzione.'}</p>`;
  details.classList.remove('hidden');
  details.dataset.open = which;
  document.querySelectorAll('.compare-card').forEach(card => card.classList.toggle('active', card.dataset.offer === which));
}

async function calculate() {
  await offersReady;
  document.querySelectorAll('[data-money-input]').forEach(formatThousands);
  const profile = {
    km: value('annualKm'), fuel: document.getElementById('fuel').value,
    segment: document.getElementById('segment').value, parking: value('parking')
  };
  const carModel = document.getElementById('carModel').value.trim();
  const offer = getOfferA(profile);
  const hasManualOfferB = document.getElementById('hasOfferB').checked;
  const catalogOfferForModel = hasManualOfferB ? null : findStaticOffer(carModel);
  const staticOffer = hasManualOfferB ? null : findStaticOffer(carModel, profile.km);
  const offerB = hasManualOfferB ? getOfferB(profile) : staticOffer ? estimateOffer(staticOffer, { ...profile, ...staticOffer.profile }) : null;
  trackActivity('calculation');
  if (offerB) trackActivity('comparison');
  document.getElementById('quotedPayment').textContent = money(offer.payment);
  document.getElementById('realMonthly').textContent = money(offer.monthlyTotal);
  document.getElementById('monthlyDriving').textContent = money(offer.monthlyTotal);
  document.getElementById('downPaymentResultLabel').textContent = offer.type === 'finance' ? 'Anticipo da versare oggi' : 'Versamento iniziale separato';
  document.getElementById('downPaymentResult').textContent = offer.downPayment ? money(offer.downPayment) : 'Nessuno';
  document.getElementById('finalPaymentResult').textContent = offer.finalPayment ? money(offer.finalPayment) : 'Nessuna';
  const extra = offer.monthlyTotal - offer.payment;
  const subject = carModel ? `Per ${carModel}, ` : '';
  document.getElementById('resultExplanation').textContent = `${subject}oltre alla ${offer.type === 'finance' ? 'rata' : 'canone'} di ${money(offer.payment)}, stimiamo ${money(extra)} al mese per usarla e mantenerla. Anticipo e maxi rata non sono inclusi qui.`;
  const unit = offer.fuel === 'electric' ? 'kWh' : 'L';
  const energyName = offer.fuel === 'electric' ? 'ricarica' : 'carburante';
  const energyPrice = `${offer.fuelPrice.toFixed(2).replace('.', ',')} €`;
  document.getElementById('fuelFormula').textContent = `Calcolo ${energyName}: ${offer.km.toLocaleString('it-IT')} km/anno × ${String(offer.fuelConsumption).replace('.', ',')} ${unit}/100 km × ${energyPrice}/${unit}, diviso 12 = circa ${money(offer.fuelMonthly)}/mese.`;
  lastShareText = `${subject || 'Per la mia auto, '}la stima di Costo Vero è ${money(offer.monthlyTotal)} al mese per guidarla. La rata è ${money(offer.payment)}; anticipo e maxi rata restano separati. Fai la tua stima:`;
  const baseQuestions = offer.type === 'finance'
    ? [
      `Qual è il TAEG effettivo e quali spese sono comprese oltre alla rata di ${money(offer.payment)}?`,
      offer.finalPayment ? `Quali opzioni ho per la maxi rata di ${money(offer.finalPayment)} e quali condizioni si applicano se restituisco l'auto?` : 'Cosa succede esattamente alla fine del finanziamento?',
      'Quali sconti sono già inclusi nel preventivo e quali richiedono rottamazione, finanziamento o altri requisiti?',
      'Quali costi di assicurazione, bollo, manutenzione e gomme restano a mio carico?'
    ]
    : [
      `Il canone di ${money(offer.payment)} include RCA, furto/incendio, Kasko, bollo, manutenzione e gomme?`,
      `Quanti km sono inclusi e quanto costa ogni km in più rispetto ai ${offer.km.toLocaleString('it-IT')} km/anno che prevedo?`,
      'Quali franchigie, danni alla riconsegna e penali di uscita anticipata devo considerare?',
      'Quali sconti sono già inclusi nel preventivo e quali richiedono rottamazione, finanziamento o altri requisiti?'
    ];
  lastChecklistText = `Domande da fare prima di firmare${carModel ? ` — ${carModel}` : ''}\n\n${baseQuestions.map((question, index) => `${index + 1}. ${question}`).join('\n')}\n\nChecklist generata da Costo Vero: ${window.location.href}`;
  const decision = document.getElementById('decisionNote');
  if (offer.type === 'finance') {
    const finalText = offer.finalPayment ? ` Alla scadenza c’è una maxi rata di <strong>${money(offer.finalPayment)}</strong>.` : '';
    if (offer.endChoice === 'keep') {
      decision.innerHTML = `<strong>Scenario: tieni l'auto.</strong> La maxi rata è inclusa nel confronto perché la pagherai per riscattare il veicolo.${finalText} I pagamenti considerati sono <strong>${money(offer.contractTotal)}</strong>, prima dei costi di utilizzo e senza stimare il valore futuro dell’auto.`;
    } else if (offer.endChoice === 'return') {
      decision.innerHTML = `<strong>Scenario: restituisci o cambi l'auto.</strong> La maxi rata non è inclusa nel confronto, perché non prevedi il riscatto.${finalText} Verifica però km contrattuali, stato del veicolo e possibili addebiti alla riconsegna.`;
    } else {
      decision.innerHTML = `<strong>Scenario prudente.</strong> Non avendo scelto cosa fare alla scadenza, il confronto include la maxi rata di <strong>${money(offer.finalPayment)}</strong>. Se restituirai l’auto rispettando le condizioni, potresti non doverla pagare.`;
    }
  } else {
    decision.innerHTML = `<strong>Come leggere questa offerta.</strong> Il canone mensile non include il versamento iniziale di <strong>${money(offer.downPayment)}</strong>, che richiede liquidità subito. I pagamenti previsti dal contratto sono <strong>${money(offer.contractTotal)}</strong>; a fine noleggio non avrai un'auto da rivendere.`;
  }
  const rows = Object.entries(offer.costs).filter(([, amount]) => amount > 0).sort((a, b) => b[1] - a[1]);
  const max = Math.max(...rows.map(([, amount]) => amount));
  document.getElementById('breakdownItems').innerHTML = rows.map(([key, amount]) => `<div class="breakdown-row"><span>${label[key]}</span><i class="bar" style="width:${Math.max(4, amount / max * 130)}px"></i><strong>${money(amount)}/mese</strong></div>`).join('');
  const comparisonResult = document.getElementById('comparisonResult');
  comparisonResult.classList.toggle('hidden', !offerB);
  document.getElementById('mainBreakdown').classList.toggle('hidden', Boolean(offerB));
  if (offerB) {
    document.getElementById('offerDetails').classList.add('hidden');
    document.getElementById('offerDetails').dataset.open = '';
    document.querySelectorAll('.compare-card').forEach(card => card.classList.remove('active'));
    renderComparison(offer, offerB, staticOffer);
  } else if (!hasManualOfferB) {
    document.getElementById('noOfferBMessage').textContent = catalogOfferForModel ? `Abbiamo un’offerta verificata per “${carModel}”, ma con ${catalogOfferForModel.contractKm.toLocaleString('it-IT')} km/anno. Seleziona lo stesso chilometraggio per confrontarla correttamente.` : carModel ? `Non abbiamo ancora un’alternativa verificata per “${carModel}” nel catalogo statico. Non mostriamo un preventivo inventato.` : 'Inserisci marca e modello per cercare un’alternativa nel catalogo statico.';
  }
  const results = document.getElementById('results');
  results.classList.remove('hidden');
  results.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function updateProposalVisibility() {
  const isFinance = proposalType() === 'finance';
  document.querySelectorAll('.choice-card').forEach(card => card.classList.toggle('selected', card.querySelector('input').checked));
  document.querySelectorAll('.finance-only').forEach(el => el.classList.toggle('hidden', !isFinance));
  document.getElementById('includedCosts').classList.toggle('hidden', isFinance);
  document.getElementById('downPaymentLabel').childNodes[0].textContent = isFinance ? 'Anticipo ' : 'Versamento iniziale ';
}
function updateSecondProposalVisibility() {
  const isFinance = document.getElementById('proposalTypeB').value === 'finance';
  document.getElementById('finalPaymentBField').classList.toggle('hidden', !isFinance);
  document.getElementById('includedCostsB').classList.toggle('hidden', isFinance);
  document.getElementById('endChoiceBField').classList.toggle('hidden', !isFinance);
  document.getElementById('downPaymentBLabel').childNodes[0].textContent = isFinance ? 'Anticipo ' : 'Versamento iniziale ';
}
function formatThousands(input) {
  const digits = input.value.replace(/\D/g, '');
  input.value = digits ? digits.replace(/\B(?=(\d{3})+(?!\d))/g, '.') : '';
}
function toggleOfferB() {
  const show = document.getElementById('hasOfferB').checked;
  document.getElementById('offerBFields').classList.toggle('hidden', !show);
  document.getElementById('noOfferBMessage').classList.toggle('hidden', show);
}

async function shareResult() {
  if (!lastShareText) return;
  const button = document.getElementById('shareResult');
  const shareData = { title: 'La mia stima auto | Costo Vero', text: lastShareText, url: window.location.href };
  try {
    if (navigator.share) {
      await navigator.share(shareData);
      trackActivity('share');
      return;
    }
    await navigator.clipboard.writeText(`${lastShareText} ${window.location.href}`);
    trackActivity('share');
    const original = button.innerHTML;
    button.textContent = 'Testo e link copiati';
    window.setTimeout(() => { button.innerHTML = original; }, 2200);
  } catch (error) {
    if (error.name !== 'AbortError') {
      button.textContent = 'Non riesco a condividere ora';
      window.setTimeout(() => { button.innerHTML = 'Condividi questa stima <span aria-hidden="true">↗</span>'; }, 2200);
    }
  }
}

async function copyQuestions() {
  if (!lastChecklistText) return;
  const button = document.getElementById('copyQuestions');
  try {
    await navigator.clipboard.writeText(lastChecklistText);
    trackActivity('checklist');
    const original = button.innerHTML;
    button.textContent = 'Domande copiate: inviale o portale in concessionaria';
    window.setTimeout(() => { button.innerHTML = original; }, 2800);
  } catch {
    button.textContent = 'Non riesco a copiare ora';
    window.setTimeout(() => { button.innerHTML = 'Copia le domande da fare prima di firmare <span aria-hidden="true">✓</span>'; }, 2200);
  }
}

document.querySelectorAll('input[name="proposalType"]').forEach(input => input.addEventListener('change', updateProposalVisibility));
document.getElementById('proposalTypeB').addEventListener('change', updateSecondProposalVisibility);
['downPayment', 'finalPayment', 'downPaymentB', 'finalPaymentB'].forEach(id => {
  const input = document.getElementById(id);
  input.dataset.moneyInput = 'true';
  input.addEventListener('input', () => formatThousands(input));
  input.addEventListener('change', () => formatThousands(input));
  input.addEventListener('blur', () => formatThousands(input));
  formatThousands(input);
});
document.getElementById('hasOfferB').addEventListener('change', toggleOfferB);
document.querySelectorAll('.compare-card').forEach(card => card.addEventListener('click', () => showOfferDetails(card.dataset.offer)));
document.getElementById('calculate').addEventListener('click', calculate);
document.getElementById('toggleDetails').addEventListener('click', () => document.querySelector('.second-step').scrollIntoView({ behavior: 'smooth', block: 'start' }));
document.getElementById('shareResult').addEventListener('click', shareResult);
document.getElementById('copyQuestions').addEventListener('click', copyQuestions);
updateProposalVisibility();
updateSecondProposalVisibility();
toggleOfferB();
