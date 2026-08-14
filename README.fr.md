<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.md">English</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.pt-BR.md">Português (BR)</a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/mcp-tool-shop-org/brand/main/logos/comfy-preflight/readme.png" alt="comfy-preflight" width="600">
</p>

<p align="center">
  <a href="https://github.com/mcp-tool-shop-org/comfy-preflight/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/comfy-preflight/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://pypi.org/project/comfy-preflight/"><img src="https://img.shields.io/pypi/v/comfy-preflight?color=3775a9&label=pypi" alt="PyPI"></a>
  <a href="https://www.npmjs.com/package/@mcptoolshop/comfy-preflight"><img src="https://img.shields.io/npm/v/@mcptoolshop/comfy-preflight?color=cb3837&label=npm" alt="npm"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT License"></a>
  <a href="https://mcp-tool-shop-org.github.io/comfy-preflight/"><img src="https://img.shields.io/badge/landing%20page-live-2ea043" alt="Landing page"></a>
</p>

<p align="center">
  <strong>A gate that runs on a ComfyUI workflow graph in the seconds before it is submitted,</strong><br>
  and halts a submission that would spend credits producing a known-wrong result.<br>
  It does not submit. It does not fix your graph.
</p>

---

## L'écart dans lequel il se trouve

> **Un PASS de Comfy Cloud `dry_run` ne prouve pas la cohérence du lien.**
> Une charge utile retapée manuellement avec un lien de nœud autoréférentiel — `VAEDecode.samples = ["14", 0]`,
> le nœud pointant vers lui-même — a renvoyé `status: validated`.

La réponse du validateur du fournisseur est : *ce graphe est-il suffisamment bien formé pour être exécuté ?* Il ne répond pas à la question :
*est-ce le graphe que vous vouliez ?* Chaque vérification ici se situe dans cet écart, et chacune a été payée par
une exécution qui a réussi `dry_run`.

**La soumission est l'acte irréversible sans possibilité de retour en arrière réel, et un test préliminaire est une mesure compensatoire que vous effectuez
AVANT plutôt qu'après.** Un travail cloud terminé est facturé ; la seule mesure compensatoire par la suite est :
*annulez-le s'il est toujours en file d'attente, sinon aucune.* C'est tout l'argument de ce paquet.

## Installation

```bash
npx @mcptoolshop/comfy-preflight check graph.json   # no Python needed
pip install comfy-preflight                          # for the in-process gate
pip install "comfy-preflight[mcp]"                   # + the MCP stdio server
```

Le lanceur npx télécharge un binaire à partir du dépôt GitHub Release et **vérifie son SHA256**
par rapport aux sommes de contrôle dans cette même version avant de l'exécuter. Python ≥ 3.11 ; binaires pour
linux-x64 et win-x64 (installation sur macOS via `pip`).

## Utilisation

**La porte de production — en cours, sur le chemin de soumission :**

```python
from comfy_preflight import preflight

# Inside the function that submits. Not in a shell step before it.
preflight(graph, register, input_dims=(width, height))   # raises PreflightHalt
submit(graph)                                            # only reached if nothing raised
```

**La porte du développement :**

```bash
comfy-preflight check graph.json \
  --input-dims 1072x1024 --register subject.json --saved sidecar.json --json
```

| sortie | signification |
|---|---|
| `0` | rien n'a été interrompu — PASS, ADVISORY ou NOT_APPLICABLE, **chacun étant nommé dans la sortie** |
| `1` | INTERRUPTION |
| `2` | **rien n'a été examiné** — arguments incorrects, fichier illisible ou erreur interne |

Les sorties ADVISORY renvoient `0` intentionnellement : un statut différent de zéro arrête une chaîne `&&`, ce qui transformerait un avertissement
en interruption dans chaque shell qui l'exécute.

## Ce qu'il vérifie

| # | vérification | interrompt si |
|---|---|---|
| 1 | **Link topology** | une entrée de nœud lit son propre nœud ; un lien vers un ID de nœud qui n'est pas dans le graphe |
| 2 | **L'analyse inversée du registre** | un registre déclaré qui ne correspond pas à la construction du graphe — **dans les deux sens** |
| 4 | **Saved-is-submitted** | la divergence entre l'effet secondaire enregistré et la charge utile soumise **en tant que graphes analysés** |
| 5 | **Generator-legal frame** | une dimension pour laquelle le VAE du cadre effectif ne peut pas décoder |
| 8 | **Declared envelope** | **rien — il n'interrompt jamais.** Hors bande est un AVERTISSEMENT |

Trois vérifications de la conception originale **ne sont pas implémentées**, et sont nommées plutôt que simplement absentes : accord recette-vs-profil (il n'existe pas d'élément sujet-profil), estimation avant soumission
(côté transport — aucun opérande structurel du graphe) et reproduction de l'ancre (nécessite le graphe
*constructeur* ; le corpus contient des sorties, pas les scripts qui les ont créées).

### Vérification 2 — celle qui nomme la méthode

Lorsqu'un registre de sujet déclare **aucun adaptateur de style**, l'affirmation est *pas* : « le
poids est de 0,0 ». Il s'agit plutôt du fait qu'**il n'existe aucun nœud de chargeur et aucune référence de carte d'adaptateur nulle part dans le
graphe**.

> *Un poids de 0,0 n'est pas un poids nul sur une carte chargée ; c'est l'absence de carte.*

**Et il affirme l'image miroir.** Un poids positif décidé avec **aucun nœud de chargeur** est
*silencieusement inerte* : l'exécution se termine, coûte de l'argent et produit une sortie du modèle de base tandis que chaque ligne de journal indique que l'adaptateur a été demandé. Cette direction ne produit aucun signal qu'un humain pourrait remarquer —
ce qui explique pourquoi une porte mérite sa place par rapport à une personne qui examine les données.

### Vérification 5 — le cadre effectif, et non celui déclaré

`1066 / 8 = 133.25` est encodé en 133 colonnes latentes et décodé en **1064**, ce qui déplace chaque sortie
de 2 pixels par rapport à son image de contrôle et perturbe tous les appariements suivants.

**Le défaut s'est produit en amont du graphe.** Le 1066 a été dérivé correctement d'un maillage,
l'image a été rendue avec cette largeur et téléchargée, et le graphe ne l'a pas déclaré — donc une vérification lisant les littéraux du graphe n'aurait pas pu détecter l'incident qui la motive. L'opérande est le
cadre que l'exécution produira réellement, ce qui, dans un graphe img2img, correspond aux dimensions de l'image d'entrée.

÷8 interrompt. ÷16 avertit. Un seuil et une préférence, pas deux seuils.

### Vérification 8 — avertissement, et honnête quant à ce qu'elle ne peut pas dire

Pour chaque point de contrôle que le graphe charge, les paramètres sont comparés à une **table d'enveloppe citée**.
Chaque entrée contient sa bande, son URL source, sa date de récupération et une citation des propres mots de la carte —
et le constructeur refuse de créer une entrée qui ne le fait pas.

L'entrée du premier jour est `Qwen-Image-InstantX-ControlNet-Union`. Elle contient la
bande `controlnet_conditioning_scale` que sa carte documente, et une **absence déclarée** pour le débruitage,
parce que cette carte ne publie aucune plage de débruitage — vérifié par rapport à la carte active plutôt que récupéré. Ainsi, une exécution sur un graphe à `denoise=0.92` signale le 0,92, nomme le paramètre et indique
clairement qu'elle ne peut pas le juger et pourquoi.

Signaler la valeur qu'elle ne peut pas juger est la moitié honnête de la découverte. Inventer une bande pour la juger
serait la moitié malhonnête.

## Le contrat d'adoption

**Appelez-le en cours sur le chemin de soumission. Il n'y a pas de drapeau d'omission.**

*La vérification se trouve dans l'outil qui effectue l'étape irréversible.* Un test préliminaire dans une chaîne shell avant une soumission est un **transport, et non une protection** — dans l'incident qui a donné lieu à cette règle,
47 020 texels ont été validés après qu'une porte s'était déjà déclenchée, car une chaîne PowerShell avait contourné un code de sortie d'échec. Personne n'a décidé de continuer ; la construction était incapable de s'arrêter.

**L'interface de ligne de commande et le serveur MCP sont tous deux des transports, et non des portes.** Lire une INTERRUPTION à partir de l'un ou l'autre et ensuite soumettre depuis un autre endroit est la même chaîne avec une interface plus agréable.

Aucune fonction ici ne prend un paramètre `skip`, `force`, `warn_only` ou `enabled`, et les tests lisent chaque
signature plutôt que de se fier à la documentation. **Chaque porte `raise` ; aucune n'est une simple `assert`** —
`python -O` supprime `assert` silencieusement, et CI exécute toute la suite sous `-O` et
`PYTHONOPTIMIZE=1` pour prouver que les portes survivent à cela.

## Sur MCP

```bash
python -m comfy_preflight.mcp_server     # stdio
npx @mcptoolshop/comfy-preflight mcp     # same server, no Python required
```

Un outil, `preflight`, renvoie le même résultat structuré que la bibliothèque – un test vérifie l’identité des octets. Un HALT est un appel *réussi* qui renvoie `{"verdict": "halt", ...}`, car signaler cela comme une erreur de protocole entraînerait la perte de la structure dont l’appelant a besoin.

## Sécurité

Aucun appel réseau, aucun identifiant, aucune télémétrie, et il n’écrit rien nulle part. Il lit un graphe et un profil, et renvoie un verdict. Modèle de menace complet – données utilisées, données *non* utilisées, et permissions requises – dans [SECURITY.md](SECURITY.md).

## Documentation

📖 **[Le manuel](https://mcp-tool-shop-org.github.io/comfy-preflight/handbook/)** – prise en main, chaque vérification en détail, le contrat d’adoption (du produit) et le tableau des enveloppes.

## Licence

MIT – voir [LICENSE](LICENSE).

<p align="center">
  Built by <a href="https://mcp-tool-shop.github.io/">MCP Tool Shop</a>
</p>
