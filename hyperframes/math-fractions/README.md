# 四年级数学教学视频 · HyperFrames 项目

## 文件结构

```
math-fractions/
├── index.html              # 视频合成主文件（6 个场景 · 40秒）
├── hyperframes.config.json # 渲染配置
├── script.txt              # 旁白脚本（TTS / 人工录音）
└── README.md
```

## 视频场景结构

| 时间 | 场景 | 内容 |
|------|------|------|
| 0–5s | 封面 | 标题动画 |
| 5–11s | 情境导入 | 分苹果问题引入 |
| 11–19s | 认识½ | 圆形切分动画 + 分数写法 |
| 19–26s | 各部分名称 | 分子/分数线/分母标注 |
| 26–34s | 更多分数 | 1/3, 2/4, 3/4, 1/2 卡片 |
| 34–40s | 知识总结 | 三卡片归纳 |

## 渲染步骤

### 1. 安装依赖

```bash
# 需要 Node.js 22+ 和 FFmpeg
brew install ffmpeg          # macOS
# 或 sudo apt install ffmpeg # Ubuntu

npm install -g hyperframes
```

### 2. 初始化并导入项目

```bash
# 将本目录放入 HyperFrames 项目
npx hyperframes init math-video
cp index.html math-video/
cp hyperframes.config.json math-video/

cd math-video
```

### 3. 预览

```bash
npx hyperframes preview
# 浏览器打开 http://localhost:3000 实时预览
```

### 4. 渲染 MP4

```bash
npx hyperframes render --output dist/math-fractions.mp4
```

### 5. 添加 TTS 旁白（可选）

```bash
# 使用 edge-tts（免费）
pip install edge-tts
edge-tts --voice zh-CN-XiaoxiaoNeural --file script.txt --write-media narration.mp3

# 合并音视频
ffmpeg -i dist/math-fractions.mp4 -i narration.mp3 \
  -c:v copy -c:a aac -shortest \
  dist/math-fractions-final.mp4
```

## 在 Claude Code 中使用

打开项目目录后，直接用自然语言指令：

```
/hyperframes 修改第3个场景，把圆形改成正方形，颜色改为蓝色
/hyperframes 在第5个场景后增加一个练习题场景
/hyperframes-cli render --fps 60
```

## 自定义建议

- **换主题**：修改 CSS 变量中的 `#ffb400`（金色）和 `#1a2d45`（深蓝）
- **换内容**：将"分数"替换为其他四年级数学单元（小数、面积等）
- **加配音**：替换 `script.txt` 内容后重新生成 TTS
