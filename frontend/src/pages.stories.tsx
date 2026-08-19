import { useMemo } from 'react';
import type { Meta, StoryObj } from '@storybook/react-vite';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
  Outlet,
  RouterProvider,
} from '@tanstack/react-router';
import { ResearchWorkspacePage, StrategyPage } from './features/workbench/WorkbenchPages';
import { DataCapabilitiesPage } from './features/data/DataCapabilitiesPage';
import { sharedMswScenarios, storybookProblemHandlers } from './testing/msw-handlers';

function ActualDomainPage({ page }: { page: 'research' | 'strategy' | 'data' }) {
  const client = useMemo(
    () => new QueryClient({ defaultOptions: { queries: { retry: false } } }),
    [],
  );
  const pageRouter = useMemo(() => {
    const root = createRootRoute({ component: Outlet });
    const route =
      page === 'research'
        ? createRoute({
            getParentRoute: () => root,
            path: '/research/$researchId',
            component: ResearchWorkspacePage,
          })
        : page === 'strategy'
          ? createRoute({
              getParentRoute: () => root,
              path: '/strategies/$strategyId',
              component: StrategyPage,
            })
          : createRoute({
              getParentRoute: () => root,
              path: '/data',
              component: DataCapabilitiesPage,
            });
    const path =
      page === 'research'
        ? '/research/RSCH-399GM4EKDQ6VFNPE5EQ50HTV2J?tab=overview'
        : page === 'strategy'
          ? '/strategies/STRAT-6X4TD9TY7SPPCAM5F5AG7ZH8WG?version=4&tab=backtests'
          : '/data';
    return createRouter({
      routeTree: root.addChildren([route]),
      history: createMemoryHistory({ initialEntries: [path] }),
    });
  }, [page]);
  return (
    <QueryClientProvider client={client}>
      <RouterProvider router={pageRouter} />
    </QueryClientProvider>
  );
}

const meta = {
  title: 'Pages/Actual domain pages',
  component: ActualDomainPage,
  parameters: { layout: 'fullscreen', msw: { handlers: storybookProblemHandlers } },
  args: { page: 'research' },
} satisfies Meta<typeof ActualDomainPage>;

export default meta;
type Story = StoryObj<typeof meta>;

export const ResearchProblem: Story = {};
export const StrategyProblem: Story = { args: { page: 'strategy' } };
export const DataHappy: Story = {
  args: { page: 'data' },
  parameters: { msw: { handlers: sharedMswScenarios.happy } },
};
export const DataLoading: Story = {
  args: { page: 'data' },
  parameters: { msw: { handlers: sharedMswScenarios.loading } },
};
export const DataEmpty: Story = {
  args: { page: 'data' },
  parameters: { msw: { handlers: sharedMswScenarios.empty } },
};
export const DataDelayed: Story = {
  args: { page: 'data' },
  parameters: { msw: { handlers: sharedMswScenarios.delayed } },
};
export const DataStale: Story = {
  args: { page: 'data' },
  parameters: { msw: { handlers: sharedMswScenarios.stale } },
};
export const DataPermission: Story = {
  args: { page: 'data' },
  parameters: { msw: { handlers: sharedMswScenarios.permission } },
};
export const DataConflict: Story = {
  args: { page: 'data' },
  parameters: { msw: { handlers: sharedMswScenarios.conflict } },
};
