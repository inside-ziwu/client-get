# shared-ui-select

## ADDED Requirements

### Requirement: 下拉选择器 SHALL 在选项超出可视高度时保持全部选项可达

共享 Select 组件(`shared-ui/select.tsx`)的下拉内容区 SHALL 限制最大高度(不超过 24rem 且不超过 Radix 计算的可用视口高度),超出部分 SHALL 通过 Viewport 滚动可达,并提供上下滚动按钮作为可视滚动入口。

#### Scenario: 选项较多时可选到底部

- **GIVEN** 某下拉包含 19 个选项(如预热档位)
- **WHEN** 用户展开下拉
- **THEN** 列表高度不超过可视区域,通过滚轮、键盘或按住上下滚动按钮可以到达并选中任意选项(包括最后一项)

#### Scenario: 选项较少时行为不变

- **GIVEN** 某下拉选项总高度小于最大高度
- **WHEN** 用户展开下拉
- **THEN** 列表完整展示,无滚动按钮干扰,现有交互不变
