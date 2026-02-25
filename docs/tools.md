# Tool interface

Tools are the only operations executor can perform.

Planned core tools:

## run_command

Schema:
- `command: string`

Behavior:
- validated by policy (allowlist/denylist/operators)
- executed with `subprocess.run(..., shell=False)`

## read_file

Schema:
- `path: string`

Behavior:
- validated against workspace root constraints
- returns file content (truncated by config)

## write_file

Schema:
- `path: string`
- `content: string`

Behavior:
- validated against workspace root constraints
- writes UTF-8 text

## run_plan

Schema:
- `steps: array` of objects (`command`, `read_file`, `write_file`)

Behavior:
- each step validated and executed sequentially

Safety rule:

- every tool call must pass the same policy checks as direct CLI calls.

