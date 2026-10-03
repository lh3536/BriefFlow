# BriefFlow Web MVP

React + Vite 单页界面。需要 Node.js 22.12+（建议 Node.js 24 LTS）及 npm。
依赖版本和 lockfile 已提交；首次安装需要网络，之后可本地演示。

从仓库根目录：

```sh
cd frontend
npm install
npm run dev
```

打开 `http://127.0.0.1:5173`。先按 [Backend README](../backend/README.md) 启动后端。
浏览器请求同源 `/api/brief`，Vite 默认代理到 `http://127.0.0.1:8000`；
修改目标时，在启动 Vite 前设置 `BRIEFFLOW_API_TARGET`。
端口被占用时启动会报错，不会静默切换端口。

```sh
npm test
npm run build
npm run preview
```

构建输出在 `dist/`（不提交）；preview 地址 `http://127.0.0.1:4173`，同样代理 API。
正式托管若不使用 Vite，需要自行把 `/api` 反向代理到后端；本版不包含部署。

## 页面与数据

- 自然语言需求输入、快捷示例、Generate Brief、Loading 和清晰错误反馈。
- 展示 Preference、推荐数量、高匹配数量、摘要及推荐卡片。
- 卡片保留 API 顺序，显示机构、地点、类别、Match/Priority、理由、deadline、来源。
- 高匹配计数按现有 Output Agent 的 80–100 分展示口径统计，不改动推荐评分。
- 未知日期显示“未注明”，过期项标为“已截止”。来源链接只允许 HTTP(S)。
- 没有结果时显示空状态；异常或不符合展示契约的 API 数据显示错误，不白屏。
- 请求超时 20 秒，允许重试；所有字体和静态资源本地打包，不依赖 CDN。

## Mock / Offline Demo

正常提交始终调用 API。后端使用 Mock 数据时显示 `Demo / Mock Mode · API`。
连接失败或服务器错误时**不静默伪造结果**：显示错误，用户可点“加载离线示例”。
该按钮不请求 API，展示 `src/demo-brief.json` 中固定的现有流水线响应快照，并显示
`Demo / Mock Mode · 离线示例`、快照日期和“不是对新需求的实时推荐”说明。
加载时同步展示示例需求和偏好，不把固定结果冒充用户刚输入的结果。

快照来自 2026-10-04 的现有 Mock Pipeline，9 条模拟推荐；原 `data/mock/mock_db.json`
未修改。不会在浏览器重新实现 Agent、Retrieval 或 Ranking。
离线演示仍需要本机 Vite dev/preview 提供页面；不是可脱离本机服务器的 PWA。

技术参考：[Vite Guide](https://vite.dev/guide/)。
