import { Badge } from './components/badge';

const SYSTEM_CLASSES: Record<string, string> = {
  S: 'bg-amber-100 text-amber-800',
  A: 'bg-emerald-100 text-emerald-800',
  B: 'bg-sky-100 text-sky-800',
  C: 'bg-orange-100 text-orange-800',
  D: 'bg-slate-100 text-slate-700',
};

const MODEL_CLASSES: Record<string, string> = {
  A: 'bg-green-100 text-green-800',
  B: 'bg-blue-100 text-blue-800',
  C: 'bg-orange-100 text-orange-800',
  X: 'bg-red-100 text-red-800',
};

export interface RatingTagProps {
  grade: string;
  variant?: 'system' | 'model';
}

export function RatingTag({ grade, variant = 'system' }: RatingTagProps) {
  const classes = variant === 'model' ? MODEL_CLASSES : SYSTEM_CLASSES;
  return (
    <Badge variant="secondary" className={classes[grade] ?? 'bg-slate-100 text-slate-700'}>
      {grade}
    </Badge>
  );
}
