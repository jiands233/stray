# STRAY — 暂停的制作归档，不是成片

这是 2026-11-19（Asia/Shanghai）因额度不足而暂停的赛博朋克追车短片《STRAY》制作归档。仓库里没有最终成片，也不能把现有预演当成 1080p60 交付。

## 实际状态（事实）

- 完整预演只有 `previews/STRAY_proxy_v3_640x360_12fps.mp4`：**640×360、12fps、60 秒**，不是 1080p60，也没有用插帧冒充 60 帧。该预演未通过镜头验收。
- 主角超跑、警车、直升机、油罐车四套程序几何资产已建；驾驶舱已建，并有夜景黑漆材质脚本。模型自身许可见 `assets/codex/LICENSE.txt`（CC0）。
- 镜头没有全部验收。v5 修过断崖、点火起飞、飞行隧道等片段；v6 补了驾驶舱进出、探照灯和卷街。**最新驾驶舱动态检查仍发现进舱方向 / 穿模问题。** 卷街自检为 0 遮挡、主角中心未出画，但镜头太远，警车坠落不可读，不能视为通过。
- 漫画风格脚本（`assets/codex/lookdev/comic_look.py`）和两张 lookdev 广告试图已有，但**漫画精修未完成，广告屏未完成全片替换**，不能写成已完成。
- 配乐与音效已有来源记录和预混，**未经听审**，不能当成终混。
- 没有最终 1080p60 成片，没有启动全片正式渲染。

原规格仍然有效：1080p60、16:9、代码真实 3D 逐帧渲染、一镜到底、不用实拍或视频生成模型。详见 `SPEC.md`。

## 恢复起点

脚本里写死了 `/workspace/stray/...` 绝对路径。本归档**没有改这些路径去适配仓库结构**。若要续做，应把目录放回 `/workspace/stray/`，或自行处理路径，不要假定克隆后能直接渲染。

建议阅读顺序：

1. `SPEC.md` — 创作要求
2. `production/PIPELINE.md` — 管线接口与暂停前记录
3. `production/HANDOFF_V6.json`、`previews/repairs_v6/REVIEW_FIRST.md` — 最新修正交接
4. `production/HANDOFF_REPAIRS.json`、`previews/repairs_v5/REVIEW_FIRST.md` — 更早的段落修正（断崖 / 起飞等 v6 未重渲）
5. `assets/codex/README.md`、`assets/codex/assets_night.blend` — 四资产 + 黑漆持久化版本（优先于 `assets.blend`）
6. `audio/SOURCES.md` — 音乐和录音出处、许可与限制

资产构建当时使用 Blender 4.5.3 LTS；制作预演管线使用本机的 Blender 4.2。安装包和解压目录**没有**纳入本仓库，需自行下载官方二进制。

## 目录

```
SPEC.md                          创作要求
production/                      场景脚本、交接、基准摘要、镜头快照 .blend
assets/codex/                    四资产与驾驶舱源码、.blend、预览图、lookdev
audio/                           来源说明、合法素材、预混
previews/                        完整低清预演与关键修正片段
```

重要文件：

- 资产：`assets/codex/assets_night.blend`（优先）、`assets/codex/assets.blend`
- 最新镜头脚本：`production/staging_v6.py`；更早段落：`production/staging_v5.py`、`production/build_scene.py`
- 完整预演：`previews/STRAY_proxy_v3_640x360_12fps.mp4`
- 最新修正片段：`previews/repairs_v6/*.mp4`
- 更早关键修正（断崖、坠落点火、飞行隧道、油罐车撞击等）：`previews/repairs_v5/*.mp4`

## 音频许可（不要弄错）

本仓库**没有**统一开源许可证。不得把整库或配乐当成 CC0。

- 配乐：Punch Deck《Alive》，来源页标注 105 BPM、CC BY 3.0。已保存连续 60 秒片段（不在中间截断）。BPM 与「蓄力后静音再 Drop」是否符合要求**只有来源声明，未经听审**，也没有人为插入静音或把听感写成已确认。
- 直升机音效是 **CC BY 4.0**，不是 CC0。
- 引擎、警笛、爆炸、所用玻璃破碎音按 `audio/SOURCES.md` 记录为 CC0；警笛是德国警车实地录音，不是已认证的纽约警车；爆炸来自烟花录音，不是真实车辆爆炸。
- `audio/glass.mp3` 已下载但未使用，原因见 SOURCES。

发表或继续混音前必须按 `audio/SOURCES.md` 保留署名。

## 渲染耗时（仅作记录，不是工期）

暂停前同机、同镜头 22.4 秒处的 1920×1080 对比：32 samples + 阴影/辉光约 28.5 秒/帧；关掉阴影和辉光、4 samples 约 6.2 秒/帧。后者不是同等品质，也不能外推成全片完工时间。更早的约 41 小时粗估来自未优化、且当时有并发任务的测试，已不能当工期。

## 未纳入本仓库、仍在本机的内容

原始工作目录仍在本机 `/workspace/stray/`，本归档只读复制，没有改它。未上传：

- Blender 安装目录与安装包（含 `/workspace/stray/blender-4.2.0-linux-x64/`、`blender.tar.xz`，以及 `assets/codex/blender-4.5.3-linux-x64/` 及其安装包）
- 原始逐帧 PNG 目录（animatic_frames*、各 repairs 片段帧图）
- 运行日志、pid、Codex 任务/对话日志、临时目录、缓存、`__pycache__`、`.blend1`
- 阶段 1 旧档 `assets/codex/phase1_archive/`（已被当前四资产文件取代）
- 音频分析中间件（`music_analysis.wav`、`music_rms.npy`、`sfx_only.wav`）和网页抓取 HTML
- 空的 `assets/ads/` 目录
