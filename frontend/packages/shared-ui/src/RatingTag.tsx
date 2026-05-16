import { Badge } from './components/badge';

const RATING_CLASSES: Record<string, string> = {
  S: 'bg-amber-100 text-amber-800',
  A: 'bg-emerald-100 text-emerald-800',
  B: 'bg-sky-100 text-sky-800',
  C: 'bg-orange-100 text-orange-800',
  D: 'bg-slate-100 text-slate-700',
};

export interface RatingTagProps {
  grade: string;
}

export function RatingTag({ grade }: RatingTagProps) {
  return (
    <Badge variant="secondary" className={RATING_CLASSES[grade] ?? 'bg-slate-100 text-slate-700'}>
      {grade}
    </Badge>
  );
}
