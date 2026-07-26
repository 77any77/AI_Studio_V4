# AI Studio V4

工业级 AI 漫剧生产平台。

## 当前版本

Engineering v0.1

已建立：

- 标准 Python 工程结构
- PySide6 桌面界面
- API 配置中心
- OpenAI 兼容接口客户端
- 项目保存/读取
- 小说导入
- 自动测试
- GitHub Actions Windows 自动构建 EXE
- Windows 启动冒烟测试

## 本地开发

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
python -m ai_studio
```

## 自动生成 Windows EXE

将整个项目上传到 GitHub 后：

1. 打开仓库的 `Actions`
2. 运行 `Build Windows EXE`
3. 构建结束后下载 `AI-Studio-V4-Windows`

用户电脑无需安装 Python。
