'use client';

import { Dialog, DialogContent, DialogTitle } from '@shared/ui';

interface Props {
  groupId: string;
  open: boolean;
  onClose: () => void;
}

export default function AddCompanyModal({ open, onClose }: Props) {
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-6xl max-h-[85vh] overflow-hidden flex flex-col">
        <DialogTitle>从公司列表添加</DialogTitle>
        <p className="py-20 text-center text-sm text-muted-foreground">即将实现...</p>
      </DialogContent>
    </Dialog>
  );
}
