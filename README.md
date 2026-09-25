# mei-telos

一套用 Markdown 写的个人画像文件：8 个文件，让 AI 在每次对话开始就认识你，
并在你说出变化时保持更新。配套 AI 入门知识库 4.8 节使用，也可以独立使用。

## 为什么需要

新对话里的 AI 对你一无所知：背景要重讲、偏好要重提、目标要重说。
画像文件把“你是谁”外化成磁盘上的 8 个 md，AI 每次开工先读，读完再干活。

## 8 个文件

| 文件 | 装什么 | 什么时候更新 |
|------|--------|------------|
| profile/identity.md | 学校、专业、状态、沟通风格 | 身份或状态变化时 |
| profile/goals.md | 短期 / 中期 / 长期目标 | 目标调整时 |
| profile/interests.md | 真正投入时间的方向 | 新兴趣出现时 |
| profile/skills.md | 会什么、熟练到什么程度 | 新技能出现时 |
| profile/beliefs.md | 做事原则与判断方式 | 原则变化时 |
| profile/learned.md | 固定偏好 + 被纠正过的教训 | 每次被纠正后 |
| profile/soul.md | AI 以什么人设为你服务 | 对 AI 性格不满意时 |
| profile/work-style.md | 节奏、协作与决策习惯 | 习惯变化时 |

每个文件结构相同：定位句 → 分节内容 → 末尾变更记录表。

## 三步上手

1. 把 `profile/` 拷到你的工作区（项目专用）或用户目录（跨项目通用）
2. 把文件里的【占位符】换成你自己的信息——宁可少写，别写空话
3. 新开对话发开场指令，让 AI 复述确认（见 [docs/reading.md](docs/reading.md)）

## 保持新鲜

- 更新信号表：哪些话意味着哪个文件该改 → [docs/updating.md](docs/updating.md)
- 写入三规范：先读再改、带日期、记变更
- 敏感信息红线：联系方式与密码类不入文件
- 保鲜检查（脚本，只读）：缺文件、没填的占位符、超过 30 天没更新、
  超过 90 天该整份重审的，一条命令列出来

```bash
python scripts/telos_freshness_check.py                 # 扫脚本旁的 profile/
python scripts/telos_freshness_check.py --profile-dir 你的画像目录
python scripts/telos_freshness_check.py --selftest      # 内置用例
```

退出码：0 = 新鲜，1 = 有 major 项（缺失/占位符没填/超 90 天），
2 = 目录不存在。报告可加 `--json` 接其他工具。

## 边界

这是纯文件方案：不涉及对话历史归档、向量检索、多机同步。先把 8 个文件
用起来，需要进阶机制时再引入其他工具。

## License

MIT
