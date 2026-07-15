import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ListPage } from '../src/components/list-page';

describe('ListPage', () => {
  it('按标题、筛选、批量操作、内容和分页的顺序组织列表页', () => {
    render(
      <ListPage
        title="公司列表"
        description="浏览并筛选目标公司"
        primaryAction={<button type="button">新增公司</button>}
        filters={<div>筛选条件</div>}
        selectionToolbar={<div>已选择 2 项</div>}
        pagination={<div>分页控件</div>}
      >
        <div>公司数据</div>
      </ListPage>,
    );

    expect(screen.getByRole('heading', { level: 1, name: '公司列表' })).toBeInTheDocument();
    expect(screen.getByText('浏览并筛选目标公司')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '新增公司' })).toBeInTheDocument();
    expect(screen.getByText('已选择 2 项').parentElement).toHaveClass('animate-in', 'fade-in');

    const sections = ['筛选条件', '已选择 2 项', '公司数据', '分页控件'].map((text) =>
      screen.getByText(text),
    );
    for (let index = 1; index < sections.length; index += 1) {
      const previousSection = sections[index - 1]!;
      const currentSection = sections[index]!;
      expect(
        previousSection.compareDocumentPosition(currentSection) & Node.DOCUMENT_POSITION_FOLLOWING,
      ).toBeTruthy();
    }
  });

  it('省略可选区域并透传自定义 className', () => {
    const { container } = render(
      <ListPage title="联系人" className="custom-page">
        <div>联系人数据</div>
      </ListPage>,
    );

    expect(container.firstElementChild).toHaveClass('custom-page');
    expect(screen.getByRole('heading', { name: '联系人' })).toBeInTheDocument();
    expect(screen.getByText('联系人数据')).toBeInTheDocument();
  });
});
