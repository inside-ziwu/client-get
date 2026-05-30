import dayjs from 'dayjs';
import timezone from 'dayjs/plugin/timezone';
import utc from 'dayjs/plugin/utc';

dayjs.extend(utc);
dayjs.extend(timezone);

export function formatDateTime(value?: string | number | Date | null, format = 'YYYY-MM-DD HH:mm') {
  if (!value) {
    return '-';
  }

  const date = dayjs(value);
  return date.isValid() ? date.format(format) : '-';
}

export function formatZonedDateTime(value?: string | number | Date | null, tz?: string | null) {
  if (!value || !tz) {
    return '-';
  }

  const date = dayjs(value);
  if (!date.isValid()) return '-';
  const zoned = date.tz(tz);
  const parts = new Intl.DateTimeFormat('en-US', { timeZone: tz, timeZoneName: 'short' }).formatToParts(date.toDate());
  const label = parts.find((part) => part.type === 'timeZoneName')?.value ?? tz;
  return `${zoned.format('YYYY-MM-DD HH:mm')} ${label}`;
}
