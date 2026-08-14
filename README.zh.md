<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.md">English</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.pt-BR.md">Português (BR)</a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/mcp-tool-shop-org/brand/main/logos/comfy-preflight/readme.png" alt="comfy-preflight" width="600">
</p>

<p align="center">
  <a href="https://github.com/mcp-tool-shop-org/comfy-preflight/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/comfy-preflight/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT License"></a>
  <a href="https://mcp-tool-shop-org.github.io/comfy-preflight/"><img src="https://img.shields.io/badge/landing%20page-live-2ea043" alt="Landing page"></a>
</p>

<p align="center">
  <strong>A gate that runs on a ComfyUI workflow graph in the seconds before it is submitted,</strong><br>
  and halts a submission that would spend credits producing a known-wrong result.<br>
  It does not submit. It does not fix your graph.
</p>

---

## 它所处的差距

> **“Comfy Cloud `dry_run` PASS”并不能证明链接的合理性。**
> 一个手动重新输入的有效载荷，其中包含一个自引用节点链接——`VAEDecode.samples = ["14", 0]`，即该节点指向自身——返回了`status: validated`。

提供商的验证器回答的是：*这个图是否结构良好到足以运行？* 它不会回答：*这是你想要运行的图吗？* 这里的每个检查都存在于那个差距中，并且每一个都由一次成功通过`dry_run`的运行所支付。

**提交是一个不可逆的操作，没有真正的撤销功能，而预检是一个补偿机制，你应该在提交之前而不是之后运行。** 完成后的云作业会产生费用；之后唯一的补偿措施是：*如果它仍在排队中，则取消它，否则就没有了。* 这就是这个软件包的全部论点。

## 安装

```bash
npx @mcptoolshop/comfy-preflight check graph.json   # no Python needed
pip install comfy-preflight                          # for the in-process gate
pip install "comfy-preflight[mcp]"                   # + the MCP stdio server
```

npx 启动器从该存储库的 GitHub 发布版下载一个二进制文件，并在运行之前，**验证其 SHA256 值是否与发布版中的校验和匹配。** Python ≥ 3.11；适用于 linux-x64 和 win-x64 的二进制文件（macOS 通过 `pip` 安装）。

## 使用它

**生产环境的门控——在提交路径中进行：**

```python
from comfy_preflight import preflight

# Inside the function that submits. Not in a shell step before it.
preflight(graph, register, input_dims=(width, height))   # raises PreflightHalt
submit(graph)                                            # only reached if nothing raised
```

**开发环境的入口：**

```bash
comfy-preflight check graph.json \
  --input-dims 1072x1024 --register subject.json --saved sidecar.json --json
```

| 退出 | 含义 |
|---|---|
| `0` | 没有停止——PASS、ADVISORY（建议）或 NOT_APPLICABLE（不适用），**每个都在输出中命名。** |
| `1` | HALT（停止） |
| `2` | **没有任何内容被检查**——参数错误、无法读取的文件，或者内部错误。 |

ADVISORY 退出时会故意返回 `0`：非零状态会停止一个 `&&` 链，这会将建议变成在每个运行它的 shell 中的停止操作。

## 它检查的内容

| # | 检查 | 停止于 |
|---|---|---|
| 1 | **Link topology** | 一个节点输入读取其自身的节点；链接到一个不在图中的节点 ID。 |
| 2 | **反向注册扫描** | 声明的注册与图的构建不匹配——**双向检查。** |
| 4 | **Saved-is-submitted** | 保存的辅助文件和提交的有效载荷不同——**以解析后的图形形式。** |
| 5 | **Generator-legal frame** | 一个维度，有效的框架的 VAE 无法解码。 |
| 8 | **Declared envelope** | **没有任何内容——它永远不会停止。** 非同步操作是一个 ADVISORY（建议）。 |

原始设计中的三个检查**没有被构建**，而是以名称的形式呈现，而不是默默地缺失：配方与配置文件的匹配（不存在主题-配置文件固定），提交前估计（传输端——没有图结构化操作数）和锚点重现（需要图形*构建器*；语料库包含输出，而不是生成它们的脚本）。

### 检查 2——命名该方法的检查

当一个主题的注册声明**没有样式适配器**时，所断言的内容*不是*“权重为 0.0”。而是说**图中不存在任何加载器节点和适配器卡引用。**

> *权重为 0.0 并不是已加载卡上的零权重；而是没有卡。*

**并且它断言了镜像图像。** 一个具有**没有加载器节点**的明确正权重的适配器是*默默地无效的*：运行完成，产生费用，并生成基本模型输出，而每条日志都表明请求了适配器。这种方向不会产生人类可以注意到的信号——这正是门控机制胜过人工检查的地方。

### 检查 5——有效的框架，而不是声明的框架

`1066 / 8 = 133.25` 编码为 133 个潜在列并解码为**1064**，使每个输出都与其控制图像相差 2 像素，并破坏了所有下游配对。

**缺陷发生在图形的上游。** 1066 是从一个网格正确派生的，图像以该宽度渲染并上传，并且图从未声明它——因此，读取图形字面量的检查无法捕获导致它的事件。操作数是运行将实际生成的框架，在 img2img 图中，它是输入图像的尺寸。

÷8 停止。÷16 建议。一个下限和一个偏好，而不是两个下限。

### 检查 8——建议，并且诚实地说明了它无法说明的内容

对于图加载的每个检查点，参数都会与**引用的**包络表进行比较。每个条目都包含其范围、来源 URL、检索日期以及卡片自身文字的引用——并且构造器拒绝构建不包含这些内容的条目。

第一天的条目是 `Qwen-Image-InstantX-ControlNet-Union`。它包含了其卡片记录的 `controlnet_conditioning_scale` 范围，并声明了 denoise 的**缺失**，因为该卡片根本没有发布任何 denoise 范围——而是与实时卡进行验证，而不是回忆。因此，在 `denoise=0.92` 上运行一个图会报告 0.92，命名参数，并明确说明它无法判断它以及原因。

报告它无法判断的值是该发现的诚实部分。为了判断它而发明一个范围将是不诚实的部分。

## 采用协议

**在提交路径中将其称为正在进行的操作。没有跳过标志。**

*检查存在于执行不可逆步骤的工具内部。* 在提交之前进行的预检是一个传输，而不是一个保护——在本规则产生事件中，47,020 个像素被提交，因为 PowerShell 链绕过了失败的退出代码，而门控机制已经触发。没有人决定继续；该构造无法停止。

**CLI 和 MCP 服务器都是传输，而不是门控。** 从两者读取 HALT 并从其他地方进行提交是具有更好界面的相同链。

这里没有函数接受 `skip`、`force`、`warn_only` 或 `enabled` 参数，并且测试会读取每个签名，而不是信任文档。**每个门控都会 `raise`；没有一个是裸 `assert`——** `python -O` 会静默地删除 `assert`，并且 CI 在 `-O` 和 `PYTHONOPTIMIZE=1` 下运行整个套件，以证明门控机制可以承受它。

## 通过 MCP

```bash
python -m comfy_preflight.mcp_server     # stdio
npx @mcptoolshop/comfy-preflight mcp     # same server, no Python required
```

一个工具，`preflight`，返回与库返回的相同结构化的结果——测试会验证字节是否完全一致。HALT 是一个*成功的*调用，它返回 `{"verdict": "halt", ...}`，因为将其报告为协议错误会导致丢弃调用方所需的数据结构。

## 安全性

不进行任何网络调用，不使用任何凭据，不收集任何遥测数据，并且不会在任何地方写入任何内容。它读取一个图和一个配置文件，并返回一个结果。完整的威胁模型——涉及的数据、未涉及的数据以及所需的权限——请参见 [SECURITY.md](SECURITY.md)。

## 文档

📖 **[手册](https://mcp-tool-shop-org.github.io/comfy-preflight/handbook/)**——入门指南、每个检查的详细说明、采用协议和数据表。

## 许可证

MIT——请参见 [LICENSE](LICENSE)。

<p align="center">
  Built by <a href="https://mcp-tool-shop.github.io/">MCP Tool Shop</a>
</p>
