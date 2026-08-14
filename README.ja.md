<p align="center">
  <a href="README.md">English</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.pt-BR.md">Português (BR)</a>
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

## それが存在するギャップ

> **A Comfy Cloud `dry_run` PASS は、リンクの整合性を証明しません。**
> 自己参照ノードリンク（`VAEDecode.samples = ["14", 0]`、つまり、自身を指すノード）を持つ、手動で再入力されたペイロードは、`status: validated` を返します。

プロバイダーのバリデーターは、「このグラフは実行するのに十分な形式が整っているか」と答えます。それは「これはあなたが意図したグラフですか？」とは答えません。ここに存在するすべてのチェックは、そのギャップの中に存在し、それぞれは `dry_run` を通過した実行によって支払われました。

**送信は不可逆的な行為であり、実際には元に戻すことはできません。また、事前確認は、後ではなく、その前に実行する補完手段です。** クラウドジョブが完了すると料金が発生します。その後で唯一の補完手段は、「まだキューに登録されている場合はキャンセルし、それ以外の場合は何もしない」ことです。それがこのパッケージ全体の根拠です。

## インストール

```bash
npx @mcptoolshop/comfy-preflight check graph.json   # no Python needed
pip install comfy-preflight                          # for the in-process gate
pip install "comfy-preflight[mcp]"                   # + the MCP stdio server
```

npxランチャーは、このリポジトリのGitHubリリースからバイナリをダウンロードし、実行する前に、同じリリースのチェックサムと照合して**SHA256を検証します**。Python ≥ 3.11; linux-x64およびwin-x64用のバイナリ（macOSは`pip`経由でインストール）。

## 使用方法

**本番環境ゲート — プロセス内、送信パス上:**

```python
from comfy_preflight import preflight

# Inside the function that submits. Not in a shell step before it.
preflight(graph, register, input_dims=(width, height))   # raises PreflightHalt
submit(graph)                                            # only reached if nothing raised
```

**開発用ドア:**

```bash
comfy-preflight check graph.json \
  --input-dims 1072x1024 --register subject.json --saved sidecar.json --json
```

| 終了 | 意味 |
|---|---|
| `0` | 何も停止しない — PASS、ADVISORY、またはNOT_APPLICABLE。それぞれは**出力に名前が付けられています**。 |
| `1` | HALT |
| `2` | **何も検証されなかった** — 無効な引数、読み取り不可能なファイル、または内部エラー。 |

ADVISORYは、意図的にステータスコード `0` を返します。ゼロ以外のステータスは、`&&` チェーンを停止させます。これにより、アドバイザリーがすべてのシェルで実行される場合に、HALTに変わります。

## チェック対象

| # | チェック | 停止する条件 |
|---|---|---|
| 1 | **Link topology** | ノード入力が自身のノードを読み取る場合、またはグラフ内に存在しないノードIDへのリンクがある場合。 |
| 2 | **逆方向のレジスタスキャン** | 宣言されたレジスタが、グラフの構造と一致しない（**両方の方向に**）。 |
| 4 | **Saved-is-submitted** | 保存されたサイドカーと送信されたペイロードが、**解析されたグラフとして**異なる。 |
| 5 | **Generator-legal frame** | 有効なフレームのVAEがデコードできない次元。 |
| 8 | **Declared envelope** | **何も起こらない — 決して停止しない。** 帯域外はADVISORYです。 |

元の設計からの3つのチェックは**実装されておらず**、静かに欠落するのではなく、名前が付けられています：レシピとプロファイルの整合性（サブジェクト-プロファイルフィクスチャが存在しない）、送信前の見積もり（トランスポート側 — グラフ構造演算子がない）、アンカーの再現（グラフ*ビルダー*が必要。コーパスには出力が含まれており、それらを作成したスクリプトは含まれていません）。

### チェック2 — メソッドに名前を付けるもの

サブジェクトのレジスタが**スタイルアダプターを持たない**と宣言する場合、主張されているのは「重みが0.0である」ではありません。それは、**グラフ内にローダーノードもアダプターカード参照も存在しない**ということです。

> *重みが0.0であることは、ロードされたカード上のゼロの重みではなく、カードが存在しないことを意味します。*

**また、その逆も主張します。** 決定された正の重みで**ローダーノードがない**場合、それは*静かに不活性*です：実行は完了し、コストがかかり、ベースモデルの出力が生成されますが、すべてのログ行にはアダプターが要求されたことが示されています。この方向では、人間が気づくことができるシグナルは生成されません。それがまさにゲートが人による確認よりも優れている理由です。

### チェック5 — 宣言されたものではなく、有効なフレーム

`1066 / 8 = 133.25` は133個の潜在的な列にエンコードされ、**1064個**にデコードされます。これにより、すべての出力が制御画像から2ピクセルずれてしまい、後続のペアリングがすべて失敗します。

**欠陥はグラフの上流で発生しました。** 1066はメッシュから正しく導き出され、画像はその幅でレンダリングされてアップロードされ、グラフではそれが宣言されませんでした。したがって、グラフリテラルを読み取るチェックでは、それを動機付けるインシデントを検出することはできませんでした。オペランドは、実行が実際に生成するフレームであり、img2imgグラフでは入力画像の寸法です。

÷8で停止します。÷16でアドバイスします。下限と優先順位であり、2つの下限ではありません。

### チェック8 — アドバイザリーであり、言えないことについても正直です

グラフがロードする各チェックポイントについて、パラメータは**引用された**エンベロープテーブルと比較されます。すべてのエントリには、バンド、ソースURL、取得日、およびカード自体の言葉の引用が含まれており、コンストラクターはそれらのいずれかが存在しないエントリを構築することを拒否します。

初日のエントリは`Qwen-Image-InstantX-ControlNet-Union`です。それは、そのカードが文書化している`controlnet_conditioning_scale`バンドを持ち、また、ノイズ除去範囲がないことを**宣言しています**。これは、そのカードがノイズ除去範囲を一切公開していないためであり、ライブカードに対して検証され、再利用されるものではありません。したがって、`denoise=0.92`でグラフを実行すると、0.92が報告され、パラメータの名前が付けられ、判断できないこととその理由が明確に述べられます。

判断できない値を報告することが、この発見の正直な部分です。それを判断するためにバンドを発明することは、不誠実な部分になります。

## 導入契約

**送信パス上でプロセス内として呼び出します。スキップフラグはありません。**

*チェックは、不可逆的なステップを実行するツール内に存在します。* 送信する前にシェルチェーンで事前確認を行うことは、**トランスポートであり、ガードではありません**。このルールを生成したインシデントでは、47,020テクセルが、ゲートがすでに発動した後でコミットされました。これは、PowerShellチェーンが無効な終了コードを通過したためです。誰も続行することを決定したわけではなく、構築は停止できませんでした。

**CLIとMCPサーバーの両方がトランスポートであり、ゲートではありません。** どちらかからHALTを読み取り、別の場所から送信することは、より優れたインターフェースを備えた同じチェーンです。

この関数は、`skip`、`force`、`warn_only`、または`enabled`パラメータを受け取ることはなく、テストは各シグネチャを読み取り、ドキュメントを信頼しません。**すべてのゲートは`raise`されます。いずれも単なる`assert`ではありません** — `python -O` は `assert` を静かに削除し、CIは完全なスイートを `-O` および `PYTHONOPTIMIZE=1` の下で実行して、ゲートがそれを生き残らせることを証明します。

## MCP経由

```bash
python -m comfy_preflight.mcp_server     # stdio
npx @mcptoolshop/comfy-preflight mcp     # same server, no Python required
```

あるツール、`preflight`は、ライブラリが返すのと同じ構造化された結果を返します。これは、バイト単位での同一性を検証するテストです。HALTは、`{"verdict": "halt", ...}`を返す*成功した*呼び出しであり、プロトコルエラーとして報告すると、呼び出し元が必要とする構造が無駄になってしまうためです。

## セキュリティ

ネットワークへのアクセスはなく、認証情報もテレメトリデータも送信せず、どこにも何も書き込みません。グラフとプロファイルを読み取り、結果を返します。完全な脅威モデル（触れられたデータ、触れられていないデータ、必要な権限）は、[SECURITY.md](SECURITY.md)に記載されています。

## ドキュメント

📖 **[ハンドブック](https://mcp-tool-shop-org.github.io/comfy-preflight/handbook/)** — 導入方法、各チェックの詳細、導入契約、およびエンベロープテーブル。

## ライセンス

MIT — [LICENSE](LICENSE)を参照してください。

<p align="center">
  Built by <a href="https://mcp-tool-shop.github.io/">MCP Tool Shop</a>
</p>
