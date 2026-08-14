import type { SiteConfig } from '@mcptoolshop/site-theme';

const DESCRIPTION =
  'A gate that runs on a ComfyUI workflow graph in the seconds before it is submitted, and halts a submission that would spend credits producing a known-wrong result.';

export const config: SiteConfig = {
  title: 'comfy-preflight',
  description: DESCRIPTION,
  logoBadge: 'CP',
  brandName: 'comfy-preflight',
  repoUrl: 'https://github.com/mcp-tool-shop-org/comfy-preflight',
  npmUrl: 'https://www.npmjs.com/package/@mcptoolshop/comfy-preflight',
  footerText:
    'MIT Licensed — built by <a href="https://mcp-tool-shop.github.io/" style="color:var(--color-muted);text-decoration:underline">MCP Tool Shop</a>',

  hero: {
    badge: 'Open source · MIT',
    headline: 'The wrong graph bills the same.',
    headlineAccent: 'Catch it before you submit.',
    description:
      'A Comfy Cloud dry_run returned status: validated on a graph whose VAEDecode read its own output. A provider’s validator answers whether a graph will run — not whether it’s the graph you meant. comfy-preflight checks the difference in the seconds before submission, in-process, where a shell step can’t walk past it.',
    primaryCta: { href: '#usage', label: 'Get started' },
    secondaryCta: { href: 'handbook/', label: 'Read the Handbook' },
    previews: [
      { label: 'npx', code: 'npx @mcptoolshop/comfy-preflight check graph.json' },
      { label: 'pip', code: 'pip install comfy-preflight' },
      {
        label: 'In-process',
        code: 'preflight(graph, register, input_dims=(w, h))\nsubmit(graph)  # only if nothing raised',
      },
    ],
  },

  sections: [
    {
      kind: 'features',
      id: 'features',
      title: 'What it checks',
      subtitle:
        'Five checks, composed into one verdict. Every one was paid for by a run that got past dry_run.',
      features: [
        {
          title: 'Link topology',
          desc: 'A node input reading its own node, or a link to a node id that is not in the graph. The founding case: a retyped payload with VAEDecode.samples = ["14", 0] that a provider called validated.',
        },
        {
          title: 'The inverted register scan',
          desc: 'When a subject declares no style adapter, the claim is not "the weight is 0.0" — it is that no loader node and no card reference exist anywhere. It asserts the mirror image too: a decided weight with no loader is silently inert, and produces base-model output while every log line says otherwise.',
        },
        {
          title: 'Saved is submitted',
          desc: 'The saved sidecar and the submitted payload, compared as parsed graphs rather than as text — because a JSON re-dump can differ in whitespace without a value moving.',
        },
        {
          title: 'Generator-legal frame',
          desc: 'A Qwen VAE downsamples by 8, so a width of 1066 decodes to 1064 and puts every output 2 px off its control image. The operand is the effective frame, which on an img2img graph lives in the uploaded image rather than in the graph.',
        },
        {
          title: 'The declared envelope',
          desc: 'Graph parameters against a cited envelope table, per checkpoint. Advisory, never a halt — a documented band is documentation, and a gate that halts correct work gets disabled by the third person who hits it.',
        },
        {
          title: 'It never fixes your graph',
          desc: 'No rewiring, no auto-inserted loader, no rounded frame. It names the defect and the node, and you decide. A graph a gate repaired is a graph nobody reviewed.',
        },
      ],
    },
    {
      kind: 'code-cards',
      id: 'usage',
      title: 'Usage',
      cards: [
        {
          title: 'The development door',
          code: 'npx @mcptoolshop/comfy-preflight check graph.json \\\n  --input-dims 1072x1024 --register subject.json\n\n# 0 = nothing halted   1 = HALT   2 = nothing was examined',
        },
        {
          title: 'The production gate — in-process, on the submit path',
          code: 'from comfy_preflight import preflight\n\n# Inside the function that submits. Not in a shell step before it.\npreflight(graph, register, input_dims=(width, height))\nsubmit(graph)   # only reached if nothing raised',
        },
        {
          title: 'Over MCP (stdio)',
          code: 'pip install "comfy-preflight[mcp]"\npython -m comfy_preflight.mcp_server\n\n# or, with no Python at all:\nnpx @mcptoolshop/comfy-preflight mcp',
        },
      ],
    },
  ],
};
