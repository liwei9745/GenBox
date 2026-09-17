# 精准改图网关协议调研

日期：2026-09-11
范围：Vel 哇浪 AI、Klong API、Google Gemini 原生接口、OpenAI Images API，以及 LiteLLM 的统一图片编辑抽象。
限制：本次只阅读公开文档，未读取私有 Provider 配置，未发起真实请求，未消耗付费额度。

## 结论摘要

1. 文生图成功只能证明当前端点的文生图路由和该模型的生成请求可用，不能推导图片编辑、输入图片编码、蒙版或尺寸参数也可用。
2. “模型名”和“协议”必须分开建模。同一个聚合 Provider 可以承载不同模型和不同协议，但必须按当前模型解析请求，不得把 Provider 级 `endpoint_type` 强行套给所有模型。
3. 用户体验应默认沿用文生图的模型端点、精确模型 ID 和协议解析；已有明确的精准改图配置继续保留。旧成功记录缺少出站模型和协议字段，不能冒充“已成功协议缓存”。高级覆盖只修改当前模型，不改变同 Provider 的 GPT 配置。
4. 尺寸目录独立于传输协议。协议决定请求地址和请求体；模型目录决定尺寸档位、宽高比、质量映射和最终输出校验。
5. 前置检查可以验证路由、字段、编码和本地尺寸映射，但不能在零成本情况下保证上游编辑成功。真实验证必须作为单独的“一次试用”，不自动轮换协议、不自动重试付费 POST。

## 网关文档证据

### Vel 哇浪 AI

来源：[Vel API 图像接口文档](https://docs.velapi.cc/#image)，访问日期 2026-09-11。

公开文档将图片编辑统一放在：

```text
POST https://api.velapi.cc/v1/images/edits
Content-Type: application/json
```

文档列出以下模型能力：

- `nano-banana-2-2k`、`nano-banana-2-2k-sp`、`nano-banana-2-4K`：文生图使用 `/v1/images/generations`，图生图/编辑使用 `/v1/images/edits`。
- Nano Banana 2 编辑请求与 GPT 形式相同：`model`、`image`、`prompt`，`mask` 可选。
- `image` 可以是服务端可下载的 URL 或 Base64；响应为 `data[].url`，并支持 `response_format=url|b64_json`。
- `size` 可以传任意 `WxH`，服务端会就近匹配宽高比和尺寸档；`quality` 使用 `standard|low`、`medium`、`high|hd|ultra` 映射不同分辨率档。
- 文档同时注明 `/v1/responses` 对该 Nano Banana 2 变体暂不可用，并要求以 GET `/v1/models` 和实际返回为准。

文档中的编辑结构可抽象为：

```json
{
  "model": "nano-banana-2-2k",
  "image": "https://public.example/input.png",
  "prompt": "改成夜景，保留主体和构图",
  "mask": "https://public.example/mask.png",
  "size": "1792x1024",
  "quality": "medium",
  "response_format": "url"
}
```

注意：这是 Vel 文档声明的 JSON 网关契约，不代表所有 OpenAI 兼容网关都接受同样的字段。尤其是服务端下载 URL 的要求，与客户端直接上传 multipart 文件是两种不同的输入路径。

### Klong API

来源：[Klong Nano Banana 文档](https://docs.klong.lat/docs/image/nano-banana)，访问日期 2026-09-11。

Klong 文档明确把两组入口分开，不能只根据“Nano Banana”文字猜测：

| 模型 ID | 协议 | 编辑入口 |
|---|---|---|
| `nano-banana2`、`nano-banana-pro` | OpenAI Images API（NewAPI 中转） | `POST /v1/images/edits` |
| `gemini-3.1-flash-image-preview`、`gemini-3-pro-image-preview` | Gemini 原生 | `POST /v1beta/models/{model}:generateContent` |

Klong 特别警告：`nano-*` 不要送到 Gemini URL，`gemini-*` 不要送到 OpenAI Images API。这是本项目“模型 ID 与协议映射必须独立”的直接证据。

Klong 的 OpenAI 兼容编辑支持两种请求形态：

1. `multipart/form-data`：`model`、`prompt`、`response_format` 和 `image=@file`。
2. JSON：`image`、`image_url`、`images`、`reference_images` 作为兼容字段；单张可以是字符串，多张可以是数组；文档还声明接受 URL 或 Data URL。

自动适配优先采用 multipart 单张原图，避免把 Klong 的可选 JSON 兼容字段误当成唯一契约；JSON 仍可通过当前模型的显式高级覆盖选择。

示例：

```json
{
  "model": "nano-banana-pro",
  "prompt": "换成夜景背景",
  "image": [
    "https://public.example/a.png",
    "https://public.example/b.png"
  ],
  "size": "2K"
}
```

该文档把 `size` 定义为像素尺寸、宽高比或档位（例如 `1024x1024`、`16:9`、`2K`），并强调最终尺寸以返回图片为准。

Klong 的 Gemini 原生编辑应采用 Gemini `contents[].parts[]`，图片作为 `inline_data`，尺寸与比例放在 `generationConfig.imageConfig`。其原生路径不是 OpenAI 的 `image` 表单字段。

## 官方协议对照

### OpenAI Images 编辑

来源：[OpenAI Images API reference](https://developers.openai.com/api/reference/resources/images)，访问日期 2026-09-11。

- 编辑方法是 `/images/edits`，输入是图片、提示词以及可选蒙版等编辑参数。
- 典型输出是 Images 响应中的 `data[]`，可返回 `url` 或 `b64_json`。
- 尺寸、质量和响应格式是协议参数，但具体可用值仍由实际模型或网关决定。

因此 OpenAI 兼容适配器至少要明确：

```text
transport = openai_images
edit_input = multipart_file | json_url | json_data_url
model_field = model
prompt_field = prompt
image_field = image (or gateway-declared alias)
mask_field = mask (optional)
size_field = size (when model/gateway declares it)
quality_field = quality (when model/gateway declares it)
```

不能看到 `endpoint_type=openai` 就默认所有模型都支持同一个 `image` 编码和 `size` 语义。

### Gemini 原生 GenerateContent

来源：[Google Gemini image generation](https://ai.google.dev/gemini-api/docs/image-generation) 与 [GenerateContent API](https://ai.google.dev/api/generate-content)，访问日期 2026-09-11。

Gemini 图片编辑是“文本 + 图片到图片”。请求通常将文本和图片放在同一轮 `contents[].parts[]` 中：

```json
{
  "contents": [
    {
      "role": "user",
      "parts": [
        { "text": "把背景改成夜景，保留主体" },
        {
          "inline_data": {
            "mime_type": "image/png",
            "data": "<base64-without-data-url-prefix>"
          }
        }
      ]
    }
  ],
  "generationConfig": {
    "responseModalities": ["IMAGE"],
    "imageConfig": {
      "aspectRatio": "16:9",
      "imageSize": "2K"
    }
  }
}
```

原生 Gemini 的图片数据和 OpenAI multipart 文件不是同一层协议；适配器需要负责 MIME、Base64、`inline_data`、响应 parts 中图片数据的解析，以及 `aspectRatio`/`imageSize` 的模型级映射。

## LiteLLM / 成熟统一抽象的借鉴

来源：[LiteLLM image edits](https://docs.litellm.ai/docs/image_edits) 和 [LiteLLM image generation](https://docs.litellm.ai/docs/image_generation)，访问日期 2026-09-11。

LiteLLM 的做法值得借鉴：

- 对外提供统一的 `image_edit` 调用，但内部按 provider/model 选择适配器。
- 同一抽象支持单图、多图、蒙版和不同返回格式。
- Gemini 支持需要单独的 provider 适配，不是把 Gemini 当成 OpenAI multipart 的简单别名。
- `size`、`quality` 等公共参数可以映射到不同厂商的 `aspect_ratio`、`image_size`，映射失败应暴露为能力差异，而不是静默丢弃。
- 统一响应格式便于 GenBox 做严格输出校验，但不应抹去原始 provider、模型和协议证据。

这支持 GenBox 采用“统一任务契约 + 明确内部适配器”的方向，但不能把 LiteLLM 的支持列表当成目标网关实际能力证明。

## 建议的两套用户方案

### 方案 A：自动跟随文生图配置（默认）

用户只选择现有 Provider、模型和尺寸预设。系统解析当前端点配置，结合精确网关域名和模型的文档化编辑配方：

```text
selected_provider
selected_model
resolved_transport
resolved_outbound_model
resolved_size_family
```

前端只显示简洁状态，例如：

```text
自动接入：OpenAI Images · nano-banana-2-2k
```

如果模型有明确的编辑能力目录，则显示已授权尺寸；如果只有文档候选，仍须用户逐项授权试用，不能误报为已支持。当前实现不把历史成功记录当成协议发现服务。

### 方案 B：手动切换协议（高级）

用户显式打开“高级协议”后，才允许切换：

- `自动跟随文生图`
- `OpenAI Images 兼容`
- `Gemini 原生`
- 后续增加 `Qwen`、`豆包/Seedream` 等原生适配器

每个协议选项应带模型约束和输入格式说明。例如当前模型是 `nano-banana-2-2k` 时，默认采用网关文档对应的 OpenAI Images；手动 Gemini 仅适用于明确支持原生协议的端点。界面显示当前实际接入方式，不把模型品牌直接等同于协议。

手动应用形成一条只属于当前模型的覆盖记录：

```text
provider_id + endpoint_revision + exact_model
  -> protocol_override + input_profile + size_family
```

恢复操作必须保留，且恢复为“文生图自动跟随”而不是不可逆地删除状态。应用、恢复、检查配置三个动作应合并成易懂的状态流：

```text
查看当前配置 -> 检查配置 -> 应用覆盖 -> 恢复自动跟随
```

## 前置检查与试用边界

建议分三层：

1. **本地零请求检查**：图片 MIME、Base64/Data URL 前缀、文件大小、蒙版尺寸、目标尺寸映射、模型 ID 与协议白名单。
2. **只读能力检查**：在网关明确支持时读取 `/v1/models` 或文档化能力元数据；GET/OPTIONS/path 探测不能证明图片编辑一定可用。
3. **一次真实试用**：用户确认后提交一个确定的编辑请求，绑定当前 Provider、端点配置版本、模型、协议、输入 profile、尺寸族和目标尺寸。一次失败只记录本次证据，不自动换协议重试。

错误应按证据分类：

- `503`、超时、网关限流：服务或路由暂不可判定，不标记为尺寸不支持。
- `400`：记录规范化错误和响应摘要，只有明确字段错误时才建议修改 profile。
- 返回成功但输出尺寸不符：严格校验失败，不能把结果当成目标尺寸成功。
- 缺失图片或解析不到 `data[].url`/`b64_json`/Gemini inline image：协议响应解析失败。

## 对当前 Nano Banana 目标的判断

对于现有 Provider “GPT Image 2” 中的 `nano-banana-2-2k`：

- **可以继续使用同一个 Provider**，Provider 名称本身不决定协议。
- 若该网关遵循 Vel 文档，优先验证 OpenAI Images `/v1/images/edits`，JSON URL/Data URL 或网关要求的 multipart 之一。
- 若该网关遵循 Klong 的 `gemini-*` 规则，不能把 `nano-banana-2-2k` 改写为 Gemini 原生模型路径；应继续使用其 OpenAI Images 兼容入口。
- 当前文生图成功是有价值的路由线索，但不是编辑成功证据。编辑试用前仍需确认输入字段、图片编码和模型出站别名。
- 不应因为一次 `Invalid data URL` 就把模型永久判为不支持，也不应因为一次成功就永久声明所有尺寸可用。

## 实施顺序

1. 先把文生图实际生效的 `transport/profile/outbound_model` 暴露为只读解析结果，精准改图默认复用。
2. 建立模型级协议覆盖和独立尺寸族，保留 GPT 已有授权、成功证据和严格输出校验。
3. 将当前隐藏的请求格式、图片文字等高级字段折叠为“高级协议设置”，默认显示当前自动解析结果。
4. 修复模型尺寸预设的受控状态更新，切换模型或协议时只刷新当前模型的尺寸目录，绝不覆盖另一模型记录。
5. 增加零请求检查器和一次试用确认；日志显示协议、编辑入口、输入 profile、目标尺寸和实际输出尺寸的脱敏摘要。
6. 先在 `nano-banana-2-2k` 上人工验收，再扩展 Gemini 原生、Qwen、豆包/Seedream 原生适配。

本调研不授权真实请求，也没有修改运行中的 Provider 配置。
