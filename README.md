# Expression Evaluator (Streamlit)

A visual DSA mini-project that shows how arithmetic expressions are processed using stacks: **Infix → Postfix / Prefix → Result**.

## Features

- **Three modes (tabs):** Infix, Postfix, Prefix
- **Step-by-step visualization:**
  - Infix → Postfix conversion (operator stack)
  - Postfix evaluation (operand stack)
  - (Optional) Postfix → Prefix build steps
- **Supported operators:** `+  -  *  /  ^`
- **Parentheses:** `(` `)` (infix only)
- **Unary minus:** handled internally as `u-` (e.g., `-(3+4)`, `-2^2`)

## Tech Stack

- Python
- Streamlit
- Pandas (tables)

## Run Locally

1. Install dependencies:
   - `pip install streamlit pandas`
2. Start the app:
   - `streamlit run app.py`

## Input Examples

### Infix

- `3 + 4 * 2 / (1 - 5) ^ 2`
- `-(3 + 4) * 2`

### Postfix (space-separated tokens)

- `3 4 2 * 1 5 - 2 ^ / +`

### Prefix (space-separated tokens)

- `+ 3 / * 4 2 ^ - 1 5 2`

## How It Works (High Level)

- **Infix → Postfix:** Shunting-yard algorithm (operator stack + output list)
- **Postfix Evaluation:** operand stack; push numbers, pop/apply operators
- **Prefix Evaluation:** scan right-to-left using an operand stack

## Project Structure

- `app.py` — Streamlit UI + algorithms with step tracing

