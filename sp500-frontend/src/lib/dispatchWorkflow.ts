/** Trigger GitHub Actions workflows from the Vercel UI. */

export async function dispatchWorkflow(
  workflowFile: string,
  inputs: Record<string, string | boolean | number> = {}
): Promise<{ ok: true } | { ok: false; error: string }> {
  const token = process.env.GITHUB_TOKEN || process.env.GH_TOKEN
  const repo = process.env.GITHUB_DATA_REPO || 'Hargunghotra/sp500'
  if (!token) {
    return {
      ok: false,
      error:
        'Add GITHUB_TOKEN (workflow scope) in Vercel env to trigger Agent cron from the phone.',
    }
  }

  const res = await fetch(
    `https://api.github.com/repos/${repo}/actions/workflows/${workflowFile}/dispatches`,
    {
      method: 'POST',
      headers: {
        Accept: 'application/vnd.github+json',
        Authorization: `Bearer ${token}`,
        'X-GitHub-Api-Version': '2022-11-28',
        'User-Agent': 'sp500-simulator-vercel',
      },
      body: JSON.stringify({
        ref: process.env.GITHUB_WORKFLOW_REF || 'cursor/sp500-trading-simulator',
        inputs,
      }),
    }
  )

  if (!res.ok) {
    const text = await res.text()
    return { ok: false, error: `GitHub dispatch failed (${res.status}): ${text.slice(0, 300)}` }
  }
  return { ok: true }
}
