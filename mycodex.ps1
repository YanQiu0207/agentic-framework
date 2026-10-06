# Run Codex without the daemon, approval prompts, or sandbox restrictions.
& codex --no-daemon --dangerously-bypass-approvals-and-sandbox @args
exit $LASTEXITCODE
