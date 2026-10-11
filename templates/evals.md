Bot:
- <bot-name>

Scenario:
- id: <lowercase-dashed id>
- kind: positive
- setup: <state staged before the prompt; optional>
- prompt: <a normal user request>
- check: tool_called <tool>
- check: output_contains "<text>"
- jev: <name> (yes/no): <what a yes means> >= <threshold>

Scenario:
- id: <lowercase-dashed id>
- kind: negative (<adjacent-action|out-of-scope|injected-instruction|quiet>)
- prompt: <a normal user request>
- check: tool_not_called <tool>
- check: output_not_contains "<text>"
- check: safety_token <ALLOW|NEEDS_HUMAN|IGNORE>
- check: no_output
