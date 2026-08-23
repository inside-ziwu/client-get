# 真站冒烟 2026-08-23（A8，信息性）

命令：`uv run python scripts/run_industry_news_fetch.py --from-file app/data/industry_news_sources_pcb.json --dry-run`

出口：开发机本地网络，非 Sealos 生产出口。14 源全部解析出 ≥1 条。

| 代号 | 名称 | 条数 | 前 3 条标题 |
|---|---|---:|---|
| `pcb-update` | PCB Update | 23 | The EPA's TBBPA flame-retardant risk analysis is dividing industry and environme<br>IDTechEx examines whether in-mold electronics could be the path for printed elec<br>A hobbyist demonstrated 3-D printing a working PCB at home instead of ordering o |
| `pcea` | PCEA | 10 | PCEA Announces Fall Webinar Schedule<br>PCB West Panel to Take On What’s Next for PCB Design<br>PCB Market Authority Nakahara to Deliver Industry Outlook at PCB West |
| `iconnect007` | I-Connect007 | 46 | Qnity Advances Node Materials Innovation with KLA Inspection Technology<br>Eltek Reports Q2 2026 Results<br>MKS Earns Zhen Ding 2026 Awards for Service and Innovation |
| `pcdandf` | PCD&F | 12 | Taesung Returns to Profit on Strong FC-BGA Equipment Demand<br>Stackpole Electronics Expands CSSU Series Current Sense Resistors<br>GreenSource Fabrication to Showcase Advanced PCB Manufacturing Capabilities at I |
| `circuits-assembly` | Circuits Assembly | 12 | Velocity Group Opens Electronics Manufacturing Plant in Ohio<br>CACI Opens Defense Electronics Manufacturing Center in New York<br>PCB West Panel to Take On What’s Next for PCB Design |
| `ipc` | IPC | 10 | The Supply Chain Is Tightening Again. The Data Makes It Hard to Look Away<br>Winners of Hand Soldering Competition Vietnam 2026 Announced<br>Introduction to Wire Harness Design II |
| `pcb-west` | PCB West | 10 | PCB West Panel to Take On What’s Next for PCB Design<br>PCB Market Authority Nakahara to Deliver Industry Outlook at PCB West<br>A Day of Assembly Classes at PCB West 2026 |
| `pcb-east` | PCB East | 8 | PCB East 2027 Booth Sales Open for Returning Exhibitors<br>PCB East 2026 Attendance Up Almost 48% Over Last Year<br>PCB East 2026 Exhibits Open Today |
| `tpca` | TPCA | 8 | 2026年7月台灣上市櫃PCB原物料營收 MoM 8.64%(廠商總表)<br>2026年7月台灣上市櫃PCB原物料營收YoY 55.1%<br>2026年7月台灣CCL 出口YoY 70.6% |
| `nepcon-japan` | NEPCON JAPAN | 5 | [January (Tokyo) Show] Post Show Report 2026 released! (2026/05/18)<br>Press release published: “Rao Tummala and Leading Companies ASE, TSMC, Intel, To<br>[Press release] RX Japan Announces 40th Anniversary Edition of NEPCON JAPAN 2026 |
| `productronica` | Productronica | 9 | German Brand Award productronica impresses with brand revival and corporate bran<br>Strong signal for the industry: productronica 2025 drives positive industry tren<br>productronica Innovation Award 2025: The winners have been chosen |
| `electronica` | electronica | 8 | From components to intelligent systems: electronics as the basis for the All Ele<br>Secure components: Focus shifts to cyber resilience in electronics development<br>Energy efficiency as a key topic in electronics |
| `cpca-news` | CPCA 协会动态 | 6 | 智链生态·筑基未来——2026 中国电子电路产业趋势分析会在南通海门举办<br>焕新组织聚合力 绿色转型启新篇——CPCA 环保分会换届工作会议顺利召开<br>CPCA理监事长工作会议在合肥召开 |
| `cpca-weekly` | CPCA 每周资讯 | 6 | CPCA每周资讯第147期<br>CPCA每周资讯第146期<br>CPCA每周资讯第145期 |

## PCB Update 标题规则定稿

样本标题是段落全文（含导语），不是锚文本。与 PRD「标题取所在段落全文」一致，种子保持 `title_from: parent` + `href_exclude: pcbupdate\.com|pcea|mediakit`。fixture 按此规则保留一条外链剪报。

## 备注

- 个别源当日条数随站点更新波动；本次无 0 条。
- I-Connect007 首轮约 46 条、无发布时间，将按当轮 `fetched_at` 入库（design §11 已接受）。
- NEPCON 含 PDF 链接，按原文链接保留。

