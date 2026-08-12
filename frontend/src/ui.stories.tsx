import type { Meta, StoryObj } from '@storybook/react-vite';
import { Badge, Panel, State } from './ui';

const meta = {
  title: 'Design System/Server states',
  component: Panel,
  args: { title: 'Validation state', children: <Badge>FROZEN</Badge> },
} satisfies Meta<typeof Panel>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Frozen: Story = {};
export const Loading: Story = {
  args: { title: 'Server state', children: <State kind="loading">Loading server truth…</State> },
};
export const Empty: Story = {
  args: { title: 'Server state', children: <State kind="empty">No records available.</State> },
};
export const PermissionDenied: Story = {
  args: {
    title: 'Protected action',
    children: <State kind="permission">Your role cannot perform this action.</State>,
  },
};
export const Failure: Story = {
  args: {
    title: 'Mandatory validation',
    children: <State kind="error">Validation failed. No override is available.</State>,
  },
};
