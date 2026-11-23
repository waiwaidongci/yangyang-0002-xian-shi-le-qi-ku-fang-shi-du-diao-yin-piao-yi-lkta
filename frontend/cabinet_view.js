import { api, h } from '/base.js'
import { feedback, handle, pick } from '/loan_forms.js'

export async function cabinets(root, user) {
  const [{ cabinets: boxes, placements }, records] = await Promise.all([api('/api/cabinets'), api('/api/treatments')])
  const candidates = records.filter(row => row.status !== 'released' && ['rehouse', 'condition'].includes(row.intervention) &&
    !placements.some(p => p.treatment_id === row.id))
  root.innerHTML = `<article class="studio"><header class="studio-heading"><h1>平衡柜调湿调度</h1>
    <p>准入湿度 45%–55%，处置通过独立复测后才腾空柜位。</p></header>
    <div class="cabinet-floor">${boxes.map(box => `<section><h2>${h(box.title)}</h2>
      <div class="cabinet-readings"><strong>${h(box.humidity)}% RH</strong><span>${box.occupied} / ${box.capacity} 已占</span></div>
      <meter min="0" max="${box.capacity}" value="${box.occupied}">${box.occupied} 位</meter>
      ${user.role === 'operator' ? `<form class="cabinet-reading studio-form" data-box="${h(box.code)}"><label>实测湿度<input name="humidity" type="number" min="10" max="95" step=".1" required></label><button>登记读数</button>${feedback}</form>` : ''}
      </section>`).join('')}</div>
    ${user.role === 'operator' && candidates.length ? `<form class="placement-form studio-form" id="place-form">
      <label>调湿处置${pick('treatment_id', candidates, r => r.id, r => r.instrument_code)}</label>
      <label>分配柜位${pick('cabinet_code', boxes, r => r.code, r => r.title)}</label>
      <button>登记入柜</button>${feedback}</form>` : ''}
    <div class="cabinet-custody">${placements.map(p => `<section><strong>${h(p.name)} · ${h(p.cabinet_code)}</strong>
      <span> 入柜湿度 ${h(p.intake_humidity)}% · ${p.vacated_at ? '已腾空' : '占柜中'}</span>
      ${user.role === 'reviewer' && !p.vacated_at ? `<form data-vacate="${p.id}"><button>复核退柜</button>${feedback}</form>` : ''}</section>`).join('') || '<p>暂无琴占用平衡柜。</p>'}</div></article>`
  root.querySelectorAll('[data-box]').forEach(form => handle(form, async values => {
    await api(`/api/cabinets/${form.dataset.box}/humidity`, 'PUT', values)
    await cabinets(root, user)
  }))
  root.querySelectorAll('[data-vacate]').forEach(form => handle(form, async () => {
    await api(`/api/cabinets/placements/${form.dataset.vacate}/vacate`, 'POST')
    await cabinets(root, user)
  }))
  const form = root.querySelector('#place-form')
  if (form) handle(form, async values => {
    await api('/api/cabinets/placements', 'POST', { ...values, treatment_id: Number(values.treatment_id) })
    await cabinets(root, user)
  })
}
