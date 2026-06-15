/**
 * Maps DateRangeContext state to API query params (from_date / to_date ISO strings).
 */
export function rangeToQueryParams(range, customDates = {}) {
  const now = new Date();
  let from = new Date(now);

  if (range === '24 HOURS' || range === '24h') {
    from.setHours(from.getHours() - 24);
  } else if (range === '7 DAYS' || range === '7d') {
    from.setDate(from.getDate() - 7);
  } else if (range === '30 DAYS' || range === '30d') {
    from.setDate(from.getDate() - 30);
  } else if ((range === 'CUSTOM RANGE' || range === 'custom') && customDates.startDate && customDates.endDate) {
    const start = new Date(`${customDates.startDate}T00:00:00`);
    const end = new Date(`${customDates.endDate}T23:59:59`);
    return {
      from_date: start.toISOString(),
      to_date: end.toISOString(),
    };
  } else {
    from.setHours(from.getHours() - 24);
  }

  return {
    from_date: from.toISOString(),
    to_date: now.toISOString(),
  };
}
