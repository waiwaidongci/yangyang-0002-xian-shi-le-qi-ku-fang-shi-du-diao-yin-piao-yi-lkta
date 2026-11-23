import { api, h, mount, waitJob } from '/base.js'
import { reservations } from '/reservation_view.js'
import { cabinets } from '/cabinet_view.js'
import { handover } from '/handover_view.js'

const pageNames = {
  inventory: '借用台账',
  windows: '测量簿',
  analysis: '漂移分析',
  treatment: '停借与复测', reservations: '借琴候补', cabinets: '平衡柜', handover: '领还签证'
}
const availability = { available: '可借', held: '停借', attention: '待登记停借', unmeasured: '待测量' }
const treatmentStatus = { open: '待处置', applied: '复测中', released: '已恢复借用' }
const methodNames = { rehouse: '换柜平衡', retune: '复调与检弦', condition: '柜内调湿' }
const analysisStatus = { insufficient: '样本不足', constant: '测值秩恒定', computed: '已计算' }
const time = new Intl.DateTimeFormat('zh-CN', {
  timeZone: 'Asia/Shanghai', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23'
})
let selectedCode = 'VA-017'
let currentAssessment = null

const stamp = value => value ? time.format(new Date(value)) : '待录入'
const drift = value => value == null ? '未录入' : `${Number(value) > 0 ? '+' : ''}${Number(value)}¢`
const humidity = value => value == null ? '未录入' : `${Number(value)}%`
const tag = (value, state) => `<span class="state state-${h(state)}">${h(value)}</span>`

function heading(kicker, title, description) {
  return `<header class="studio-heading"><span class="folio">${h(kicker)}</span><h1>${h(title)}</h1><p>${h(description)}</p></header>`
}

function assetSelect(assets) {
  return `<label class="selector">乐器
    <select id="asset-select">${assets.map(a => `<option value="${h(a.code)}" ${a.code === selectedCode ? 'selected' : ''}>${h(a.code)} · ${h(a.name)}</option>`).join('')}</select>
  </label>`
}

function windowTable(rows) {
  if (!rows.length) return '<p class="blank">暂无测量。请为该乐器录入湿度或调音记录。</p>'
  return `<div class="table-frame"><table class="ledger"><thead><tr><th>观测窗（北京时间）</th><th>相对湿度</th><th>音高漂移</th><th>配对结果</th></tr></thead>
    <tbody>${rows.map(row => {
      const paired = row.humidity_percent != null && row.drift_cents != null
      return `<tr><td>${h(stamp(row.measured_at))}</td><td>${h(humidity(row.humidity_percent))}</td><td>${h(drift(row.drift_cents))}</td>
        <td>${tag(paired ? '已配对' : '待补录', paired ? 'available' : 'open')}</td></tr>`
    }).join('')}</tbody></table></div>`
}

function bindAsset(outlet, redraw) {
  const selector = outlet.querySelector('#asset-select')
  selector?.addEventListener('change', () => {
    selectedCode = selector.value
    currentAssessment = null
    redraw()
  })
  outlet.querySelectorAll('[data-asset]').forEach(link => link.addEventListener('click', () => {
    selectedCode = link.dataset.asset
    currentAssessment = null
  }))
}

function bindForm(form, action) {
  form.addEventListener('submit', async event => {
    event.preventDefault()
    const feedback = form.querySelector('output')
    const button = form.querySelector('button')
    button.disabled = true
    feedback.textContent = '提交中…'
    try {
      await action(Object.fromEntries(new FormData(form)))
    } catch (error) {
      feedback.textContent = error.message
      feedback.className = 'form-error'
    } finally {
      button.disabled = false
    }
  })
}

async function inventory(outlet) {
  const assets = await api('/api/instruments')
  outlet.innerHTML = `<article class="studio">
    ${heading('林间艺术中心 · 乐器库', '借用前的最后一道检查', '对照各把乐器的最新音分和停借状态，再把琴交给排练组。')}
    <div class="inventory-overview">
      <div><strong>${assets.filter(a => a.readiness === 'available').length}</strong><span>把可借</span></div>
      <div><strong>${assets.filter(a => a.readiness !== 'available').length}</strong><span>把待处理</span></div>
      <p><b>停借线 ±15 音分</b><br>取最近观测窗的实测音高偏移。测量缺失时先补录。</p>
    </div>
    <div class="table-frame"><table class="ledger inventory-table"><thead><tr><th>柜位 / 乐器</th><th>参考 A 音</th><th>最近时窗</th><th>实际偏移</th><th>借用状态</th><th>去向</th></tr></thead>
    <tbody>${assets.map(asset => `<tr><td><small>${h(asset.cabinet)} / ${h(asset.code)}</small><b>${h(asset.name)}</b></td>
    <td>${h(asset.reference_hz)} Hz</td><td>${h(stamp(asset.measured_at))}</td>
    <td>${h(drift(asset.drift_cents))}</td><td>${tag(availability[asset.readiness], asset.readiness)}</td>
    <td><a data-asset="${h(asset.code)}" href="#${asset.active_treatment ? 'treatment' : 'windows'}">${asset.active_treatment ? '查看复测' : '查看测量'} →</a></td></tr>`).join('')}</tbody></table></div>
  </article>`
  bindAsset(outlet, () => {})
}

async function windows(outlet, user) {
  const [assets, rows] = await Promise.all([
    api('/api/instruments'), api(`/api/instruments/${selectedCode}/windows`)
  ])
  const operator = user.role === 'operator'
  outlet.innerHTML = `<article class="studio">
    ${heading('时窗日志', '把湿度和音分记在同一窗', '调音仪与湿度计可分次登记。同一乐器、同一时刻的记录组成一对。')}
    ${assetSelect(assets)}
    <div class="measurement-layout"><section><h2>最近 12 个观测窗</h2>${windowTable(rows)}</section>
    <aside class="paper-note"><h2>补录观测</h2>
    ${operator ? `<form id="window-form" class="studio-form">
      <label>来源<select name="channel"><option value="humidity_percent">湿度计（% RH）</option>
      <option value="drift_cents">调音仪（音分）</option></select></label>
      <label>观测时刻（北京时间）<input name="measured_at" type="datetime-local" step="900" required></label>
      <label>仪器读数<input name="reading" type="number" step="0.1" inputmode="decimal" required placeholder="如 51.5 或 −3.0"></label>
      <button type="submit">登记来源读数</button><output aria-live="polite"></output>
    </form>` : '<p>由库管登记仪器原始读数。</p>'}
    <p>已登记的同一来源读数会封存。另一来源可以补录到相同时窗。</p></aside></div>
  </article>`
  bindAsset(outlet, () => windows(outlet, user))
  const form = outlet.querySelector('#window-form')
  if (form) bindForm(form, async values => {
    await api(`/api/instruments/${selectedCode}/windows`, 'PUT', {
      measured_at: `${values.measured_at}:00+08:00`, [values.channel]: values.reading
    })
    await windows(outlet, user)
    outlet.querySelector('output').textContent = '已登记读数'
  })
}

function plot(canvas, points) {
  const context = canvas.getContext('2d')
  const width = canvas.width, height = canvas.height
  const left = 74, right = width - 28, top = 22, bottom = height - 52
  const humidityRange = [Math.min(40, ...points.map(p => p.humidity - 2)), Math.max(65, ...points.map(p => p.humidity + 2))]
  const magnitude = Math.ceil(Math.max(20, ...points.map(p => Math.abs(p.drift) + 2)) / 10) * 10
  const x = value => left + (value - humidityRange[0]) / (humidityRange[1] - humidityRange[0]) * (right - left)
  const y = value => top + (magnitude - value) / (2 * magnitude) * (bottom - top)
  context.clearRect(0, 0, width, height)
  context.fillStyle = '#dae3d3'
  context.fillRect(left, y(5), right - left, y(-5) - y(5))
  context.lineWidth = 1
  context.font = '19px monospace'
  context.textAlign = 'right'
  for (const tick of [-magnitude, -magnitude / 2, 0, magnitude / 2, magnitude]) {
    context.strokeStyle = tick === 0 ? '#749082' : '#aab6a3'
    context.beginPath()
    context.moveTo(left, y(tick))
    context.lineTo(right, y(tick))
    context.stroke()
    context.fillStyle = '#30574a'
    context.fillText(`${tick > 0 ? '+' : ''}${tick}¢`, left - 10, y(tick) + 6)
  }
  context.textAlign = 'center'
  for (let tick = Math.ceil(humidityRange[0] / 5) * 5; tick <= humidityRange[1]; tick += 5) {
    context.fillText(`${tick}%`, x(tick), bottom + 31)
  }
  for (const point of points) {
    context.beginPath()
    context.arc(x(point.humidity), y(point.drift), 7, 0, 2 * Math.PI)
    context.fillStyle = Math.abs(point.drift) >= 15 ? '#8b4533' : '#306c53'
    context.fill()
  }
}

async function analysis(outlet, user) {
  const [assets, history] = await Promise.all([
    api('/api/instruments'), api(`/api/instruments/${selectedCode}/assessments`)
  ])
  const report = history.find(row => row.id === currentAssessment) || history[0]
  outlet.innerHTML = `<article class="studio">
    ${heading('关系检验', '湿度与调音漂移', '按同一把乐器的两个来源配对。用平均秩处理相同读数。')}
    <div class="toolbar">${assetSelect(assets)}
      ${user.role !== 'viewer' ? '<form id="analysis-form"><button type="submit">计算最新观测窗</button><output aria-live="polite"></output></form>' : ''}
    </div>
    <div class="analysis-layout">
      <section class="paper-chart"><h2>配对散点与 ±5 音分稳定带</h2>
      ${report?.points.length ? '<canvas id="drift-plot" width="920" height="340" aria-label="横轴相对湿度百分比，纵轴音分偏移">配对数据见下表。</canvas>' :
        '<p class="blank">该乐器尚无配对窗。请先到测量簿补齐两个来源。</p>'}</section>
      <aside class="paper-note"><h2>Spearman 秩相关</h2>${report ? `
      <strong class="rho">${report.rho == null ? '—' : Number(report.rho).toFixed(3)}</strong>
      <p>${h(analysisStatus[report.status])} · ${report.pair_count} 对 · ${report.missing_count} 个缺测窗</p>
      <p>每次取最新 12 个时窗，至少 5 个完整配对。相关关系供处置排查，恢复借用取决于处置后的实测复核。</p>
      <label class="selector">计算记录<select id="report-select">
        ${history.map(row => `<option value="${row.id}" ${report.id === row.id ? 'selected' : ''}>#${row.id} · ${h(stamp(row.created_at))}</option>`).join('')}
      </select></label>` : '<p class="blank">提交一次计算生成首份记录。</p>'}</aside>
    </div>
    ${report?.points.length ? `<details><summary>查看本次配对数据</summary>${windowTable(report.points.map(point => ({
      measured_at: point.window, humidity_percent: point.humidity, drift_cents: point.drift
    })))}</details>` : ''}
  </article>`
  if (report?.points.length) plot(outlet.querySelector('#drift-plot'), report.points)
  bindAsset(outlet, () => analysis(outlet, user))
  outlet.querySelector('#report-select')?.addEventListener('change', event => {
    currentAssessment = Number(event.target.value)
    analysis(outlet, user)
  })
  const form = outlet.querySelector('#analysis-form')
  if (form) bindForm(form, async () => {
    const code = selectedCode
    const { job_id: id } = await api(`/api/instruments/${code}/assessments`, 'POST')
    const result = await waitJob(id)
    if (selectedCode === code && form.isConnected) {
      currentAssessment = Number(result.id)
      await analysis(outlet, user)
    }
  })
}

function treatmentCard(record, user) {
  return `<section class="docket"><header class="docket-top">
    <h2>${h(record.instrument_code)} · ${h(methodNames[record.intervention])}</h2>
    ${tag(treatmentStatus[record.status], record.status)}</header>
    <p><b>触发窗 ${h(stamp(record.opened_window))}</b> · ${h(record.reason)}</p>
    ${record.applied_at ? `<p>处置完成 ${h(stamp(record.applied_at))}</p>` : ''}
    ${record.status === 'open' && user.role === 'operator' ? `<form class="apply-form studio-form" data-record="${record.id}">
      <label>完成时刻（北京时间）<input name="applied_at" type="datetime-local" required></label>
      <button type="submit">登记处置完成</button><output aria-live="polite"></output></form>` : ''}
    ${record.status !== 'open' ? windowTable(record.retest.windows) : ''}
    ${record.retest.reason ? `<p class="callout">${h(record.retest.reason)}</p>` : ''}
    ${record.status === 'applied' && user.role === 'reviewer' ? `<form class="release-form studio-form" data-record="${record.id}">
      <button type="submit">复核并恢复借用</button><output aria-live="polite"></output></form>` : ''}
    ${record.released_by ? `<p>签审 ${h(record.released_by)} · ${h(stamp(record.released_at))}</p>` : ''}
  </section>`
}

async function treatment(outlet, user) {
  const [assets, records] = await Promise.all([api('/api/instruments'), api('/api/treatments')])
  const available = assets.filter(a => a.loan_status === 'available')
  outlet.innerHTML = `<article class="studio">
    ${heading('出柜前复核', '停借、处置与恢复', '处置完成后，近两个同琴观测窗都须配对并处于稳定带。')}
    <div class="treatment-layout"><div class="dockets">${records.length ? records.map(record => treatmentCard(record, user)).join('') :
     '<p class="blank">暂无处置记录。达到停借线的乐器可发起处置。</p>'}</div>
    <aside class="paper-note"><h2>${user.role === 'operator' ? '发起停借处置' : '恢复条件'}</h2>
    ${user.role === 'operator' && available.length ? `<form id="open-form" class="studio-form">
      <label>乐器<select name="instrument_code">${available.map(asset => `<option value="${h(asset.code)}" ${asset.code === selectedCode ? 'selected' : ''}>${h(asset.code)} · ${h(asset.name)} · ${h(drift(asset.drift_cents))}</option>`).join('')}</select></label>
      <label>处置类型<select name="intervention">${Object.entries(methodNames).map(([key, value]) => `<option value="${key}">${value}</option>`).join('')}</select></label>
      <label>现场记录<textarea name="reason" minlength="3" maxlength="160" required placeholder="记录发现的柜位或调音问题"></textarea></label>
      <button type="submit">停借并登记处置</button><output aria-live="polite"></output>
    </form>` : ''}
    <p>两个时窗相隔至少 4 小时，湿度 45%–55%，音高偏移绝对值 ≤5 音分。</p>
    <a href="#windows">去测量簿补录 →</a></aside></div>
  </article>`
  const form = outlet.querySelector('#open-form')
  if (form) bindForm(form, async body => {
    await api('/api/treatments', 'POST', body)
    await treatment(outlet, user)
  })
  outlet.querySelectorAll('.apply-form').forEach(form => bindForm(form, async values => {
    await api(`/api/treatments/${form.dataset.record}/apply`, 'POST', { applied_at: `${values.applied_at}:00+08:00` })
    await treatment(outlet, user)
  }))
  outlet.querySelectorAll('.release-form').forEach(form => bindForm(form, async () => {
    await api(`/api/treatments/${form.dataset.record}/release`, 'POST')
    await treatment(outlet, user)
  }))
}

const pageRenderers = { inventory, windows, analysis, treatment, reservations, cabinets, handover }
mount({
  title: '弦室',
  kicker: '林间艺术中心',
  pages: pageNames,
  render: (page, outlet, user) => pageRenderers[page](outlet, user)
})
