import { h } from '/base.js'

export function pick(name, rows, value, label) {
  return `<select name="${h(name)}" required>${rows.map(row => `<option value="${h(value(row))}">${h(label(row))}</option>`).join('')}</select>`
}
export const dateTime = text => `${text}:00+08:00`
const localClock = new Intl.DateTimeFormat('zh-CN', {
  timeZone: 'Asia/Shanghai', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23'
})
export const dateLabel = value => localClock.format(new Date(value))
export const feedback = '<output aria-live="polite"></output>'
export const stateNames = {
  waiting: '候补', reserved: '已预约', out: '已领出', returned: '已归还', incident: '异常隔离', cancelled: '已撤销'
}
export function handle(form, action) {
  form.onsubmit = async event => {
    event.preventDefault()
    const button = form.querySelector('button')
    const output = form.querySelector('output')
    button.disabled = true
    output.textContent = '提交中…'
    try { await action(Object.fromEntries(new FormData(form))) }
    catch (error) { output.textContent = error.message; output.className = 'form-error' }
    finally { button.disabled = false }
  }
}
