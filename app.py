import re
from dataclasses import dataclass
from typing import Any

import pandas as pd
import streamlit as st


@dataclass(frozen=True)
class OpInfo:
    precedence: int
    associativity: str  # "left" | "right"
    arity: int  # 1 or 2


class Algorithm:
    _OPS: dict[str, OpInfo] = {
        "+": OpInfo(precedence=1, associativity="left", arity=2),
        "-": OpInfo(precedence=1, associativity="left", arity=2),
        "*": OpInfo(precedence=2, associativity="left", arity=2),
        "/": OpInfo(precedence=2, associativity="left", arity=2),
        "^": OpInfo(precedence=3, associativity="right", arity=2),
        "u-": OpInfo(precedence=4, associativity="right", arity=1),  # unary minus
    }

    _TOKEN_RE = re.compile(
        r"""
        \s*(
            (?:(?:\d+(?:\.\d*)?)|(?:\.\d+))(?:[eE][+-]?\d+)?  # number
            |[+\-*/^()]                                         # operator/parens
        )\s*
        """,
        re.VERBOSE,
    )

    def tokenize(self, expression: str) -> list[str]:
        if not expression or not expression.strip():
            raise ValueError("Expression is empty.")

        tokens: list[str] = []
        pos = 0
        while pos < len(expression):
            match = self._TOKEN_RE.match(expression, pos)
            if not match:
                bad = expression[pos : pos + 16]
                raise ValueError(f"Unexpected character near: {bad!r}")
            token = match.group(1)
            tokens.append(token)
            pos = match.end()

        # Convert unary '-' to 'u-' when appropriate
        normalized: list[str] = []
        prev_type: str | None = None  # "num" | "op" | "(" | ")"
        for token in tokens:
            if self._is_number(token):
                normalized.append(token)
                prev_type = "num"
                continue
            if token == "(":
                normalized.append(token)
                prev_type = "("
                continue
            if token == ")":
                normalized.append(token)
                prev_type = ")"
                continue
            if token in self._OPS:
                if token == "-" and (prev_type is None or prev_type in {"op", "("}):
                    normalized.append("u-")
                else:
                    normalized.append(token)
                prev_type = "op"
                continue
            raise ValueError(f"Unknown token: {token!r}")

        return normalized

    def infix_to_postfix(self, expression: str) -> tuple[list[str], list[dict[str, Any]]]:
        tokens = self.tokenize(expression)
        op_stack: list[str] = []
        output: list[str] = []
        steps: list[dict[str, Any]] = []

        def snap(token: str, action: str) -> None:
            steps.append(
                {
                    "Token": token,
                    "Action": action,
                    "Operator Stack": " ".join(op_stack),
                    "Output (Postfix)": " ".join(output),
                }
            )

        for token in tokens:
            if self._is_number(token):
                output.append(token)
                snap(token, "Append number to output")
                continue

            if token == "(":
                op_stack.append(token)
                snap(token, "Push '(' to stack")
                continue

            if token == ")":
                while op_stack and op_stack[-1] != "(":
                    output.append(op_stack.pop())
                    snap(token, "Pop operator to output")
                if not op_stack or op_stack[-1] != "(":
                    raise ValueError("Mismatched parentheses.")
                op_stack.pop()
                snap(token, "Pop '(' from stack")
                continue

            if token not in self._OPS:
                raise ValueError(f"Unsupported operator: {token!r}")

            o1 = token
            while op_stack and op_stack[-1] in self._OPS:
                o2 = op_stack[-1]
                if self._should_pop(o1, o2):
                    output.append(op_stack.pop())
                    snap(o1, f"Pop '{o2}' to output (precedence/associativity)")
                else:
                    break
            op_stack.append(o1)
            snap(o1, "Push operator to stack")

        while op_stack:
            top = op_stack.pop()
            if top in {"(", ")"}:
                raise ValueError("Mismatched parentheses.")
            output.append(top)
            snap("End", f"Pop '{top}' to output")

        return output, steps

    def evaluate_postfix(self, postfix_tokens: list[str]) -> tuple[float, list[dict[str, Any]]]:
        stack: list[float] = []
        steps: list[dict[str, Any]] = []

        def snap(token: str, action: str) -> None:
            steps.append(
                {
                    "Token": token,
                    "Action": action,
                    "Operand Stack": " ".join(self._fmt_num(v) for v in stack),
                }
            )

        for token in postfix_tokens:
            if self._is_number(token):
                stack.append(float(token))
                snap(token, "Push number")
                continue

            if token not in self._OPS:
                raise ValueError(f"Unsupported operator in postfix: {token!r}")

            op_info = self._OPS[token]
            if op_info.arity == 1:
                if len(stack) < 1:
                    raise ValueError("Insufficient operands for unary operator.")
                a = stack.pop()
                if token == "u-":
                    stack.append(-a)
                else:
                    raise ValueError(f"Unknown unary operator: {token!r}")
                snap(token, "Apply unary operator")
                continue

            if len(stack) < 2:
                raise ValueError("Insufficient operands for binary operator.")
            b = stack.pop()
            a = stack.pop()
            stack.append(self._apply_binary(token, a, b))
            snap(token, "Apply binary operator")

        if len(stack) != 1:
            raise ValueError("Invalid postfix expression (stack did not resolve to one value).")

        return stack[0], steps

    def postfix_to_prefix(self, postfix_tokens: list[str]) -> tuple[list[str], list[dict[str, Any]]]:
        stack: list[list[str]] = []
        steps: list[dict[str, Any]] = []

        def snap(token: str, action: str) -> None:
            steps.append(
                {
                    "Token": token,
                    "Action": action,
                    "Expr Stack": " | ".join(" ".join(parts) for parts in stack),
                }
            )

        for token in postfix_tokens:
            if self._is_number(token):
                stack.append([token])
                snap(token, "Push operand expression")
                continue

            if token not in self._OPS:
                raise ValueError(f"Unsupported operator in postfix: {token!r}")

            op_info = self._OPS[token]
            if op_info.arity == 1:
                if len(stack) < 1:
                    raise ValueError("Insufficient operands for unary operator.")
                a = stack.pop()
                stack.append([token, *a])
                snap(token, "Build unary prefix expression")
                continue

            if len(stack) < 2:
                raise ValueError("Insufficient operands for binary operator.")
            b = stack.pop()
            a = stack.pop()
            stack.append([token, *a, *b])
            snap(token, "Build binary prefix expression")

        if len(stack) != 1:
            raise ValueError("Invalid postfix expression (did not resolve to one expression).")
        return stack[0], steps

    def infix_to_prefix(self, expression: str) -> tuple[list[str], list[dict[str, Any]], list[dict[str, Any]]]:
        postfix_tokens, infix_steps = self.infix_to_postfix(expression)
        prefix_tokens, prefix_steps = self.postfix_to_prefix(postfix_tokens)
        return prefix_tokens, infix_steps, prefix_steps

    def evaluate_prefix(self, prefix_tokens: list[str]) -> tuple[float, list[dict[str, Any]]]:
        stack: list[float] = []
        steps: list[dict[str, Any]] = []

        def snap(token: str, action: str) -> None:
            steps.append(
                {
                    "Token": token,
                    "Action": action,
                    "Operand Stack": " ".join(self._fmt_num(v) for v in stack),
                }
            )

        for token in reversed(prefix_tokens):
            if self._is_number(token):
                stack.append(float(token))
                snap(token, "Push number")
                continue

            if token not in self._OPS:
                raise ValueError(f"Unsupported operator in prefix: {token!r}")

            op_info = self._OPS[token]
            if op_info.arity == 1:
                if len(stack) < 1:
                    raise ValueError("Insufficient operands for unary operator.")
                a = stack.pop()
                if token == "u-":
                    stack.append(-a)
                else:
                    raise ValueError(f"Unknown unary operator: {token!r}")
                snap(token, "Apply unary operator")
                continue

            if len(stack) < 2:
                raise ValueError("Insufficient operands for binary operator.")
            a = stack.pop()
            b = stack.pop()
            stack.append(self._apply_binary(token, a, b))
            snap(token, "Apply binary operator")

        if len(stack) != 1:
            raise ValueError("Invalid prefix expression (stack did not resolve to one value).")
        return stack[0], steps

    def parse_rpn_tokens(self, expression: str) -> list[str]:
        if not expression or not expression.strip():
            raise ValueError("Expression is empty.")
        raw = expression.replace(",", " ").split()
        tokens: list[str] = []
        for token in raw:
            if self._is_number(token) or token in self._OPS:
                tokens.append(token)
            else:
                raise ValueError(f"Unexpected token: {token!r}")
        return tokens

    def _should_pop(self, incoming: str, stack_top: str) -> bool:
        i = self._OPS[incoming]
        s = self._OPS[stack_top]
        if i.associativity == "left":
            return i.precedence <= s.precedence
        return i.precedence < s.precedence  # right-associative

    def _apply_binary(self, op: str, a: float, b: float) -> float:
        if op == "+":
            return a + b
        if op == "-":
            return a - b
        if op == "*":
            return a * b
        if op == "/":
            return a / b
        if op == "^":
            return a**b
        raise ValueError(f"Unknown operator: {op!r}")

    def _is_number(self, token: str) -> bool:
        return token[:1].isdigit() or token.startswith(".")

    def _fmt_num(self, value: float) -> str:
        if value == int(value):
            return str(int(value))
        return f"{value:.10g}"


st.set_page_config(page_title="Expression Evaluator", page_icon="🧮", layout="wide")

st.title("Expression Evaluator (Stacks)")
st.markdown("Select a tab: **Infix**, **Postfix**, or **Prefix**.")

algo = Algorithm()
tab_infix, tab_postfix, tab_prefix = st.tabs(["Infix", "Postfix", "Prefix"])

with tab_infix:
    infix_example = "3 + 4 * 2 / (1 - 5) ^ 2"
    infix_input = st.text_input("Infix expression:", infix_example, key="infix_input")

    if st.button("Convert & Evaluate", type="primary", key="infix_btn"):
        try:
            postfix_tokens, infix_steps = algo.infix_to_postfix(infix_input)
            prefix_tokens, _, prefix_build_steps = algo.infix_to_prefix(infix_input)
            result, postfix_eval_steps = algo.evaluate_postfix(postfix_tokens)

            c1, c2 = st.columns(2, gap="large")
            with c1:
                st.subheader("Infix → Postfix")
                st.dataframe(pd.DataFrame(infix_steps), use_container_width=True, hide_index=True)
            with c2:
                st.subheader("Postfix Evaluation")
                st.dataframe(pd.DataFrame(postfix_eval_steps), use_container_width=True, hide_index=True)

            st.divider()
            a, b, c = st.columns(3)
            with a:
                st.success(f"Postfix: `{ ' '.join(postfix_tokens) }`")
            with b:
                st.info(f"Prefix: `{ ' '.join(prefix_tokens) }`")
            with c:
                st.metric("Result", algo._fmt_num(result))

            with st.expander("Postfix → Prefix steps"):
                st.dataframe(pd.DataFrame(prefix_build_steps), use_container_width=True, hide_index=True)

        except Exception as e:
            st.error(f"Invalid infix expression: {e}")

with tab_postfix:
    postfix_example = "3 4 2 * 1 5 - 2 ^ / +"
    postfix_input = st.text_input("Postfix tokens (space-separated):", postfix_example, key="postfix_input")

    if st.button("Evaluate Postfix", type="primary", key="postfix_btn"):
        try:
            postfix_tokens = algo.parse_rpn_tokens(postfix_input)
            result, steps = algo.evaluate_postfix(postfix_tokens)
            st.subheader("Operand Stack Steps")
            st.dataframe(pd.DataFrame(steps), use_container_width=True, hide_index=True)
            st.divider()
            st.metric("Result", algo._fmt_num(result))
        except Exception as e:
            st.error(f"Invalid postfix expression: {e}")

with tab_prefix:
    prefix_example = "+ 3 / * 4 2 ^ - 1 5 2"
    prefix_input = st.text_input("Prefix tokens (space-separated):", prefix_example, key="prefix_input")

    if st.button("Evaluate Prefix", type="primary", key="prefix_btn"):
        try:
            prefix_tokens = algo.parse_rpn_tokens(prefix_input)
            result, steps = algo.evaluate_prefix(prefix_tokens)
            st.subheader("Operand Stack Steps")
            st.dataframe(pd.DataFrame(steps), use_container_width=True, hide_index=True)
            st.divider()
            st.metric("Result", algo._fmt_num(result))
        except Exception as e:
            st.error(f"Invalid prefix expression: {e}")

with st.sidebar:
    st.header("Notes")
    st.write("- Supported operators: `+ - * / ^`")
    st.write("- Parentheses: `(` and `)` (infix only)")
