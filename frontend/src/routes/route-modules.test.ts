import { describe, expect, it } from 'vitest';
import * as approvals from './ApprovalRoutes';
import * as experiments from './ExperimentRoutes';
import * as governance from './GovernanceRoutes';
import * as research from './ResearchRoutes';
import * as strategies from './StrategyRoutes';
import * as validation from './ValidationRoutes';

describe('P0 route module boundaries', () => {
  it('exposes a lazy-loadable component for every implemented P0 route', () => {
    expect(research.ResearchLandingRoute).toBeTypeOf('function');
    expect(research.ResearchWorkspacePage).toBeTypeOf('function');
    expect(experiments.ExperimentLandingRoute).toBeTypeOf('function');
    expect(experiments.ExperimentPage).toBeTypeOf('function');
    expect(strategies.StrategyLandingRoute).toBeTypeOf('function');
    expect(strategies.StrategyPage).toBeTypeOf('function');
    expect(validation.ValidationLandingRoute).toBeTypeOf('function');
    expect(validation.ValidationPage).toBeTypeOf('function');
    expect(approvals.ApprovalListPage).toBeTypeOf('function');
    expect(approvals.ApprovalPage).toBeTypeOf('function');
    expect(governance.DataCapabilitiesPage).toBeTypeOf('function');
  });

  it('keeps routes, features, and domain modules independent from the bootstrap entrypoint', () => {
    const modules = import.meta.glob('../{routes,features,domain}/**/*.{ts,tsx}', {
      eager: true,
      import: 'default',
      query: '?raw',
    });
    for (const [path, source] of Object.entries(modules)) {
      expect(source, path).not.toMatch(/from\s+['"][^'"]*main(?:\.tsx)?['"]/);
      expect(source, path).not.toMatch(/import\(\s*['"][^'"]*main(?:\.tsx)?['"]\s*\)/);
    }
  });
});
