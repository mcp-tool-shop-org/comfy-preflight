<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.md">English</a>
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

## O espaço em que ele se encontra

> **Um pacote Comfy Cloud `dry_run` não comprova a integridade do link.**
> Uma carga útil redigitada manualmente com um link de nó auto-referenciado — `VAEDecode.samples = ["14", 0]`,
> o nó apontando para si mesmo — retornou `status: validated`.

A resposta do validador do provedor é: *este gráfico está bem formatado o suficiente para ser executado*. Ele não responde a pergunta:
*este é o gráfico que você pretendia*. Cada verificação aqui se encontra nesse espaço, e cada uma foi paga por
uma execução que passou pelo `dry_run`.

**O envio é o ato irreversível sem um verdadeiro "desfazer", e uma pré-verificação é um mecanismo de compensação que você executa
ANTES, em vez de depois.** Um trabalho na nuvem concluído é cobrado; o único mecanismo de compensação posterior é:
*cancele-o se ainda estiver na fila, caso contrário, nenhum*. Esse é todo o argumento para este pacote.

## Instalar

```bash
npx @mcptoolshop/comfy-preflight check graph.json   # no Python needed
pip install comfy-preflight                          # for the in-process gate
pip install "comfy-preflight[mcp]"                   # + the MCP stdio server
```

O iniciador npx baixa um binário deste repositório no GitHub Release e **verifica seu SHA256**
em relação aos valores de verificação no mesmo lançamento, antes de executá-lo. Python ≥ 3.11; binários para
linux-x64 e win-x64 (instalações do macOS via `pip`).

## Use-o

**O portão de produção — em processo, no caminho de envio:**

```python
from comfy_preflight import preflight

# Inside the function that submits. Not in a shell step before it.
preflight(graph, register, input_dims=(width, height))   # raises PreflightHalt
submit(graph)                                            # only reached if nothing raised
```

**A porta de desenvolvimento:**

```bash
comfy-preflight check graph.json \
  --input-dims 1072x1024 --register subject.json --saved sidecar.json --json
```

| sair | significado |
|---|---|
| `0` | nada interrompido — PASS, ADVISORY ou NOT_APPLICABLE, **cada um nomeado na saída** |
| `1` | INTERROMPER |
| `2` | **nada foi examinado** — argumentos inválidos, arquivo ilegível ou um erro interno |

As saídas ADVISORY `0` intencionalmente: um status diferente de zero interrompe uma cadeia `&&`, o que transformaria um aviso
em uma interrupção em todos os shells que a executam.

## O que ele verifica

| # | verificar | interrompe quando |
|---|---|---|
| 1 | **Link topology** | um nó de entrada lê seu próprio nó; um link para um ID de nó que não está no gráfico |
| 2 | **A verificação invertida do registro** | um registro declarado que não corresponde à construção do gráfico — **em ambas as direções** |
| 4 | **Saved-is-submitted** | o sidecar salvo e a carga útil enviada diferindo **como gráficos analisados** |
| 5 | **Generator-legal frame** | uma dimensão que o VAE do quadro efetivo não consegue decodificar |
| 8 | **Declared envelope** | **nada — ele nunca interrompe.** Fora da banda é um AVISO |

Três verificações do projeto original **não foram implementadas** e são nomeadas em vez de simplesmente ausentes: concordância entre receita e perfil (não existe uma configuração de assunto-perfil), estimativa antes do envio
(lado de transporte — nenhum operando estrutural de gráfico) e reprodução de âncora (requer o
*construtor*; o corpus contém saídas, não os scripts que as criaram).

### Verificação 2 — a que nomeia o método

Quando o registro de um assunto declara **nenhum adaptador de estilo**, a afirmação sendo feita é *não* "o
peso é 0,0". É que **não existe nenhum nó de carregador e nenhuma referência de cartão adaptador em lugar algum no
gráfico**.

> *Um peso de 0,0 não é um peso zero em um cartão carregado; é a ausência de um cartão.*

**E ele afirma a imagem espelhada.** Um peso positivo decidido com **nenhum nó de carregador** é
*silenciosamente inerte*: a execução é concluída, custa dinheiro e produz uma saída do modelo base, enquanto todas as linhas de log dizem que o adaptador foi solicitado. Essa direção não produz nenhum sinal que um humano possa notar —
o que é exatamente onde um portão justifica sua existência em vez de uma pessoa olhando.

### Verificação 5 — o quadro efetivo, não o declarado

`1066 / 8 = 133.25` codifica para 133 colunas latentes e decodifica para **1064**, colocando cada saída
2 pixels fora de sua imagem de controle e quebrando todos os pares subsequentes.

**O defeito ocorreu a montante do gráfico.** O valor 1066 foi derivado corretamente de uma malha, a
imagem foi renderizada nessa largura e carregada, e o gráfico nunca declarou isso — então, uma verificação lendo literais do gráfico não poderia ter detectado o incidente que a motiva. O operando é o
quadro que a execução realmente produzirá, que em um gráfico img2img é as dimensões da imagem de entrada.

÷8 interrompe. ÷16 avisa. Um limite e uma preferência, não dois limites.

### Verificação 8 — aviso e honesto sobre o que não pode dizer

Para cada ponto de verificação que o gráfico carrega, os parâmetros são comparados com uma tabela de envelope **citada**.
Cada entrada contém sua faixa, URL de origem, data de recuperação e uma citação das próprias palavras do cartão —
e o construtor se recusa a construir uma entrada que não corresponda.

A entrada inicial é `Qwen-Image-InstantX-ControlNet-Union`. Ela contém a
faixa `controlnet_conditioning_scale` documentada em seu cartão, e uma **ausência declarada** para desruído,
porque esse cartão não publica nenhuma faixa de desruído — verificado em relação ao cartão ativo, em vez de
relembrado. Portanto, uma execução em um gráfico em `denoise=0.92` relata o valor 0,92, nomeia o parâmetro e diz
claramente que não pode julgá-lo e por quê.

Relatar o valor que não pode julgar é a metade honesta da descoberta. Inventar uma faixa para julgá-lo
seria a metade desonesta.

## O contrato de adoção

**Chame-o de em processo no caminho de envio. Não há sinalizador de ignorar.**

*A verificação está dentro da ferramenta que executa o passo irreversível.* Uma pré-verificação em uma cadeia de shell antes do envio é um **transporte, não um guardião** — no incidente que gerou esta regra,
47.020 texels foram confirmados depois que um portão já havia sido acionado, porque uma cadeia PowerShell passou por um código de saída com falha. Ninguém decidiu prosseguir; a construção era incapaz de parar.

**A CLI e o servidor MCP são ambos transportes, não guardiões.** Ler uma INTERRUPÇÃO de qualquer um deles e
em seguida enviar de outro lugar é a mesma cadeia com uma interface melhor.

Nenhuma função aqui recebe um parâmetro `skip`, `force`, `warn_only` ou `enabled`, e os testes leem cada
assinatura em vez de confiar na documentação. **Cada portão `raise`; nenhum é um simples `assert`** —
`python -O` exclui `assert` silenciosamente, e o CI executa toda a suíte sob `-O` e
`PYTHONOPTIMIZE=1` para provar que os portões sobrevivem a isso.

## Sobre MCP

```bash
python -m comfy_preflight.mcp_server     # stdio
npx @mcptoolshop/comfy-preflight mcp     # same server, no Python required
```

Uma ferramenta, `preflight`, que retorna o mesmo resultado estruturado que a biblioteca retorna – um teste verifica a identidade dos bytes. Uma chamada HALT é uma chamada *bem-sucedida* que retorna `{"verdict": "halt", ...}`, porque reportá-la como um erro de protocolo descartaria a estrutura de que o chamador precisa.

## Segurança

Não há chamadas de rede, nem credenciais, nem telemetria e não grava nada em lugar nenhum. Lê um grafo e um perfil e retorna um resultado. Modelo completo de ameaças – dados acessados, dados *não* acessados e as permissões necessárias – em [SECURITY.md](SECURITY.md).

## Documentação

📖 **[O manual](https://mcp-tool-shop-org.github.io/comfy-preflight/handbook/)** — como começar, cada verificação em detalhe, o contrato de adoção e a tabela de envelopes.

## Licença

MIT – consulte [LICENSE](LICENSE).

<p align="center">
  Built by <a href="https://mcp-tool-shop.github.io/">MCP Tool Shop</a>
</p>
