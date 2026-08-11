import ts from 'typescript';
import { afterAll, describe, expect, it } from 'vitest';
import i18n from './i18n';
import { errorCopy, localizedErrorCopy } from './ui';

const productionSources = import.meta.glob(
  ['./**/*.tsx', '!./**/*.test.tsx', '!./**/*.stories.tsx'],
  { query: '?raw', import: 'default', eager: true },
) as Record<string, string>;

const allowedVisibleLiterals = new Set([
  'QF',
  'English',
  '简体中文',
  'COMPLETED',
  'REQUIRED',
  'SYSTEM',
  'ENABLED',
  'DISABLED',
  'EXACT',
  'CONTROLLED_OVERRIDE',
  'SET',
  'RANGE',
  'PASS',
  'WARN',
  'FAIL',
]);

function isAllowedVisibleLiteral(literal: string): boolean {
  const separator = literal.indexOf('=');
  const value = separator < 0 ? literal : literal.slice(separator + 1);
  return allowedVisibleLiterals.has(value);
}

function flattenKeys(value: unknown, prefix = ''): string[] {
  if (!value || typeof value !== 'object') return prefix ? [prefix] : [];
  return Object.entries(value).flatMap(([key, nested]) =>
    flattenKeys(nested, prefix ? `${prefix}.${key}` : key),
  );
}

function rawVisibleLiterals(path: string, source: string): string[] {
  const file = ts.createSourceFile(path, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const found: string[] = [];
  const hasVisibleLanguage = (value: string): boolean => /[A-Za-z]{2}|[\u3400-\u9fff]/.test(value);
  const visibleAttributeNames = new Set([
    'alt',
    'aria-description',
    'aria-label',
    'aria-placeholder',
    'aria-roledescription',
    'aria-valuetext',
    'caption',
    'description',
    'emptyText',
    'errorText',
    'helperText',
    'label',
    'message',
    'placeholder',
    'summary',
    'title',
  ]);
  const inside = (node: ts.Node, predicate: (candidate: ts.Node) => boolean): boolean => {
    for (let candidate: ts.Node | undefined = node.parent; candidate; candidate = candidate.parent)
      if (predicate(candidate)) return true;
    return false;
  };
  const insideTranslationCall = (node: ts.Node): boolean =>
    inside(
      node,
      (candidate) =>
        ts.isCallExpression(candidate) &&
        ts.isIdentifier(candidate.expression) &&
        candidate.expression.text === 't',
    );
  const insideVisibleAttribute = (node: ts.Node): boolean =>
    inside(
      node,
      (candidate) =>
        ts.isJsxAttribute(candidate) && visibleAttributeNames.has(candidate.name.getText(file)),
    );
  const structuralLiteral = (node: ts.StringLiteralLike): boolean => {
    const parent = node.parent;
    if (
      ts.isImportDeclaration(parent) ||
      ts.isExportDeclaration(parent) ||
      ts.isExternalModuleReference(parent) ||
      ts.isLiteralTypeNode(parent) ||
      ts.isCaseClause(parent) ||
      (ts.isPropertyAssignment(parent) && parent.name === node) ||
      (ts.isPropertyDeclaration(parent) && parent.name === node) ||
      (ts.isPropertySignature(parent) && parent.name === node) ||
      (ts.isMethodDeclaration(parent) && parent.name === node) ||
      (ts.isElementAccessExpression(parent) && parent.argumentExpression === node)
    )
      return true;
    if (
      ts.isBinaryExpression(parent) &&
      [
        ts.SyntaxKind.EqualsEqualsToken,
        ts.SyntaxKind.EqualsEqualsEqualsToken,
        ts.SyntaxKind.ExclamationEqualsToken,
        ts.SyntaxKind.ExclamationEqualsEqualsToken,
      ].includes(parent.operatorToken.kind)
    )
      return true;
    return false;
  };
  const renderedJsxExpression = (node: ts.Node): boolean => {
    let child = node;
    for (
      let candidate: ts.Node | undefined = node.parent;
      candidate;
      candidate = candidate.parent
    ) {
      if (ts.isJsxAttribute(candidate)) return false;
      if (ts.isJsxExpression(candidate))
        return ts.isJsxElement(candidate.parent) || ts.isJsxFragment(candidate.parent);
      if (
        ts.isParenthesizedExpression(candidate) ||
        ts.isAsExpression(candidate) ||
        ts.isSatisfiesExpression(candidate) ||
        ts.isNonNullExpression(candidate)
      ) {
        child = candidate;
        continue;
      }
      if (ts.isConditionalExpression(candidate)) {
        if (child === candidate.condition) return false;
        child = candidate;
        continue;
      }
      if (ts.isBinaryExpression(candidate)) {
        const operator = candidate.operatorToken.kind;
        if (
          ![
            ts.SyntaxKind.QuestionQuestionToken,
            ts.SyntaxKind.BarBarToken,
            ts.SyntaxKind.AmpersandAmpersandToken,
            ts.SyntaxKind.PlusToken,
          ].includes(operator) ||
          (operator === ts.SyntaxKind.AmpersandAmpersandToken && child === candidate.left)
        )
          return false;
        child = candidate;
        continue;
      }
      if (
        ts.isCallExpression(candidate) &&
        ts.isIdentifier(candidate.expression) &&
        candidate.expression.text === 'emptyPage' &&
        candidate.arguments.includes(child as ts.Expression)
      ) {
        child = candidate;
        continue;
      }
      if (ts.isArrowFunction(candidate) && candidate.body === child) {
        child = candidate;
        continue;
      }
      if (
        ts.isCallExpression(candidate) &&
        candidate.arguments.includes(child as ts.Expression) &&
        ts.isPropertyAccessExpression(candidate.expression) &&
        candidate.expression.name.text === 'map'
      ) {
        child = candidate;
        continue;
      }
      return false;
    }
    return false;
  };
  const containingFunction = (node: ts.Node): ts.Node | undefined => {
    for (let candidate: ts.Node | undefined = node.parent; candidate; candidate = candidate.parent)
      if (ts.isFunctionLike(candidate)) return candidate;
    return undefined;
  };
  const renderedBindings: Array<{ name: string; scope: ts.Node | undefined }> = [];
  const rememberRenderedBinding = (identifier: ts.Identifier) =>
    renderedBindings.push({ name: identifier.text, scope: containingFunction(identifier) });
  const collectRenderedBindings = (node: ts.Node) => {
    if (
      ts.isJsxExpression(node) &&
      (ts.isJsxElement(node.parent) || ts.isJsxFragment(node.parent)) &&
      node.expression &&
      ts.isIdentifier(node.expression)
    )
      rememberRenderedBinding(node.expression);
    if (
      ts.isJsxAttribute(node) &&
      visibleAttributeNames.has(node.name.getText(file)) &&
      node.initializer &&
      ts.isJsxExpression(node.initializer) &&
      node.initializer.expression &&
      ts.isIdentifier(node.initializer.expression)
    )
      rememberRenderedBinding(node.initializer.expression);
    ts.forEachChild(node, collectRenderedBindings);
  };
  collectRenderedBindings(file);
  const directRenderedBindingInitializer = (node: ts.Node): boolean => {
    let child = node;
    for (
      let candidate: ts.Node | undefined = node.parent;
      candidate;
      candidate = candidate.parent
    ) {
      if (ts.isVariableDeclaration(candidate)) {
        const name = candidate.name;
        return (
          candidate.initializer === child &&
          ts.isIdentifier(name) &&
          renderedBindings.some(
            (binding) =>
              binding.name === name.text && binding.scope === containingFunction(candidate),
          )
        );
      }
      if (
        !ts.isParenthesizedExpression(candidate) &&
        !ts.isConditionalExpression(candidate) &&
        !ts.isBinaryExpression(candidate) &&
        !ts.isAsExpression(candidate) &&
        !ts.isSatisfiesExpression(candidate) &&
        !ts.isNonNullExpression(candidate)
      )
        return false;
      child = candidate;
    }
    return false;
  };
  const literalValue = (node: ts.StringLiteralLike | ts.TemplateExpression): string =>
    ts.isTemplateExpression(node)
      ? [node.head.text, ...node.templateSpans.map((span) => span.literal.text)].join(' ')
      : node.text;
  const visit = (node: ts.Node) => {
    if (ts.isJsxText(node)) {
      const value = node.text.replace(/\s+/g, ' ').trim();
      if (hasVisibleLanguage(value)) found.push(value);
    }
    if (
      ts.isJsxAttribute(node) &&
      node.initializer &&
      ts.isStringLiteral(node.initializer) &&
      visibleAttributeNames.has(node.name.getText(file)) &&
      hasVisibleLanguage(node.initializer.text)
    )
      found.push(`${node.name.getText(file)}=${node.initializer.text}`);
    if (
      ts.isStringLiteral(node) &&
      hasVisibleLanguage(node.text) &&
      (renderedJsxExpression(node) ||
        insideVisibleAttribute(node) ||
        directRenderedBindingInitializer(node)) &&
      !structuralLiteral(node) &&
      !insideTranslationCall(node)
    )
      found.push(`jsx-expression=${node.text}`);
    if (
      ts.isTemplateExpression(node) &&
      (renderedJsxExpression(node) ||
        insideVisibleAttribute(node) ||
        directRenderedBindingInitializer(node)) &&
      !insideTranslationCall(node)
    ) {
      const visibleChunks = literalValue(node);
      if (hasVisibleLanguage(visibleChunks)) found.push(`template=${node.getText(file)}`);
    }
    ts.forEachChild(node, visit);
  };
  visit(file);
  return found;
}

afterAll(async () => i18n.changeLanguage('zh-CN'));

describe('P0 UI localization contract', () => {
  it('keeps English and Chinese semantic resource trees exhaustive and symmetric', () => {
    const english = new Set(flattenKeys(i18n.getResourceBundle('en', 'translation')));
    const chinese = new Set(flattenKeys(i18n.getResourceBundle('zh-CN', 'translation')));
    expect([...english].sort()).toEqual([...chinese].sort());
    expect(english.size).toBeGreaterThan(250);
  });

  it('AST-scans every production P0 UI surface and rejects untranslated visible copy', () => {
    expect(Object.keys(productionSources)).toEqual(
      expect.arrayContaining([
        './CanonicalChart.tsx',
        './format.tsx',
        './main.tsx',
        './ui.tsx',
        './routes/OverviewRoute.tsx',
        './routes/MemoRoutes.tsx',
        './design-system/domain-components.tsx',
      ]),
    );
    expect(
      Object.keys(productionSources).every((path) => !/\.(?:test|stories)\.tsx$/.test(path)),
    ).toBe(true);
    const violations = Object.entries(productionSources).flatMap(([path, source]) =>
      rawVisibleLiterals(path, source)
        .filter((literal) => !isAllowedVisibleLiteral(literal))
        .map((literal) => `${path}: ${literal}`),
    );
    expect(violations).toEqual([]);
  });

  it('mutation seam rejects hard-coded English and CJK visible copy', () => {
    expect(
      rawVisibleLiterals(
        'CanonicalChart.tsx',
        `export const Broken = ({ value }: { value: number }) => {
          const summary = \`Ending NAV \${value} points shown\`;
          return <><div aria-label="Chart summary" title="图表摘要" placeholder={'Search records'} alt="趋势图"/><td>{'Gap'}</td><p>{summary}</p></>;
        }`,
      ),
    ).toEqual(
      expect.arrayContaining([
        'aria-label=Chart summary',
        'title=图表摘要',
        'jsx-expression=Search records',
        'alt=趋势图',
        'jsx-expression=Gap',
        'template=`Ending NAV ${value} points shown`',
      ]),
    );
  });

  it('does not treat structural attributes, code constants, or dynamic translation keys as copy', () => {
    expect(
      rawVisibleLiterals(
        'CanonicalChart.tsx',
        `const API_ROUTE = '/api/v1/research';
        const STATUS = 'COMPLETED';
        export const Valid = ({ kind, status }: { kind: string; status: string }) => (
          <div className="definition-pair" data-testid="research-card" id="research-card" key="research" aria-labelledby="research-heading">
            {status === 'COMPLETED' ? t(\`chart.period.\${kind}\`) : t('common.unavailable')}
          </div>
        )`,
      ),
    ).toEqual([]);
  });

  it('permits only explicit native endonyms and canonical machine values', () => {
    const literals = rawVisibleLiterals(
      'MachineValues.tsx',
      `export const MachineValues = () => <><span>{'PASS'}</span><span>{'English'}</span></>`,
    );
    expect(literals).toEqual(['jsx-expression=PASS', 'jsx-expression=English']);
    expect(literals.filter((literal) => !isAllowedVisibleLiteral(literal))).toEqual([]);
    expect(isAllowedVisibleLiteral('jsx-expression=Unlisted prose')).toBe(false);
  });

  it('covers every canonical error in both languages without leaking English fallback in Chinese', async () => {
    expect(Object.keys(errorCopy)).toHaveLength(65);
    await i18n.changeLanguage('en');
    const english = i18n.getFixedT('en');
    for (const [code, copy] of Object.entries(errorCopy))
      expect(localizedErrorCopy(code as keyof typeof errorCopy, english, 'en')).toBe(copy);
    await i18n.changeLanguage('zh-CN');
    const chinese = i18n.getFixedT('zh-CN');
    for (const [code, copy] of Object.entries(errorCopy)) {
      const translated = localizedErrorCopy(code as keyof typeof errorCopy, chinese, 'zh-CN');
      expect(translated).not.toBe(copy);
      expect(translated.length).toBeGreaterThan(4);
    }
  });
});
