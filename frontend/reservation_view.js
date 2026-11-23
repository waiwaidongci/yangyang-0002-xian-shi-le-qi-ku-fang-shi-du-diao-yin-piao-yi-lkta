import { api, h } from '/base.js'
import { dateLabel, dateTime, feedback, handle, pick, stateNames } from '/loan_forms.js'

export async function reservations(root, user) {
  const [requests, instruments] = await Promise.all([api('/api/loans'), api('/api/instruments')])
  root.innerHTML = `<article class="studio"><header class="studio-heading"><h1>排练借琴候补</h1>
    <p>同琴时段相撞时保留候补。已经领出或异常隔离的琴需先办归还。</p></header>
    <div class="reservation-layout"><section class="rehearsal-queue">${requests.map(row => `<article>
      <div><small>${h(row.code)} · ${h(row.instrument_code)} ${h(row.name)}</small><h2>${h(row.ensemble)}</h2>
      <p>${h(dateLabel(row.use_from))} 至 ${h(dateLabel(row.use_until))}</p></div>
      <div><strong>${h(stateNames[row.state])}</strong>${row.state === 'waiting' ? ` · 排位 ${row.queue_position}` : ''}
      ${user.role === 'reviewer' && row.state === 'waiting' ? `<form data-loan="${row.id}" data-action="reserve"><button>确认预约</button>${feedback}</form>` : ''}
      ${user.role === 'operator' && ['waiting','reserved'].includes(row.state) ? `<form data-loan="${row.id}" data-action="cancel"><button>撤销申请</button>${feedback}</form>` : ''}
      </div></article>`).join('') || '<p>暂无申请，先登记排练时段。</p>'}</section>
    <aside class="paper-note"><h2>登记借琴单</h2>${user.role === 'operator' ? `<form class="studio-form" id="new-loan">
      <label>申请单号<input name="code" placeholder="REH-024" required></label>
      <label>乐器${pick('instrument_code', instruments, row => row.code, row => row.name)}</label>
      <label>排练组<input name="ensemble" required></label>
      <label>开始（北京时间）<input name="use_from" type="datetime-local" required></label>
      <label>结束（北京时间）<input name="use_until" type="datetime-local" required></label>
      <button>进入候补</button>${feedback}</form>` : '<p>由库管登记排练团队和借琴时段。</p>'}
      <p><a href="#handover">前往领还交接 →</a></p></aside></div></article>`
  root.querySelectorAll('[data-loan]').forEach(form => handle(form, async () => {
    await api(`/api/loans/${form.dataset.loan}/${form.dataset.action}`, 'POST')
    await reservations(root, user)
  }))
  const form = root.querySelector('#new-loan')
  if (form) handle(form, async values => {
    await api('/api/loans', 'POST', { ...values, use_from: dateTime(values.use_from), use_until: dateTime(values.use_until) })
    await reservations(root, user)
  })
}
