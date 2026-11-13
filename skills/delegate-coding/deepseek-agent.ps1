<#
  deepseek-agent.ps1 - run one headless Claude Code agent on DeepSeek and print its reply.

  Only this child process talks to DeepSeek; nothing global is changed.
  Usage:
    powershell -NoProfile -ExecutionPolicy Bypass -File deepseek-agent.ps1 -Cwd <dir> -PromptFile <file>
      [-Model claude-sonnet-5-5 (Flash, default) | claude-opus-5-5 (Pro)]
      [-Access dev|strict] [-MaxTurns 80] [-Log <file.json>] [-ClaudeCmd claude]
  Prints "== DEEPSEEK ok=.. turns=.. secs=.." and then the agent's final reply.
  Exit code is claude's own.
#>
param(
  [Parameter(Mandatory)] [string]$Cwd,
  [Parameter(Mandatory)] [string]$PromptFile,
  # DeepSeek maps claude-opus* -> Pro, any other claude* -> Flash.
  [string]$Model = 'claude-sonnet-5-5',
  # dev: full Bash minus a deny list. strict: read-only tools plus py / git status / git diff.
  [ValidateSet('dev', 'strict')] [string]$Access = 'dev',
  # Hard cap on agent turns; DeepSeek has no stopping sense of its own. 0 = no cap.
  [int]$MaxTurns = 80,
  [string]$Log = '',
  [string]$ClaudeCmd = 'claude'
)
$ErrorActionPreference = 'Stop'

# Agent = may spawn subagents; they inherit this child's DeepSeek endpoint and permissions.
$allow = @{
  strict = @('Read', 'Glob', 'Grep', 'Agent', 'Bash(py *)', 'Bash(git status*)', 'Bash(git diff*)')
  dev    = @('Read', 'Edit', 'Write', 'Glob', 'Grep', 'NotebookEdit', 'TodoWrite', 'Agent', 'Bash')
}[$Access]
$deny = @('WebFetch', 'WebSearch',
  'Bash(git push*)', 'Bash(git remote*)', 'Bash(git reset --hard*)', 'Bash(git clean*)', 'Bash(git config --global*)',
  'Bash(rm -r*)', 'Bash(rm -fr*)', 'Bash(rm -rf*)', 'Bash(rmdir *)', 'Bash(del *)', 'Bash(format *)',
  'Bash(curl *)', 'Bash(wget *)', 'Bash(ssh *)', 'Bash(scp *)', 'Bash(Invoke-WebRequest*)',
  'Bash(pip install*)', 'Bash(py -m pip install*)', 'Bash(npm install -g*)', 'Bash(npm publish*)',
  'Bash(setx *)', 'Bash(reg *)', 'Bash(shutdown*)',
  'Bash(powershell*)', 'Bash(pwsh*)', 'Bash(cmd *)', 'Bash(cmd.exe*)', 'Bash(claude *)', 'Bash(codex *)')
# acceptEdits would auto-approve edits even when they are not allowed, so strict must deny them outright.
if ($Access -eq 'strict') { $deny += @('Edit', 'Write', 'NotebookEdit') }

$system = @'
You are a focused agent working only inside the current directory.
- Do the task, then run the project's tests yourself and fix until they pass. Stop as soon as the task is done.
- On this Windows machine use `py` for Python, never `python`. The Bash tool is Git Bash: use POSIX syntax.
- Do not change the expected results of existing tests unless the task requires it; if you do, say what and why.
- Finish with a short report in the language the task is written in: what changed, and the real last line of the test output.
'@

$key = $env:DEEPSEEK_API_KEY
if (-not $key) { $key = [Environment]::GetEnvironmentVariable('DEEPSEEK_API_KEY', 'User') }
if (-not $key) { throw 'DEEPSEEK_API_KEY is not set (process or User scope).' }

# Drop everything inherited from the host Claude session, then point this child at DeepSeek.
Get-ChildItem Env: | Where-Object { $_.Name -match '^(ANTHROPIC_|CLAUDE|CLAUDECODE$)' } |
  ForEach-Object { [Environment]::SetEnvironmentVariable($_.Name, $null, 'Process') }
$env:ANTHROPIC_BASE_URL = 'https://api.deepseek.com/anthropic'
$env:ANTHROPIC_API_KEY  = $key
$env:CLAUDE_CONFIG_DIR  = Join-Path $env:USERPROFILE '.claude-deepseek'
$env:CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC = '1'

# PS 5.1 pipes native programs in the OEM code page by default, which mangles Chinese.
$utf8 = New-Object System.Text.UTF8Encoding $false
$OutputEncoding = $utf8
[Console]::OutputEncoding = $utf8
[Console]::InputEncoding = $utf8

$prompt = Get-Content -Raw -Encoding UTF8 $PromptFile
Set-Location $Cwd
# --bare alone exposes only Bash/Read/Edit; --tools puts back the full set (incl. Agent for subagents).
$tools = ($allow | ForEach-Object { $_ -replace '\(.*$', '' } | Select-Object -Unique) -join ','
$extra = @('--tools', $tools, '--append-system-prompt', $system, '--disallowedTools') + $deny
if ($MaxTurns -gt 0) { $extra += @('--max-turns', [string]$MaxTurns) }
$start = Get-Date
$ErrorActionPreference = 'Continue'
# No --bare: it strips the tool set to Bash/Read/Edit (no subagents). Isolation comes from
# CLAUDE_CONFIG_DIR (no user hooks/skills/CLAUDE.md) + --strict-mcp-config (no MCP servers).
# --permission-prompts none: never waits for a human.
$out = $prompt | & $ClaudeCmd -p --strict-mcp-config --model $Model --output-format json @extra `
  --permission-mode acceptEdits --permission-prompts none --allowedTools @allow 2>&1
$code = $LASTEXITCODE
$text = ($out | ForEach-Object { [string]$_ }) -join "`n"
if ($Log) { [System.IO.File]::WriteAllText($Log, $text, $utf8) }

$i = $text.IndexOf('{')
$result = $null
if ($i -ge 0) { try { $result = $text.Substring($i) | ConvertFrom-Json } catch { $result = $null } }
$secs = [int]((Get-Date) - $start).TotalSeconds
if ($result) {
  Write-Host ('== DEEPSEEK ok=' + (-not $result.is_error) + ' turns=' + $result.num_turns + ' secs=' + $secs + ' exit=' + $code)
  Write-Host ([string]$result.result)
} else {
  Write-Host ('== DEEPSEEK no JSON result, exit=' + $code + ', raw tail:')
  $tail = $text
  if ($tail.Length -gt 2000) { $tail = $tail.Substring($tail.Length - 2000) }
  Write-Host ($tail -replace 'sk-[A-Za-z0-9]{8,}', 'sk-***')
}
exit $code
