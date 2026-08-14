<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.md">English</a> | <a href="README.pt-BR.md">Português (BR)</a>
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

## Lo spazio in cui opera

> **Un PASS di `dry_run` di Comfy Cloud non dimostra la correttezza del collegamento.**
> Un payload riscritto manualmente con un collegamento di nodo autoreferenziale — `VAEDecode.samples = ["14", 0]`,
> il nodo che punta a se stesso — ha restituito `status: validated`.

La risposta del validatore del fornitore è: *questo grafico è sufficientemente ben formato per essere eseguito*. Non risponde a
*è questo il grafico che intendevi*. Ogni controllo qui opera in quello spazio e ciascuno di essi è stato pagato da
un'esecuzione che ha superato `dry_run`.

**L'invio è l'azione irreversibile senza una vera possibilità di annullamento, e un pre-controllo è un meccanismo compensativo che si esegue
PRIMA invece che dopo.** Un job cloud completato viene fatturato; l'unico meccanismo compensativo successivo è
*annullalo se è ancora in coda, altrimenti nessuno*. Questo è l'intero argomento a favore di questo pacchetto.

## Installa

```bash
npx @mcptoolshop/comfy-preflight check graph.json   # no Python needed
pip install comfy-preflight                          # for the in-process gate
pip install "comfy-preflight[mcp]"                   # + the MCP stdio server
```

Il launcher npx scarica un file binario dal repository GitHub Release e **verifica il suo SHA256**
rispetto ai checksum nello stesso release prima di eseguirlo. Python ≥ 3.11; file binari per
linux-x64 e win-x64 (l'installazione su macOS avviene tramite `pip`).

## Usalo

**Il controllo di produzione — in corso, nel percorso di invio:**

```python
from comfy_preflight import preflight

# Inside the function that submits. Not in a shell step before it.
preflight(graph, register, input_dims=(width, height))   # raises PreflightHalt
submit(graph)                                            # only reached if nothing raised
```

**La porta di sviluppo:**

```bash
comfy-preflight check graph.json \
  --input-dims 1072x1024 --register subject.json --saved sidecar.json --json
```

| esci | significato |
|---|---|
| `0` | nessun elemento interrotto: PASS, ADVISORY o NOT_APPLICABLE, **ognuno dei quali è indicato nell'output** |
| `1` | HALT |
| `2` | **non è stato esaminato nulla:** argomenti errati, file illeggibile o un errore interno |

Gli errori ADVISORY restituiscono `0` intenzionalmente: uno stato diverso da zero interrompe una catena `&&`, che trasformerebbe un avviso
in un arresto in ogni shell che lo esegue.

## Cosa controlla

| # | controllo | si interrompe su |
|---|---|---|
| 1 | **Link topology** | un input di nodo che legge il proprio nodo; un collegamento a un ID di nodo non presente nel grafico |
| 2 | **La scansione del registro invertita** | un registro dichiarato che non corrisponde alla struttura del grafico — **in entrambe le direzioni** |
| 4 | **Saved-is-submitted** | il sidecar salvato e il payload inviato differiscono **come grafici analizzati** |
| 5 | **Generator-legal frame** | una dimensione che il VAE del frame effettivo non può decodificare |
| 8 | **Declared envelope** | **niente: non si interrompe mai.** L'esecuzione fuori banda è un AVVISO |

Tre controlli del progetto originale **non sono implementati** e sono indicati invece che semplicemente omessi: accordo tra ricetta e profilo (non esiste una configurazione soggetto-profilo), stima prima dell'invio
(lato di trasporto: nessun operando strutturale del grafico) e riproduzione dell'ancora (richiede il grafico
*builder*; il corpus contiene gli output, non gli script che li hanno creati).

### Controllo 2: quello che nomina il metodo

Quando il registro di un soggetto dichiara **nessun adattatore di stile**, l'affermazione è *non* "il
peso è 0.0". È che **non esiste alcun nodo caricatore e nessun riferimento alla scheda adattatore in nessuna parte del
grafico**.

> *Un peso di 0.0 non è un peso zero su una scheda caricata; è l'assenza della scheda.*

**E afferma anche l'immagine speculare.** Un peso positivo deciso con **nessun nodo caricatore** è
*silenziosamente inerte*: l'esecuzione viene completata, costa denaro e produce un output del modello di base mentre ogni riga del log indica che l'adattatore è stato richiesto. Questa direzione non produce alcun segnale che un essere umano potrebbe notare, il che è esattamente il motivo per cui un controllo giustifica la sua presenza rispetto a una persona che esegue il controllo manualmente.

### Controllo 5: il frame effettivo, non quello dichiarato

`1066 / 8 = 133.25` codifica in 133 colonne latenti e decodifica in **1064**, spostando ogni output
di 2 pixel rispetto all'immagine di controllo e interrompendo ogni accoppiamento a valle.

**Il difetto si è verificato a monte del grafico.** Il valore 1066 è stato derivato correttamente da una mesh, l'immagine è stata renderizzata con tale larghezza e caricata e il grafico non lo ha dichiarato, quindi un controllo che legge i valori letterali del grafico non avrebbe potuto rilevare l'incidente che lo motiva. L'operando è il frame che l'esecuzione produrrà effettivamente, che in un grafico img2img sono le dimensioni dell'immagine di input.

÷8 interrompe. ÷16 avvisa. Un limite minimo e una preferenza, non due limiti minimi.

### Controllo 8: avviso ed è onesto su ciò che non può dire

Per ogni checkpoint che il grafico carica, i parametri vengono confrontati con una tabella di intervalli **citata**.
Ogni voce contiene la sua banda, l'URL di origine, la data di recupero e una citazione delle parole della scheda stessa, e il costruttore si rifiuta di costruire una voce che non lo fa.

La voce del primo giorno è `Qwen-Image-InstantX-ControlNet-Union`. Contiene la
banda `controlnet_conditioning_scale` documentata dalla sua scheda e un'**assenza dichiarata** per la riduzione del rumore,
perché quella scheda non pubblica alcun intervallo di riduzione del rumore: questo viene verificato rispetto alla scheda attiva invece che richiamato. Quindi, un'esecuzione su un grafico a `denoise=0.92` segnala il valore 0,92, nomina il parametro e afferma
chiaramente che non può giudicarlo e perché.

Segnalare il valore che non può giudicare è la metà onesta della scoperta. Inventare una banda per giudicarlo sarebbe la metà disonesta.

## Il contratto di adozione

**Chiamalo in corso nel percorso di invio. Non esiste un flag di salto.**

*Il controllo si trova all'interno dello strumento che esegue l'azione irreversibile.* Un pre-controllo in una catena di shell prima dell'invio è un **trasporto, non una guardia**: nell'incidente che ha prodotto questa regola, 47.020 texel sono stati inviati dopo che una guardia aveva già attivato il blocco, perché una catena PowerShell ha superato un codice di uscita errato. Nessuno ha deciso di procedere; la costruzione era incapace di fermarsi.

**La CLI e il server MCP sono entrambi trasporti, non guardie.** Leggere un HALT da uno dei due e quindi inviare da qualche altra parte è la stessa catena con un'interfaccia migliore.

Nessuna funzione qui accetta un parametro `skip`, `force`, `warn_only` o `enabled` e i test leggono ogni
firma invece di fidarsi della documentazione. **Ogni guardia `raise`; nessuna è una semplice `assert`** —
`python -O` elimina `assert` silenziosamente e CI esegue l'intera suite sotto `-O` e
`PYTHONOPTIMIZE=1` per dimostrare che le guardie lo superano.

## Tramite MCP

```bash
python -m comfy_preflight.mcp_server     # stdio
npx @mcptoolshop/comfy-preflight mcp     # same server, no Python required
```

Uno strumento, `preflight`, restituisce lo stesso risultato strutturato restituito dalla libreria: un test verifica l’identità dei byte. Un comando HALT è una *chiamata riuscita* che restituisce `{"verdict": "halt", ...}`, perché segnalarlo come errore di protocollo comporterebbe la perdita della struttura di cui ha bisogno il chiamante.

## Sicurezza

Nessuna chiamata di rete, nessuna credenziale, nessun dato di telemetria e non scrive nulla da nessuna parte. Legge un grafico e un profilo e restituisce un risultato. Modello completo delle minacce: dati a cui si accede, dati a cui *non* si accede e autorizzazioni necessarie, in [SECURITY.md](SECURITY.md).

## Documentazione

📖 **[Il manuale](https://mcp-tool-shop-org.github.io/comfy-preflight/handbook/)** — istruzioni per l’avvio, descrizione dettagliata di ogni controllo, contratto di adozione e tabella degli elementi.

## Licenza

MIT — consultare [LICENSE](LICENSE).

<p align="center">
  Built by <a href="https://mcp-tool-shop.github.io/">MCP Tool Shop</a>
</p>
