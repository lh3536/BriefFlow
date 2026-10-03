# BriefFlow Backend

Python 3.10+。在仓库根目录创建虚拟环境、安装 Web API 及测试依赖：

```sh
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.api:app --reload --host 127.0.0.1 --port 8000
```

- API：`POST http://127.0.0.1:8000/api/brief`
- 请求：`{"user_text": "我是金融专业大三学生，帮我找粤港澳金融实习，不要销售岗。"}`
- 成功响应：原 `run_brief_flow(user_text)` 的结果，不重新计算或修改推荐数据。
- 空白、非字符串、缺字段、超出 2000 字符等请求返回 422；流水线异常返回 500 和
  `Unable to generate brief. Please try again.`，服务继续运行。
- 健康检查：`GET /api/health`；交互文档：`http://127.0.0.1:8000/docs`。

现有终端入口保持不变：`python backend/main.py`。
Router、Input/Output Agent、Retrieval 和 Ranking 业务代码均未改动。

默认 Retrieval 为 `mock`，无需互联网或 API Key。启动服务器前可设置
`BRIEFFLOW_RETRIEVAL_MODE=database` 或 `web`，具体见
[Retrieval 文档](../docs/RETRIEVAL_DATABASE.md)。前端会对 Mock 来源明确标注。

前端开发服务器通过同源 `/api` 代理到本 API，不需要放开跨域访问。
本版是本机 Demo，不含鉴权或生产部署设置；默认仅监听 loopback。

测试与验证（虚拟环境激活后）：

```sh
python -m unittest discover -s tests -v
python data/validation/validate_mock_data.py
python backend/main.py
```

技术参考：[FastAPI TestClient](https://fastapi.tiangolo.com/tutorial/testing/)。
