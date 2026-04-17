import { Tag } from 'antd';

const RATING_COLORS: Record<string, string> = {
  S: 'gold',
  A: 'green',
  B: 'blue',
  C: 'orange',
  D: 'default',
};

export interface RatingTagProps {
  grade: string;
}

export function RatingTag({ grade }: RatingTagProps) {
  return <Tag color={RATING_COLORS[grade] ?? 'default'}>{grade}</Tag>;
}
