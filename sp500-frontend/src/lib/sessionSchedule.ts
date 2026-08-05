/** Estimate GitHub Actions agent-cron next fire in America/New_York. */

const INTERVAL_MIN = 15
const SESSION_START_MIN = 4 * 60 // 4:00 AM ET
const SESSION_END_MIN = 20 * 60 // 8:00 PM ET

function etParts(now = new Date()) {
  const fmt = new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/New_York',
    weekday: 'short',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hourCycle: 'h23',
  })
  const parts = Object.fromEntries(
    fmt
      .formatToParts(now)
      .filter((p) => p.type !== 'literal')
      .map((p) => [p.type, p.value])
  )
  const weekdayMap: Record<string, number> = {
    Sun: 0,
    Mon: 1,
    Tue: 2,
    Wed: 3,
    Thu: 4,
    Fri: 5,
    Sat: 6,
  }
  return {
    weekday: weekdayMap[parts.weekday] ?? 0,
    year: Number(parts.year),
    month: Number(parts.month),
    day: Number(parts.day),
    hour: Number(parts.hour),
    minute: Number(parts.minute),
    second: Number(parts.second),
  }
}

/** Convert an ET wall-clock to a UTC Date (handles DST). */
function etWallToUtc(
  year: number,
  month: number,
  day: number,
  hour: number,
  minute: number
): Date {
  let utc = Date.UTC(year, month - 1, day, hour, minute, 0)
  for (let i = 0; i < 4; i++) {
    const p = etParts(new Date(utc))
    const want = Date.UTC(year, month - 1, day, hour, minute, 0)
    const got = Date.UTC(p.year, p.month - 1, p.day, p.hour, p.minute, 0)
    utc += want - got
  }
  return new Date(utc)
}

function addCalendarDays(
  year: number,
  month: number,
  day: number,
  days: number
): { year: number; month: number; day: number; weekday: number } {
  const probe = new Date(Date.UTC(year, month - 1, day + days, 16, 0, 0))
  const p = etParts(probe)
  return { year: p.year, month: p.month, day: p.day, weekday: p.weekday }
}

export function isExtendedSessionNow(now = new Date()): boolean {
  const p = etParts(now)
  if (p.weekday === 0 || p.weekday === 6) return false
  const mins = p.hour * 60 + p.minute
  return mins >= SESSION_START_MIN && mins < SESSION_END_MIN
}

/** Next scheduled Agent cron tick (~every 15m in extended hours). ISO UTC. */
export function nextAgentCronRun(now = new Date()): string {
  let { year, month, day, weekday, hour, minute, second } = etParts(now)
  let mins = hour * 60 + minute

  for (let guard = 0; guard < 10; guard++) {
    if (weekday >= 1 && weekday <= 5) {
      const totalSec = mins * 60 + (guard === 0 ? second : 0)
      let nextMin = Math.floor(totalSec / (INTERVAL_MIN * 60) + 1) * INTERVAL_MIN
      if (nextMin < SESSION_START_MIN) nextMin = SESSION_START_MIN
      if (nextMin < SESSION_END_MIN) {
        return etWallToUtc(
          year,
          month,
          day,
          Math.floor(nextMin / 60),
          nextMin % 60
        ).toISOString()
      }
    }

    const next = addCalendarDays(year, month, day, 1)
    year = next.year
    month = next.month
    day = next.day
    weekday = next.weekday
    mins = SESSION_START_MIN - 1 // so next loop picks 4:00
    while (weekday === 0 || weekday === 6) {
      const n2 = addCalendarDays(year, month, day, 1)
      year = n2.year
      month = n2.month
      day = n2.day
      weekday = n2.weekday
    }
  }

  return new Date(now.getTime() + INTERVAL_MIN * 60_000).toISOString()
}
