import type { ReactNode } from 'react';
import {
  createBrowserHistory,
  createRootRoute,
  createRoute,
  createRouter,
  lazyRouteComponent,
  Navigate,
  redirect,
} from '@tanstack/react-router';
import { z } from 'zod';
import { api } from '../../api/client';

type RouteComponent = () => ReactNode;

type RouteComponents = { Shell: RouteComponent };

/** Centralized typed route composition; feature implementations remain lazy. */
export function createAppRouter({ Shell }: RouteComponents) {
  const rootRoute = createRootRoute({
    component: Shell,
    beforeLoad: async ({ location }) => {
      if (location.pathname === '/login') return;
      try {
        await api.session();
      } catch {
        // eslint-disable-next-line @typescript-eslint/only-throw-error
        throw redirect({ to: '/login', replace: true });
      }
    },
  });
  const indexRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: '/',
    component: () => <Navigate to="/overview" />,
  });
  const setupRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: 'setup',
    component: () => <Navigate to="/settings" replace />,
  });
  const loginRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: 'login',
    component: lazyRouteComponent(() => import('../../routes/LoginRoute'), 'LoginPage'),
  });
  const overviewRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: 'overview',
    component: lazyRouteComponent(() => import('../../routes/OverviewRoute'), 'OverviewPage'),
  });
  const researchRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: 'research',
    component: lazyRouteComponent(
      () => import('../../routes/ResearchRoutes'),
      'ResearchLandingRoute',
    ),
  });
  const researchWorkspaceRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: 'research/$researchId',
    validateSearch: z.object({
      tab: z
        .enum(['overview', 'plan', 'timeline', 'experiments', 'evidence', 'artifacts', 'audit'])
        .optional(),
    }),
    component: lazyRouteComponent(
      () => import('../../routes/ResearchRoutes'),
      'ResearchWorkspacePage',
    ),
  });
  const dataRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: 'data',
    component: lazyRouteComponent(
      () => import('../../routes/GovernanceRoutes'),
      'DataCapabilitiesPage',
    ),
  });
  const experimentLandingRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: 'experiments',
    component: lazyRouteComponent(
      () => import('../../routes/ExperimentRoutes'),
      'ExperimentLandingRoute',
    ),
  });
  const experimentRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: 'experiments/$experimentId',
    validateSearch: z.object({
      tab: z.enum(['summary', 'results', 'inputs', 'artifacts', 'logs']).optional(),
      focus: z.enum(['provenance']).optional(),
      toolCallId: z.string().optional(),
    }),
    component: lazyRouteComponent(() => import('../../routes/ExperimentRoutes'), 'ExperimentPage'),
  });
  const strategyLandingRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: 'strategies',
    component: lazyRouteComponent(
      () => import('../../routes/StrategyRoutes'),
      'StrategyLandingRoute',
    ),
  });
  const strategyRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: 'strategies/$strategyId',
    validateSearch: z.object({
      version: z.coerce.number().int().positive().optional(),
      tab: z
        .enum([
          'overview',
          'specification',
          'backtests',
          'trades',
          'risk',
          'sensitivity',
          'validation',
          'history',
        ])
        .optional(),
    }),
    component: lazyRouteComponent(() => import('../../routes/StrategyRoutes'), 'StrategyPage'),
  });
  const validationLandingRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: 'validation',
    component: lazyRouteComponent(
      () => import('../../routes/ValidationRoutes'),
      'ValidationLandingRoute',
    ),
  });
  const validationRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: 'validation/$validationId',
    component: lazyRouteComponent(() => import('../../routes/ValidationRoutes'), 'ValidationPage'),
  });
  const approvalListRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: 'approvals',
    component: lazyRouteComponent(() => import('../../routes/ApprovalRoutes'), 'ApprovalListPage'),
  });
  const approvalRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: 'approvals/$approvalId',
    component: lazyRouteComponent(() => import('../../routes/ApprovalRoutes'), 'ApprovalPage'),
  });
  const memoLandingRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: 'memos',
    component: lazyRouteComponent(() => import('../../routes/MemoRoutes'), 'MemoLanding'),
  });
  const memoRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: 'memos/$memoId',
    component: lazyRouteComponent(() => import('../../routes/MemoRoutes'), 'MemoPage'),
  });
  const agentsRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: 'agents',
    component: lazyRouteComponent(() => import('../../routes/GovernanceRoutes'), 'AgentsPage'),
  });
  const settingsRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: 'settings',
    component: lazyRouteComponent(() => import('../../routes/SettingsRoute'), 'SettingsPage'),
  });
  const activityRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: 'activity',
    validateSearch: z.object({
      eventId: z.string().optional(),
      provenanceId: z.string().optional(),
      requestId: z.string().optional(),
    }),
    component: lazyRouteComponent(() => import('../../routes/GovernanceRoutes'), 'ActivityPage'),
  });
  const routeTree = rootRoute.addChildren([
    indexRoute,
    setupRoute,
    loginRoute,
    overviewRoute,
    researchRoute,
    researchWorkspaceRoute,
    dataRoute,
    experimentLandingRoute,
    experimentRoute,
    strategyLandingRoute,
    strategyRoute,
    validationLandingRoute,
    validationRoute,
    approvalListRoute,
    approvalRoute,
    memoLandingRoute,
    memoRoute,
    agentsRoute,
    settingsRoute,
    activityRoute,
  ]);
  return createRouter({ routeTree, history: createBrowserHistory(), defaultPreload: 'intent' });
}
