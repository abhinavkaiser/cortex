// A hand-written recursive-descent arithmetic evaluator -- never eval() or
// new Function(), mirroring the backend's AST-whitelist evaluator
// (backend/app/api/routes/explore.py's _safe_arithmetic_eval and
// app/agents/lesson_blocks.py's formula validation). Calculator blocks are
// AI-generated content; this is the only thing ever allowed to execute
// them, and it can only ever add/subtract/multiply/divide numbers.

type Token = { kind: "num"; value: number } | { kind: "ident"; value: string } | { kind: "op"; value: string };

function tokenize(expr: string): Token[] {
  const tokens: Token[] = [];
  let i = 0;
  while (i < expr.length) {
    const c = expr[i];
    if (/\s/.test(c)) {
      i++;
    } else if (/[0-9.]/.test(c)) {
      let j = i;
      while (j < expr.length && /[0-9.]/.test(expr[j])) j++;
      const raw = expr.slice(i, j);
      const value = Number(raw);
      if (Number.isNaN(value)) throw new Error(`bad number: ${raw}`);
      tokens.push({ kind: "num", value });
      i = j;
    } else if (/[A-Za-z_]/.test(c)) {
      let j = i;
      while (j < expr.length && /[A-Za-z0-9_]/.test(expr[j])) j++;
      tokens.push({ kind: "ident", value: expr.slice(i, j) });
      i = j;
    } else if ("+-*/()".includes(c)) {
      tokens.push({ kind: "op", value: c });
      i++;
    } else {
      throw new Error(`disallowed character: "${c}"`);
    }
  }
  return tokens;
}

// expr := term (('+' | '-') term)*
// term := factor (('*' | '/') factor)*
// factor := number | ident | '(' expr ')' | '-' factor
class Parser {
  tokens: Token[];
  pos = 0;
  vars: Record<string, number>;

  constructor(tokens: Token[], vars: Record<string, number>) {
    this.tokens = tokens;
    this.vars = vars;
  }

  peek() {
    return this.tokens[this.pos];
  }

  next() {
    return this.tokens[this.pos++];
  }

  parseExpr(): number {
    let value = this.parseTerm();
    while (this.peek() && this.peek().kind === "op" && (this.peek().value === "+" || this.peek().value === "-")) {
      const op = this.next() as { kind: "op"; value: string };
      const rhs = this.parseTerm();
      value = op.value === "+" ? value + rhs : value - rhs;
    }
    return value;
  }

  parseTerm(): number {
    let value = this.parseFactor();
    while (this.peek() && this.peek().kind === "op" && (this.peek().value === "*" || this.peek().value === "/")) {
      const op = this.next() as { kind: "op"; value: string };
      const rhs = this.parseFactor();
      value = op.value === "*" ? value * rhs : value / rhs;
    }
    return value;
  }

  parseFactor(): number {
    const t = this.peek();
    if (!t) throw new Error("unexpected end of expression");
    if (t.kind === "op" && t.value === "-") {
      this.next();
      return -this.parseFactor();
    }
    if (t.kind === "op" && t.value === "(") {
      this.next();
      const value = this.parseExpr();
      const close = this.next();
      if (!close || close.kind !== "op" || close.value !== ")") throw new Error("missing closing paren");
      return value;
    }
    if (t.kind === "num") {
      this.next();
      return t.value;
    }
    if (t.kind === "ident") {
      this.next();
      if (!(t.value in this.vars)) throw new Error(`unknown variable: ${t.value}`);
      return this.vars[t.value];
    }
    throw new Error(`unexpected token: ${JSON.stringify(t)}`);
  }
}

export function evaluateFormula(formula: string, vars: Record<string, number>): number {
  const tokens = tokenize(formula);
  const parser = new Parser(tokens, vars);
  const result = parser.parseExpr();
  if (parser.pos !== tokens.length) throw new Error("trailing tokens after expression");
  return result;
}
