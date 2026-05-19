import dayjs from 'dayjs';

export function formatDateTime(value?: string | number | Date | null, format = 'YYYY-MM-DD HH:mm') {
  if (!value) {
    return '-';
  }

  const date = dayjs(value);
  return date.isValid() ? date.format(format) : '-';
}
