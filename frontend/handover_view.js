import { api, h } from '/base.js'
import { feedback, handle, pick, stateNames } from '/loan_forms.js'

const phases = { pickup: '领琴', return: '归还' }
const quality = label => `<label>${label}<select name="${label === '琴桥' ? 'bridge_ok' : 'case_ok'}"><option value="true">完好</option><option value="false">异常</option></select></label>`
const measure = () => `${quality('琴桥')}${quality('琴盒')}
  <label>漂移（音分）<input name="drift_cents" type="number" step=".1" required></label>
  <label>核验记录<input name="note" required minlength="3"></label>`
const measured = values => ({ ...values, bridge_ok: values.bridge_ok === 'true', case_ok: values.case_ok === 'true' })

export async function handover(root, user) {
  const [loans, slips] = await Promise.all([api('/api/loans'), api('/api/condition')])
  const actionable = loans.filter(row => ['reserved','out'].includes(row.state))
  const incidents = loans.filter(row => row.state === 'incident')
  root.innerHTML = `<article class="studio"><header class="studio-heading"><h1>领还琴况交接</h1>
    <p>琴桥、琴盒和漂移随交接签证保存。异常归还进入隔离复核。</p></header>
    <div class="handover-ledger"><section>${slips.map(s => `<section class="condition-note"><h2>${h(s.loan_code)} · ${h(phases[s.phase])}</h2>
      <p>${s.bridge_ok && s.case_ok ? '外观完好' : '琴桥或琴盒异常'} · ${h(s.drift_cents)} 音分 ${s.departure_cents != null ? `／领出 ${h(s.departure_cents)} 音分` : ''}</p>
      <p>${h(s.note)} · ${s.signed_by ? h(s.signed_by) : '待签证'}</p>
      ${s.clearance_note ? `<p>解除隔离：${h(s.clearance_note)} · ${h(s.clearance_signer)}</p>` : ''}
      ${!s.signed_by && user.role === 'reviewer' ? `<form data-slip="${s.id}"><button>签证交接</button>${feedback}</form>` : ''}</section>`).join('') || '<p>暂无琴况签证。预约确认后可登记领琴记录。</p>'}
      ${user.role === 'reviewer' ? incidents.map(row => `<form class="condition-note studio-form" data-clear="${row.id}">
      <h2>${h(row.code)} · 异常复查</h2>${measure()}<button>复验并解除隔离</button>${feedback}</form>`).join('') : ''}</section>
      <aside class="paper-note"><h2>登记现场琴况</h2>${user.role === 'operator' && actionable.length ?
      `<form id="condition-form" class="studio-form">
      <label>借琴单${pick('loan_id', actionable, row => row.id, row => `${row.code} · ${stateNames[row.state]}`)}</label>
      ${measure()}<button>保存待签记录</button>${feedback}</form>` : '<p>请先确认预约，或等待库管登记交接。</p>'}</aside></div></article>`
  const form = root.querySelector('#condition-form')
  if (form) handle(form, async ({ loan_id, ...values }) => {
    const loan = actionable.find(row => row.id === Number(loan_id))
    await api(`/api/condition/loans/${loan_id}`, 'POST', { ...measured(values), phase: loan.state === 'reserved' ? 'pickup' : 'return' })
    await handover(root, user)
  })
  root.querySelectorAll('[data-slip]').forEach(form => handle(form, async () => {
    await api(`/api/condition/${form.dataset.slip}/sign`, 'POST')
    await handover(root, user)
  }))
  root.querySelectorAll('[data-clear]').forEach(form => handle(form, async values => {
    await api(`/api/condition/loans/${form.dataset.clear}/close-incident`, 'POST', measured(values))
    await handover(root, user)
  }))
}
