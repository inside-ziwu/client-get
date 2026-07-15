export type WidthPreset = 'small' | 'medium' | 'large';

export type WidthSpec = WidthPreset | { custom: number };

export function isCustomWidth(width: WidthSpec): width is { custom: number } {
  return typeof width === 'object';
}
