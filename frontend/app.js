import { translations } from '/i18n.js';

const state = { token: localStorage.getItem('astra_token') || '', user: null, locale: localStorage.getItem('astra_locale') || 'en', mode: 'login', chart: null, currentProfileId: null, placeChoice: null, currentTab: 'overview' };
const $ = (id) => document.getElementById(id);
const t = (key) => translations[state.locale]?.[key] || translations.en[key] || key;
const authHeaders = () => state.token ? { Authorization: `Bearer ${state.token}` } : {};
const esc = (value) => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));

async function api(path, options = {}) {
  const response = await fetch(path, { ...options, headers: { 'Content-Type': 'application/json', ...authHeaders(), ...(options.headers || {}) } });
  const type = response.headers.get('content-type') || '';
  const body = type.includes('application/json') ? await response.json() : await response.text();
  if (!response.ok) throw new Error(body?.detail || body?.message || `HTTP ${response.status}`);
  return body;
}
function toast(message) { const node=$('toast'); node.textContent=message; node.classList.add('show'); clearTimeout(toast.timer); toast.timer=setTimeout(()=>node.classList.remove('show'),3200); }
function applyLocale() {
  document.documentElement.lang = state.locale;
  $('localeSelect').value = state.locale;
  $('reportLocale').value = state.locale;
  document.querySelectorAll('[data-i18n]').forEach(node => {
    const value = t(node.dataset.i18n);
    if (node.dataset.i18n === 'heroTitle') node.innerHTML = value;
    else node.textContent = value;
  });
  $('authSubmit').textContent = state.mode === 'login' ? t('signIn') : t('createAccount');
  if (state.chart) renderChart();
}
function showAuth(isAuthenticated) {
  $('authPanel').hidden = isAuthenticated;
  $('workspace').hidden = !isAuthenticated;
  $('logoutButton').hidden = !isAuthenticated;
  $('upgradeButton').hidden = !isAuthenticated;
  $('accountButton').textContent = state.user?.email?.slice(0,1).toUpperCase() || 'G';
}
function openTab(tab) {
  state.currentTab = tab;
  document.querySelectorAll('.nav-item').forEach(node => node.classList.toggle('active', node.dataset.tab === tab || (tab === 'chart' && node.dataset.tab === 'birth')));
  ['overview','birth','chart','life','periods','divisional','saved'].forEach(name => { const node=$(`${name}Panel`); if (node) node.hidden = name !== tab; });
  const titles = { overview:t('overview'), birth:t('birthChart'), chart:t('birthChart'), life:t('lifeAnalysis'), periods:t('periods'), divisional:t('divisional'), saved:t('savedCharts') };
  $('pageTitle').textContent = titles[tab] || t('overview');
  if (tab === 'saved') loadSavedCharts();
  if (tab === 'overview') loadRecentCharts();
  if (['life','periods','divisional'].includes(tab) && !state.chart) {
    const target = tab === 'life' ? $('lifeReports') : tab === 'periods' ? $('periodReport') : $('vargaReport');
    target.innerHTML = `<div class="empty-state">${esc(t('noCharts'))}</div>`;
  }
}
function authSuccess(data) {
  state.token=data.access_token; state.user=data.user;
  localStorage.setItem('astra_token',state.token);
  showAuth(true); applyLocale(); openTab('overview');
  loadRecentCharts();
}
$('showLogin').addEventListener('click',()=>setAuthMode('login'));
$('showRegister').addEventListener('click',()=>setAuthMode('register'));
function setAuthMode(mode) { state.mode=mode; $('showLogin').classList.toggle('selected',mode==='login'); $('showRegister').classList.toggle('selected',mode==='register'); $('authSubmit').textContent=mode==='login'?t('signIn'):t('createAccount'); $('passwordInput').autocomplete=mode==='login'?'current-password':'new-password'; }
$('authForm').addEventListener('submit', async event => {
  event.preventDefault();
  const email=$('emailInput').value.trim(); const password=$('passwordInput').value;
  $('authMessage').textContent=''; $('authSubmit').disabled=true;
  try {
    const data=await api(`/api/auth/${state.mode==='login'?'login':'register'}`,{method:'POST',body:JSON.stringify({email,password,locale:state.locale})});
    authSuccess(data); toast(state.mode==='login'?t('loginSuccess'):t('registerSuccess'));
  } catch (error) { $('authMessage').textContent=error.message || t('authFailed'); }
  finally { $('authSubmit').disabled=false; }
});
$('localeSelect').addEventListener('change',event=>{state.locale=event.target.value;localStorage.setItem('astra_locale',state.locale);applyLocale();});
$('reportLocale').addEventListener('change',event=>{state.locale=event.target.value;localStorage.setItem('astra_locale',state.locale);applyLocale();});
$('logoutButton').addEventListener('click',()=>{state.token='';state.user=null;state.chart=null;localStorage.removeItem('astra_token');showAuth(false);});
$('accountButton').addEventListener('click',()=>toast(state.user?.email || 'ASTRA OS'));
$('upgradeButton').addEventListener('click',async()=>{try{const r=await api('/api/billing/checkout',{method:'POST',body:'{}'});location.href=r.checkout_url;}catch(e){toast(e.message);}});

document.addEventListener('click',event=>{
  const tab=event.target.closest('[data-tab]');
  if(tab){openTab(tab.dataset.tab);return;}
  const action=event.target.closest('[data-action]');
  if(action?.dataset.action==='new-chart'){openTab('birth');return;}
});

async function searchPlace() {
  const query=$('placeInput').value.trim();
  if(query.length<2){toast(t('pleaseSelectPlace'));return;}
  $('searchPlace').disabled=true; $('searchPlace').textContent=t('searching');
  try {
    const result=await api(`/api/geocode?query=${encodeURIComponent(query)}`);
    if(!result.results.length){toast(t('placeUnavailable'));return;}
    const box=$('placeResults'); box.hidden=false;
    box.innerHTML=result.results.map((item,index)=>`<button type="button" class="place-result" data-place-index="${index}">${esc(item.label)}</button>`).join('');
    state.placeResults=result.results;
  } catch(error){toast(error.message || t('placeUnavailable'));}
  finally {$('searchPlace').disabled=false;$('searchPlace').textContent=t('findPlace');}
}
$('searchPlace').addEventListener('click',searchPlace);
$('placeInput').addEventListener('keydown',event=>{if(event.key==='Enter'){event.preventDefault();searchPlace();}});
$('placeResults').addEventListener('click',async event=>{
  const button=event.target.closest('[data-place-index]'); if(!button)return;
  const item=state.placeResults[Number(button.dataset.placeIndex)];
  state.placeChoice=item; $('placeInput').value=item.label; $('latitudeInput').value=item.latitude; $('longitudeInput').value=item.longitude; $('placeResults').hidden=true;
  try { const z=await api(`/api/timezone?latitude=${item.latitude}&longitude=${item.longitude}`); $('timezoneInput').value=z.timezone; } catch(e){toast(e.message);}
});

$('birthForm').addEventListener('submit',async event=>{
  event.preventDefault();
  const latitude=Number($('latitudeInput').value), longitude=Number($('longitudeInput').value);
  if(!Number.isFinite(latitude)||!Number.isFinite(longitude)||!$('timezoneInput').value.trim()){ $('chartError').hidden=false;$('chartError').textContent=t('coordinatesRequired');return; }
  const payload={
    label:$('labelInput').value.trim() || 'My birth chart', birth_date:$('dateInput').value, birth_time:$('timeInput').value,
    place:$('placeInput').value.trim(), latitude, longitude, timezone_name:$('timezoneInput').value.trim(),
    fold:$('foldInput').value===''?null:Number($('foldInput').value), locale:$('reportLocale').value,
    chart_system:$('systemInput').value, ayanamsa:$('ayanamsaInput').value, house_system:$('houseInput').value || null,
  };
  $('chartError').hidden=true; $('generateButton').disabled=true; $('generateButton').textContent=t('loading');
  try {
    const chart=await api('/api/charts/preview',{method:'POST',body:JSON.stringify(payload)});
    state.chart=chart;state.currentProfileId=null;state.pendingBirthPayload=payload;renderChart();openTab('chart');toast(t('chartLoaded'));
  } catch(error){$('chartError').hidden=false;$('chartError').textContent=error.message;}
  finally {$('generateButton').disabled=false;$('generateButton').innerHTML=`${esc(t('generateChart'))} <span>↗</span>`;}
});

$('saveChartButton').addEventListener('click',async()=>{
  if(!state.pendingBirthPayload){toast(t('chartSaved'));return;}
  $('saveChartButton').disabled=true;$('saveChartButton').textContent=t('saving');
  try {
    const saved=await api('/api/charts',{method:'POST',body:JSON.stringify(state.pendingBirthPayload)});
    state.currentProfileId=saved.id;state.pendingBirthPayload=null;toast(t('chartSaved'));loadSavedCharts();
  }catch(e){toast(e.message);}
  finally {$('saveChartButton').disabled=false;$('saveChartButton').textContent=t('saveChart');}
});

document.querySelectorAll('[data-chart-tab]').forEach(button=>button.addEventListener('click',()=>{
  document.querySelectorAll('[data-chart-tab]').forEach(node=>node.classList.toggle('selected',node===button));
  ['summary','planets','houses','aspects'].forEach(name=>$(`chart${name[0].toUpperCase()}${name.slice(1)}`).hidden=name!==button.dataset.chartTab);
}));

function renderChart(){
  const chart=state.chart;if(!chart)return;
  const birth=chart.birth, config=chart.configuration;
  $('chartName').textContent=state.pendingBirthPayload?.label || state.savedChartLabel || t('birthChart');
  $('chartBirthLine').textContent=`${birth.local_date} · ${birth.local_time} · ${birth.place} · ${birth.timezone}`;
  $('chartQuality').innerHTML=[
    `<span class="quality-chip good">✓ ${esc(t('calculated'))}</span>`,
    `<span class="quality-chip">${esc(config.chart_system.toUpperCase())}</span>`,
    `<span class="quality-chip">${esc(config.house_system.replace('_',' '))}</span>`,
    `<span class="quality-chip">${esc(config.ayanamsa)} · ${Number(config.ayanamsa_degrees).toFixed(4)}°</span>`,
    `<span class="quality-chip">JPL DE440s</span>`
  ].join('');
  $('chartSummary').innerHTML=renderSummary(chart);
  $('chartPlanets').innerHTML=renderPlanetTable(chart);
  $('chartHouses').innerHTML=renderHouseList(chart);
  $('chartAspects').innerHTML=renderAspects(chart);
  renderLife(chart);renderPeriods(chart);renderVargas(chart);
  $('saveChartButton').disabled=Boolean(state.currentProfileId);
  $('saveChartButton').textContent=state.currentProfileId?t('saved'):t('saveChart');
}
function renderSummary(chart){
  const h=chart.houses,p=chart.planetary_positions,pc=chart.panchang,active=chart.vimshottari_dasha?.current_mahadasha;
  const metrics=[
    [t('ascendant'),`${h.ascendant_sign || chart.houses.ascendant.toFixed(1)+'°'}`],
    [t('midheaven'),`${h.midheaven.toFixed(2)}°`],
    [t('birthPanchang'),pc?.tithi?.name || '—'],
    [t('activePeriod'),active?.lord || '—'],
  ];
  const chartNotes=chart.configuration.chart_system==='western'?`<p class="subnote">${esc(t('westernNote'))}</p>`:'';
  const yogas=chart.yogas_and_doshas||[];
  const yogaHtml=yogas.length?yogas.map(y=>`<div class="aspect-item"><span>${esc(y.name)}</span><span class="tag warn">${esc(y.status.replaceAll('_',' '))}</span></div>`).join(''):`<p class="subnote">${esc(t('noYogas'))}</p>`;
  return `<div class="chart-layout"><div class="panel-card"><h3>${esc(t('calculated'))} · ${chart.configuration.chart_system==='western'?'Natal wheel':'D1 Rashi chart'}</h3>${renderWheel(chart)}<p class="subnote">${esc(t('methodNote'))}</p></div><div class="panel-card"><h3>${esc(t('summary'))}</h3><div class="metric-grid">${metrics.map(m=>`<div class="metric"><small>${esc(m[0])}</small><b>${esc(m[1])}</b></div>`).join('')}</div><h3 style="margin-top:20px">${esc(t('yogas'))}</h3><div class="aspect-list">${yogaHtml}</div>${chartNotes}<div class="domain-details"><summary>${esc(t('provenance'))}</summary><p>${esc(chart.configuration.conventions.join(' '))}</p></div></div></div>`;
}
function renderWheel(chart){
  if(chart.configuration.chart_system!=='western') return renderNorthIndian(chart);
  const pos=chart.planetary_positions;const center=180;const radius=135;
  const labels=Array.from({length:12},(_,i)=>{const a=(i*30-90-15)*Math.PI/180;return `<text class="chart-svg-label" x="${center+Math.cos(a)*112}" y="${center+Math.sin(a)*112}" text-anchor="middle" dominant-baseline="middle">${i+1}</text>`;}).join('');
  const lines=Array.from({length:12},(_,i)=>{const a=(i*30-90)*Math.PI/180;return `<line x1="${center}" y1="${center}" x2="${center+Math.cos(a)*radius}" y2="${center+Math.sin(a)*radius}" stroke="#34485d" stroke-width="1"/>`;}).join('');
  const planets=Object.entries(pos).map(([name,d])=>{const a=(Number(d.tropical_longitude)-90)*Math.PI/180;const x=center+Math.cos(a)*83;const y=center+Math.sin(a)*83;return `<g><circle class="chart-planet-dot" cx="${x}" cy="${y}" r="3.4"/><text x="${x+6}" y="${y-5}" font-size="8" fill="#e3ca9b">${esc(name.slice(0,2))}</text></g>`;}).join('');
  return `<svg class="chart-wheel" viewBox="0 0 360 360" role="img" aria-label="Western tropical natal chart"><circle cx="180" cy="180" r="145" fill="#101b28" stroke="#9d8050" stroke-width="1.2"/><circle cx="180" cy="180" r="102" fill="none" stroke="#34485d"/><circle cx="180" cy="180" r="61" fill="none" stroke="#34485d"/>${lines}${labels}${planets}<text x="180" y="174" fill="#d7b879" font-size="11" text-anchor="middle">ASTRA</text><text x="180" y="190" fill="#8fa0b4" font-size="7" text-anchor="middle">WESTERN</text></svg>`;
}
function renderNorthIndian(chart){
  const p=chart.planetary_positions;const h=chart.houses;
  const centers={1:[180,91],2:[101,73],3:[70,137],4:[101,180],5:[70,226],6:[101,287],7:[180,269],8:[259,287],9:[290,226],10:[259,180],11:[290,137],12:[259,73]};
  const frame='<rect x="18" y="18" width="324" height="324" fill="#101b28" stroke="#9d8050" stroke-width="2"/><path d="M18 18 L342 342 M342 18 L18 342 M180 18 L342 180 L180 342 L18 180 Z" fill="none" stroke="#9d8050" stroke-width="1.5"/>';
  const houses=Array.from({length:12},(_,i)=>{
    const house=i+1,[x,y]=centers[house];
    const sign=(h.cusp_sign_indices?.[i] ?? 0)+1;
    const occupants=Object.entries(p).filter(([,d])=>d.house===house).map(([name])=>planetSymbols[name]||name.slice(0,2));
    const label=house===1?'Lagna':`H${house}`;
    const occupantText=occupants.length?occupants.join(' '):'—';
    return `<g><text x="${x}" y="${y-15}" text-anchor="middle" font-size="9" fill="#8fa0b4">${label}</text><text x="${x}" y="${y}" text-anchor="middle" font-size="10" font-weight="700" fill="#d7b879">${sign}</text><text x="${x}" y="${y+14}" text-anchor="middle" font-size="11" fill="#f3e5c8">${esc(occupantText)}</text></g>`;
  }).join('');
  return `<svg class="chart-wheel" viewBox="0 0 360 360" role="img" aria-label="North Indian Vedic birth chart">${frame}${houses}</svg>`;
}

const planetSymbols={Sun:'☉',Moon:'☽',Mercury:'☿',Venus:'♀',Mars:'♂',Jupiter:'♃',Saturn:'♄',Uranus:'♅',Neptune:'♆',Pluto:'♇',Rahu:'☊',Ketu:'☋'};
function renderPlanetTable(chart){
  const p=chart.planetary_positions;const rows=Object.entries(p).map(([name,d])=>`<tr><td><span class="planet-symbol">${planetSymbols[name]||'◉'}</span><span class="planet-name">${esc(name)}</span></td><td>${esc(d.sign)}</td><td>${Number(d.degree_in_sign).toFixed(2)}°</td><td>${d.house}</td><td>${esc(d.nakshatra?.name||'—')}${d.nakshatra?.pada?` · P${d.nakshatra.pada}`:''}</td><td><span class="tag ${d.retrograde?'warn':''}">${d.retrograde?t('retrograde'):t('direct')}</span></td><td>${esc(d.dignity||'—')}</td></tr>`).join('');
  return `<div class="panel-card"><h3>${esc(t('planets'))}</h3><table class="data-table"><thead><tr><th>${esc(t('planet'))}</th><th>${esc(t('sign'))}</th><th>${esc(t('degree'))}</th><th>${esc(t('house'))}</th><th>${esc(t('nakshatra'))}</th><th>${esc(t('motion'))}</th><th>${esc(t('dignity'))}</th></tr></thead><tbody>${rows}</tbody></table></div>`;
}
function renderHouseList(chart){
  const h=chart.houses.cusps,p=chart.planetary_positions;
  const list=h.map((c,i)=>{const occupants=Object.entries(p).filter(([name,d])=>d.house===i+1).map(([name])=>name);return `<article class="house-card"><h4>${esc(t('house'))} ${i+1} · ${esc(chart.houses.cusp_signs?.[i] || '')}</h4><p>${esc(t('cusp'))}: ${Number(c).toFixed(2)}°</p><p>${esc(t('occupants'))}: ${esc(occupants.join(', ')||'—')}</p></article>`;}).join('');
  return `<div class="house-list">${list}</div>`;
}
function renderAspects(chart){
  const rows=chart.configuration.chart_system==='western'?chart.aspects.western.map(a=>({label:`${a.planet_a} ${a.aspect} ${a.planet_b}`,detail:`${a.separation.toFixed(2)}° · orb ${a.orb.toFixed(2)}°`})) : chart.aspects.vedic.map(a=>({label:`${a.planet} → ${t('house')} ${a.to_house}`,detail:`${a.aspect_offset}th aspect from house ${a.from_house}`}));
  const cards=rows.length?rows.map(r=>`<div class="aspect-item"><span>${esc(r.label)}</span><span>${esc(r.detail)}</span></div>`).join(''):`<div class="empty-state">${esc(t('noAspects'))}</div>`;
  return `<div class="panel-card"><h3>${esc(t('aspects'))}</h3><div class="aspect-list">${cards}</div></div>`;
}
function renderLife(chart){
  const root=$('lifeReports');
  if(!chart.life_domains?.length){root.innerHTML=`<div class="empty-state">${esc(t('noDomains'))}</div>`;return;}
  root.innerHTML=chart.life_domains.map(d=>`<article class="domain-card"><header><h3>${esc(d.title)}</h3><span class="tag">${d.houses_considered.map(x=>'H'+x).join(' · ')}</span></header><p>${esc(d.interpretation)}</p><div class="evidence-row">${d.supporting_factors.slice(0,5).map(f=>`<span class="evidence-chip support">+ ${esc(f.planet)} ${esc(f.type.replaceAll('_',' '))}</span>`).join('')}${d.challenging_factors.slice(0,5).map(f=>`<span class="evidence-chip challenge">− ${esc(f.planet)} ${esc(f.type.replaceAll('_',' '))}</span>`).join('')}</div><details class="domain-details"><summary>${esc(t('showEvidence'))}</summary>${d.house_evidence.map(f=>`<p>H${f.house} · ${esc(f.sign)} · ${esc(t('houseLord'))}: ${esc(f.lord)} (H${f.lord_house??'—'}) · ${esc(t('occupants'))}: ${esc(f.occupants.join(', ')||'—')}</p>`).join('')}${d.supporting_factors.length?`<p><b>${esc(t('support'))}:</b> ${d.supporting_factors.map(x=>`${esc(x.planet)} (${esc(x.type)})`).join('; ')}</p>`:`<p>${esc(t('support'))}: —</p>`}${d.challenging_factors.length?`<p><b>${esc(t('challenge'))}:</b> ${d.challenging_factors.map(x=>`${esc(x.planet)} (${esc(x.type)})`).join('; ')}</p>`:`<p>${esc(t('challenge'))}: —</p>`}</details></article>`).join('');
}
function renderPeriods(chart){
  const d=chart.vimshottari_dasha, root=$('periodReport');
  if(!d){root.innerHTML=`<div class="empty-state">${esc(t('noDomains'))}</div>`;return;}
  const periods=d.periods||[];const rows=periods.map(p=>{const start=new Date(p.start).toLocaleDateString(),end=new Date(p.end).toLocaleDateString();return `<article class="period-card ${p.active_now?'active':''}"><div><div class="period-lord">${esc(p.lord)}</div><div class="period-date">${p.nominal_years} years</div></div><div><div class="period-date">${esc(start)} → ${esc(end)}</div><div class="period-bar"><span style="width:${p.active_now?100:Math.max(9,Math.min(94,p.nominal_years/20*100))}%"></span></div></div>${p.active_now?`<span class="tag good">${esc(t('activeNow'))}</span>`:''}</article>`;}).join('');
  const active=d.current_mahadasha;const sub=d.current_antardasha;
  root.innerHTML=`<div class="two-col"><div class="panel-card"><h3>${esc(t('activePeriod'))}</h3><div class="metric-grid"><div class="metric"><small>${esc(t('mahadasha'))}</small><b>${esc(active?.lord||'—')}</b></div><div class="metric"><small>${esc(t('antardasha'))}</small><b>${esc(sub?.lord||'—')}</b></div><div class="metric"><small>${esc(t('dashaBalance'))}</small><b>${Number(d.birth_balance_years).toFixed(3)} y</b></div><div class="metric"><small>${esc(t('nakshatra'))}</small><b>${esc(d.nakshatra.name)}</b></div></div><p class="subnote">${esc(d.method_note)}</p></div><div class="panel-card"><h3>${esc(t('birthPanchang'))}</h3><p>${esc(d.nakshatra.name)} · ${esc(d.nakshatra.lord)} · Pada ${d.nakshatra.pada}</p><p>${esc(t('activeAtBirth'))}: ${periods.find(p=>p.active_at_birth)?.lord||'—'}</p><p class="subnote">${esc(t('dashaNote'))}</p></div></div><h3 style="margin:24px 0 12px">${esc(t('mahadasha'))} timeline</h3><div class="timeline">${rows}</div>`;
}
function renderVargas(chart){
  const root=$('vargaReport');const vars=chart.divisional_charts||{};const keys=Object.keys(vars);
  if(!keys.length){root.innerHTML=`<div class="empty-state">${esc(t('noDomains'))}</div>`;return;}
  const options=keys.map(k=>`<option value="${esc(k)}">${esc(k)}</option>`).join('');
  root.innerHTML=`<div class="varga-toolbar"><label>${esc(t('selectVarga'))}</label><select id="vargaSelect">${options}</select></div><div class="panel-card"><div id="vargaTable"></div></div>`;
  const select=$('vargaSelect');const update=()=>{const rows=Object.entries(vars[select.value]).map(([name,d])=>`<tr><td>${esc(name)}</td><td>${esc(chart.configuration.chart_system==='western'?'—':d.sign_index+1)}</td><td>${esc(['Aries','Taurus','Gemini','Cancer','Leo','Virgo','Libra','Scorpio','Sagittarius','Capricorn','Aquarius','Pisces'][d.sign_index])}</td><td>${Number(d.degree).toFixed(2)}°</td></tr>`).join('');$('vargaTable').innerHTML=`<table class="data-table"><thead><tr><th>${esc(t('planet'))}</th><th>Sign #</th><th>${esc(t('sign'))}</th><th>${esc(t('degree'))}</th></tr></thead><tbody>${rows}</tbody></table>`;};select.addEventListener('change',update);update();
}

async function loadRecentCharts(){
  if(!state.token)return;
  try{const items=await api('/api/charts');$('recentList').innerHTML=items.length?items.slice(0,4).map(item=>savedItem(item)).join(''):`<div class="empty-state">${esc(t('noCharts'))}</div>`;bindSavedActions($('recentList'));}catch(e){$('recentList').innerHTML=`<div class="empty-state">${esc(e.message)}</div>`;}
}
async function loadSavedCharts(){
  if(!state.token)return;
  try{const items=await api('/api/charts');$('savedChartsList').innerHTML=items.length?items.map(item=>savedItem(item)).join(''):`<div class="empty-state">${esc(t('noSaved'))}</div>`;bindSavedActions($('savedChartsList'));}catch(e){$('savedChartsList').innerHTML=`<div class="empty-state">${esc(e.message)}</div>`;}
}
function savedItem(item){return `<div class="saved-item"><div><b>${esc(item.label)}</b><small>${esc(item.birth_date)} · ${esc(item.birth_time)} · ${esc(item.place)} · ${esc(item.chart_system.toUpperCase())}</small></div><div class="saved-item-actions"><button class="small-button" data-open-profile="${item.id}">${esc(t('open'))}</button><button class="small-button" data-delete-profile="${item.id}">${esc(t('delete'))}</button></div></div>`;}
function bindSavedActions(root){root.querySelectorAll('[data-open-profile]').forEach(button=>button.addEventListener('click',async()=>{try{const chart=await api(`/api/charts/${button.dataset.openProfile}`);state.chart=chart;state.currentProfileId=Number(button.dataset.openProfile);state.pendingBirthPayload=null;state.savedChartLabel=chart.birth.place;renderChart();openTab('chart');}catch(e){toast(e.message);}}));root.querySelectorAll('[data-delete-profile]').forEach(button=>button.addEventListener('click',async()=>{if(!confirm('Delete this saved chart?'))return;try{await api(`/api/charts/${button.dataset.deleteProfile}`,{method:'DELETE'});toast(t('profileDeleted'));loadSavedCharts();loadRecentCharts();}catch(e){toast(e.message);}}));}

async function init(){
  applyLocale();
  try {
    const meta = await api('/api/meta');
    const attribution = $('geoAttribution');
    if (meta.geocoder_provider === 'nominatim') {
      attribution.innerHTML = 'Place data © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap contributors</a>';
      attribution.hidden = false;
    } else if (meta.geocoder_provider === 'mapbox') {
      attribution.innerHTML = 'Place search by <a href="https://www.mapbox.com/about/maps/" target="_blank" rel="noopener noreferrer">Mapbox</a>';
      attribution.hidden = false;
    }
  } catch (_) { /* The app can still render its sign-in screen while the API is restarting. */ }
  if(state.token){try{state.user=await api('/api/auth/me');showAuth(true);openTab('overview');}catch(e){state.token='';localStorage.removeItem('astra_token');showAuth(false);}}else showAuth(false);}
init();
